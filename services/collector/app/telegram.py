from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
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


def content_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def prediction_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Return only meaningful, public prediction fields used for deduplication."""
    return {
        "prediction_id": str(row["id"]),
        "fixture_id": str(row["fixture_id"]),
        "home_snapshot_hash": row["home_snapshot_hash"],
        "away_snapshot_hash": row["away_snapshot_hash"],
        "kickoff_at": row["kickoff_at"],
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "predicted_outcome": row["predicted_outcome"],
        "confidence": row["confidence"],
        "home_win_probability": row["home_win_probability"],
        "draw_probability": row["draw_probability"],
        "away_win_probability": row["away_win_probability"],
        "most_likely_home_goals": row["most_likely_home_goals"],
        "most_likely_away_goals": row["most_likely_away_goals"],
    }


def prediction_message(payload: dict[str, Any], event_type: str) -> str:
    heading = "توقع جديد" if event_type == "prediction_new" else "تغير مهم في التوقع"
    outcomes = {"home_win": "فوز صاحب الأرض", "draw": "تعادل", "away_win": "فوز الضيف"}
    score = "—"
    if payload["most_likely_home_goals"] is not None and payload["most_likely_away_goals"] is not None:
        score = f"{payload['most_likely_home_goals']}-{payload['most_likely_away_goals']}"
    return (
        f"{heading}\n{payload['home_team']} × {payload['away_team']}\n"
        f"النتيجة المتوقعة: {outcomes.get(payload['predicted_outcome'], 'غير محدد')}\n"
        f"النتيجة الأرجح: {score}\nالثقة: {float(payload['confidence']) * 100:.0f}%"
    )


def prediction_is_current(
    row: dict[str, Any], activated_at: datetime, *, now: datetime | None = None
) -> bool:
    current = now or datetime.now(timezone.utc)
    return bool(
        row["updated_at"] > activated_at
        and row["kickoff_at"] is not None
        and row["kickoff_at"] > current
        and not row["result_confirmed"]
    )


class TelegramBot:
    def __init__(self, pool: Any, transport: TelegramTransport) -> None:
        self.pool = pool
        self.transport = transport
        self.offset: int | None = None

    async def identity(self, chat_id: int, telegram_user_id: int | None) -> TelegramIdentity | None:
        async with self.pool.connection() as connection:
            result = await connection.execute(
                """SELECT t.chat_id, t.telegram_user_id, t.alerts,
                          u.id, u.username, u.display_name, u.role
                     FROM core.telegram_identities t JOIN core.users u ON u.id=t.user_id
                    WHERE t.chat_id=%s AND t.enabled=TRUE AND u.is_active=TRUE
                      AND t.telegram_user_id=%s""",
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
            chat = message.get("chat", {})
            sender = message.get("from", {})
            logger.warning(
                "Rejected Telegram command identity=%s",
                json.dumps(
                    {
                        "chat_id": chat_id,
                        "chat_type": str(chat.get("type", "unknown"))[:32],
                        "chat_title": str(chat.get("title", ""))[:255],
                        "telegram_user_id": (
                            int(sender_id) if sender_id is not None else None
                        ),
                        "username": str(sender.get("username", ""))[:64] or None,
                        "reason": "not_allowlisted",
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            )
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
                result = await connection.execute("UPDATE core.jobs SET status='retry', attempt_count=0, run_after=NOW(), finished_at=NULL, last_error=NULL, result=NULL, requested_by=%s, requested_via='telegram' WHERE id=%s AND status IN ('failed','dead_letter') RETURNING id", (identity.user.id, argument))
                row = await result.fetchone()
                if not row:
                    return "المهمة غير قابلة لإعادة المحاولة."
                await audit(connection, action="telegram.retry", outcome="success", actor=identity.user, target_type="job", target_id=argument, details={"chat_id": identity.chat_id})
                return f"أعيدت المهمة إلى قائمة الانتظار: {argument}"
            job_type = {"sync":"sync_pipeline", "snapshots":"build_snapshots", "run_predictions":"run_predictions"}[command]
            if job_type == "sync_pipeline":
                from app.jobs import JobQueue
                if not await JobQueue.reserve_sync_slot(connection):
                    return "توجد مزامنة قيد التنفيذ بالفعل."
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
            destinations_result = await connection.execute(
                """SELECT * FROM core.telegram_destinations
                    WHERE enabled=TRUE ORDER BY chat_id"""
            )
            destinations = await destinations_result.fetchall()
        for destination in destinations:
            await self._publish_predictions(destination)
            await self._publish_job_events(destination)

    async def _claim(
        self, destination_chat_id: int, event_key: str, event_type: str,
        digest: str, occurred_at: Any,
    ) -> bool:
        async with self.pool.connection() as connection:
            result = await connection.execute(
                """INSERT INTO core.telegram_deliveries
                   (destination_chat_id,event_key,event_type,content_hash,event_occurred_at)
                   VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (destination_chat_id,event_key,content_hash) DO UPDATE
                     SET status='claimed', claimed_at=NOW(), failure_code=NULL
                   WHERE core.telegram_deliveries.status='failed'
                     AND core.telegram_deliveries.claimed_at <= NOW() - INTERVAL '5 minutes'
                   RETURNING id""",
                (destination_chat_id,event_key,event_type,digest,occurred_at),
            )
            return await result.fetchone() is not None

    async def _finish(self, chat_id: int, event_key: str, digest: str, *, sent: bool) -> None:
        async with self.pool.connection() as connection:
            await connection.execute(
                """UPDATE core.telegram_deliveries
                      SET status=%s, sent_at=CASE WHEN %s THEN NOW() ELSE NULL END,
                          failure_code=CASE WHEN %s THEN NULL ELSE 'transport_failed' END
                    WHERE destination_chat_id=%s AND event_key=%s AND content_hash=%s""",
                ("sent" if sent else "failed", sent, sent, chat_id, event_key, digest),
            )

    async def _deliver(
        self, chat_id: int, event_key: str, event_type: str,
        digest: str, occurred_at: Any, message: str,
    ) -> None:
        if not await self._claim(chat_id, event_key, event_type, digest, occurred_at):
            return
        try:
            await self.transport.send(chat_id, message)
        except Exception as exc:
            await self._finish(chat_id, event_key, digest, sent=False)
            logger.error(
                "Telegram publication failed event_type=%s destination_chat_id=%s error_type=%s",
                event_type, chat_id, type(exc).__name__,
            )
            return
        await self._finish(chat_id, event_key, digest, sent=True)

    async def _publish_predictions(self, destination: dict[str, Any]) -> None:
        if not (destination["publish_prediction_new"] or destination["publish_prediction_changed"]):
            return
        async with self.pool.connection() as connection:
            result = await connection.execute(
                """SELECT mp.*, ht.canonical_name AS home_team,
                          at.canonical_name AS away_team,
                          hs.snapshot_hash AS home_snapshot_hash,
                          aws.snapshot_hash AS away_snapshot_hash,
                          EXISTS (
                            SELECT 1 FROM core.telegram_deliveries td
                             WHERE td.destination_chat_id=%s
                               AND td.event_key='prediction:'||mp.id::text
                          ) AS published_before
                     FROM core.match_predictions mp
                     JOIN core.teams ht ON ht.id=mp.home_team_id
                     JOIN core.teams at ON at.id=mp.away_team_id
                     JOIN core.team_snapshots hs ON hs.id=mp.home_snapshot_id
                     JOIN core.team_snapshots aws ON aws.id=mp.away_snapshot_id
                    WHERE mp.updated_at > %s
                      AND mp.kickoff_at > NOW()
                      AND mp.result_confirmed=FALSE
                    ORDER BY mp.updated_at LIMIT 100""",
                (destination["chat_id"], destination["activated_at"]),
            )
            rows = await result.fetchall()
        for row in rows:
            if not prediction_is_current(row,destination["activated_at"]):
                continue
            event_type = "prediction_changed" if row["published_before"] else "prediction_new"
            if not destination[f"publish_{event_type}"]:
                continue
            payload = prediction_payload(row)
            digest = content_hash(payload)
            await self._deliver(
                int(destination["chat_id"]), f"prediction:{row['id']}", event_type,
                digest, row["updated_at"], prediction_message(payload,event_type),
            )

    async def _publish_job_events(self, destination: dict[str, Any]) -> None:
        if not (destination["publish_update_success"] or destination["publish_update_failure"]):
            return
        async with self.pool.connection() as connection:
            result = await connection.execute(
                """SELECT id,job_type,status,finished_at
                     FROM core.jobs
                    WHERE finished_at > %s
                      AND status IN ('succeeded','dead_letter')
                      AND job_type IN ('sync_pipeline','run_predictions')
                    ORDER BY finished_at LIMIT 100""",
                (destination["activated_at"],),
            )
            rows = await result.fetchall()
        for row in rows:
            event_type = "update_success" if row["status"] == "succeeded" else "update_failure"
            if not destination[f"publish_{event_type}"]:
                continue
            payload={"job_id":str(row["id"]),"job_type":row["job_type"],"status":row["status"]}
            message = (
                f"اكتمل التحديث: {row['job_type']}" if event_type == "update_success"
                else f"فشل التحديث: {row['job_type']}. راجع سجل العمليات."
            )
            await self._deliver(
                int(destination["chat_id"]), f"job:{row['id']}", event_type,
                content_hash(payload), row["finished_at"], message,
            )
