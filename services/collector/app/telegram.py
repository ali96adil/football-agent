from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb

from app.auth import CurrentUser, audit


logger = logging.getLogger("football-telegram")
READ_COMMANDS = frozenset({"status", "fixtures", "predictions", "sources", "jobs"})
CONTROL_COMMANDS = frozenset({"sync", "snapshots", "run_predictions", "retry"})


def command_permission(command: str) -> str | None:
    if command in READ_COMMANDS:
        return "read"
    if command in CONTROL_COMMANDS:
        return "operate"
    return None


class TelegramTransport:
    def __init__(self, token: str) -> None:
        if not token.strip():
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        self.__base_url = f"https://api.telegram.org/bot{token.strip()}"

    def _call(self, method: str, payload: dict[str, Any]) -> dict:
        request = urllib.request.Request(
            f"{self.__base_url}/{method}",
            data=urllib.parse.urlencode(payload).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(request, timeout=70) as response:
                body = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Telegram {method} request failed") from exc
        if not body.get("ok"):
            raise RuntimeError(f"Telegram {method} rejected the request")
        return body

    async def updates(self, offset: int | None) -> list[dict]:
        payload: dict[str, Any] = {"timeout": 50, "allowed_updates": json.dumps(["message"])}
        if offset is not None:
            payload["offset"] = offset
        return (await asyncio.to_thread(self._call, "getUpdates", payload)).get("result", [])

    async def send(self, chat_id: int, text: str) -> None:
        await asyncio.to_thread(self._call, "sendMessage", {"chat_id": chat_id, "text": text[:4000]})


@dataclass(frozen=True)
class TelegramIdentity:
    chat_id: int
    telegram_user_id: int | None
    user: CurrentUser
    alerts: dict[str, bool]


class TelegramBot:
    def __init__(self, pool: Any, transport: TelegramTransport) -> None:
        self.pool = pool
        self.transport = transport
        self.offset: int | None = None
        self.alerted: set[str] = set()

    async def identity(self, chat_id: int, telegram_user_id: int | None) -> TelegramIdentity | None:
        async with self.pool.connection() as connection:
            result = await connection.execute(
                """SELECT t.chat_id, t.telegram_user_id, t.alerts,
                          u.id, u.username, u.display_name, u.role
                     FROM core.telegram_identities t JOIN core.users u ON u.id=t.user_id
                    WHERE t.chat_id=%s AND t.enabled=TRUE AND u.is_active=TRUE
                      AND (t.telegram_user_id IS NULL OR t.telegram_user_id=%s)""",
                (chat_id, telegram_user_id),
            )
            row = await result.fetchone()
        if not row:
            return None
        return TelegramIdentity(
            chat_id=int(row["chat_id"]), telegram_user_id=row["telegram_user_id"],
            user=CurrentUser(str(row["id"]), row["username"], row["display_name"], row["role"]),
            alerts=row["alerts"],
        )

    async def handle(self, message: dict) -> None:
        text = str(message.get("text", "")).strip()
        if not text.startswith("/"):
            return
        chat_id = int(message["chat"]["id"])
        sender_id = message.get("from", {}).get("id")
        identity = await self.identity(chat_id, int(sender_id) if sender_id is not None else None)
        if not identity:
            logger.warning("Rejected Telegram command from a non-allowlisted identity")
            return
        parts = text.split(maxsplit=1)
        command = parts[0][1:].split("@", 1)[0].lower()
        argument = parts[1].strip() if len(parts) == 2 else ""
        permission = command_permission(command)
        if permission is None:
            await self.transport.send(chat_id, "أمر غير معروف.")
            return
        if not identity.user.has(permission):
            async with self.pool.connection() as connection:
                await audit(connection, action=f"telegram.{command}", outcome="denied", actor=identity.user, details={"chat_id": chat_id})
            await self.transport.send(chat_id, "لا تملك الصلاحية المطلوبة.")
            return
        try:
            response = await self.execute(identity, command, argument)
            await self.transport.send(chat_id, response)
        except Exception:
            logger.exception("Telegram command failed: %s", command)
            await self.transport.send(chat_id, "فشل تنفيذ الأمر. راجع سجل العمليات.")

    async def execute(self, identity: TelegramIdentity, command: str, argument: str) -> str:
        async with self.pool.connection() as connection:
            if command == "status":
                result = await connection.execute("SELECT status, heartbeat_at, next_sync_at FROM core.worker_heartbeats ORDER BY heartbeat_at DESC LIMIT 1")
                row = await result.fetchone()
                return f"worker: {row['status'] if row else 'offline'}\nheartbeat: {row['heartbeat_at'] if row else '—'}"
            if command == "fixtures":
                result = await connection.execute("SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE fixture_status='scheduled') AS scheduled FROM core.fixtures")
                row = await result.fetchone(); return f"المباريات: {row['total']}\nالمجدولة: {row['scheduled']}"
            if command == "predictions":
                result = await connection.execute("SELECT COUNT(*) AS total FROM core.match_predictions")
                return f"التوقعات: {(await result.fetchone())['total']}"
            if command == "sources":
                result = await connection.execute("SELECT code, enabled, last_success_at FROM core.data_sources ORDER BY priority DESC")
                return "\n".join(f"{r['code']}: {'on' if r['enabled'] else 'off'} · {r['last_success_at'] or 'never'}" for r in await result.fetchall())
            if command == "jobs":
                result = await connection.execute("SELECT job_type, status, created_at FROM core.jobs ORDER BY created_at DESC LIMIT 10")
                return "\n".join(f"{r['job_type']}: {r['status']}" for r in await result.fetchall()) or "لا توجد مهام."
            if command == "retry":
                if not argument:
                    return "الاستخدام: /retry JOB_ID"
                result = await connection.execute("UPDATE core.jobs SET status='retry', run_after=NOW(), finished_at=NULL, last_error=NULL, result=NULL, requested_by=%s, requested_via='telegram' WHERE id=%s AND status IN ('failed','dead_letter') RETURNING id", (identity.user.id, argument))
                row = await result.fetchone()
                if not row:
                    return "المهمة غير قابلة لإعادة المحاولة."
                await audit(connection, action="telegram.retry", outcome="success", actor=identity.user, target_type="job", target_id=argument, details={"chat_id": identity.chat_id})
                return f"أعيدت المهمة إلى قائمة الانتظار: {argument}"
            job_type = {"sync":"sync_pipeline", "snapshots":"build_snapshots", "run_predictions":"run_predictions"}[command]
            result = await connection.execute(
                """INSERT INTO core.jobs (job_type,idempotency_key,payload,timeout_seconds,requested_by,requested_via)
                   VALUES (%s,%s,%s,1800,%s,'telegram') RETURNING id""",
                (job_type, f"telegram:{identity.chat_id}:{uuid4()}", Jsonb({"limit":100,"window_size":10,"fixture_days":14,"calculation_version":"v1-product"}), identity.user.id),
            )
            job_id = str((await result.fetchone())["id"])
            await audit(connection, action=f"telegram.{command}", outcome="success", actor=identity.user, target_type="job", target_id=job_id, details={"chat_id": identity.chat_id})
            return f"أضيفت المهمة: {job_id}"

    async def poll_once(self) -> None:
        for update in await self.transport.updates(self.offset):
            self.offset = int(update["update_id"]) + 1
            if "message" in update:
                await self.handle(update["message"])

    async def send_alerts(self) -> None:
        async with self.pool.connection() as connection:
            identities_result = await connection.execute("SELECT chat_id, alerts FROM core.telegram_identities WHERE enabled=TRUE")
            identities = await identities_result.fetchall()
            events_result = await connection.execute(
                """SELECT 'job:'||id::text AS key, 'فشلت المهمة '||job_type||': '||COALESCE(last_error,'unknown') AS message, 'failures' AS kind
                     FROM core.jobs WHERE status='dead_letter' AND finished_at > NOW()-INTERVAL '10 minutes'
                   UNION ALL
                   SELECT 'worker:stale', 'تحذير: heartbeat الخاصة بالـworker متأخرة.', 'worker'
                    WHERE NOT EXISTS (SELECT 1 FROM core.worker_heartbeats WHERE heartbeat_at > NOW()-INTERVAL '2 minutes')
                   UNION ALL
                   SELECT 'data:stale', 'تحذير: البيانات لم تُحدّث ضمن الحد المسموح.', 'stale_data'
                    WHERE NOT EXISTS (SELECT 1 FROM raw.api_payloads WHERE response_status < 400 AND requested_at > NOW()-INTERVAL '3 hours')"""
                + """
                   UNION ALL
                   SELECT 'source:'||code||':'||extract(epoch from last_failure_at)::bigint,
                          'فشل مصدر البيانات: '||code, 'failures'
                     FROM core.data_sources
                    WHERE last_failure_at > NOW()-INTERVAL '10 minutes'
                      AND (last_success_at IS NULL OR last_failure_at > last_success_at)
                   UNION ALL
                   SELECT 'success:'||id::text, 'اكتملت العملية: '||job_type, 'success'
                     FROM core.jobs
                    WHERE status='succeeded' AND finished_at > NOW()-INTERVAL '10 minutes'
                      AND job_type IN ('sync_pipeline','run_predictions')
                      AND EXISTS (SELECT 1 FROM core.system_settings WHERE key='telegram_success_alerts' AND value='true'::jsonb)
                """
            )
            events = await events_result.fetchall()
        for event in events:
            if event["key"] in self.alerted:
                continue
            for identity in identities:
                if identity["alerts"].get(event["kind"], True):
                    await self.transport.send(int(identity["chat_id"]), event["message"])
            self.alerted.add(event["key"])
