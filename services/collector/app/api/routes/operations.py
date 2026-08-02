from __future__ import annotations

import ipaddress
import asyncio
import logging
import os
import socket
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb
from psycopg.errors import UniqueViolation

from app.auth import CurrentUser, audit, require
from app.db.connection import pool
from app.jobs import JobQueue
from app.providers import list_providers, provider_manager


router = APIRouter(prefix="/api/v1/operations", tags=["operations"])
logger = logging.getLogger("football-collector.operations")


class ActionRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=1000)
    window_size: int = Field(default=10, ge=1, le=100)
    fixture_days: int = Field(default=14, ge=1, le=60)


class SettingsUpdate(BaseModel):
    sync_interval_seconds: int | None = Field(default=None, ge=60, le=86400)
    stale_data_minutes: int | None = Field(default=None, ge=15, le=10080)
    telegram_success_alerts: bool | None = None


CAPABILITIES = {"competitions", "fixtures", "teams", "standings", "predictions", "news"}


class SourceWrite(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]{1,49}$")
    name: str = Field(min_length=2, max_length=120)
    source_type: Literal["api", "official_site", "news", "scraper", "weather", "market", "manual"]
    provider: str | None = Field(default=None, max_length=50)
    base_url: str | None = Field(default=None, max_length=500)
    priority: int = Field(default=50, ge=0, le=100)
    capabilities: list[str] = Field(default_factory=list, max_length=12)
    enabled: bool = True
    secret: str | None = Field(default=None, min_length=8, max_length=4096)


def validate_source(payload: SourceWrite) -> None:
    unknown = set(payload.capabilities) - CAPABILITIES
    if unknown:
        raise HTTPException(status_code=422, detail="unsupported source capability")
    if payload.provider and payload.provider not in list_providers():
        raise HTTPException(status_code=422, detail="unsupported provider")
    if payload.base_url:
        parsed = urlsplit(payload.base_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise HTTPException(status_code=422, detail="base_url must be a public HTTPS URL")
        if parsed.hostname.lower() == "localhost":
            raise HTTPException(status_code=422, detail="base_url must be a public HTTPS URL")
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            pass
        else:
            if not address.is_global:
                raise HTTPException(status_code=422, detail="base_url must be a public HTTPS URL")


def encryption_key() -> str:
    key = os.getenv("SOURCE_SECRET_ENCRYPTION_KEY", "")
    if len(key) < 32:
        raise HTTPException(status_code=503, detail="source secret storage is not configured")
    return key


async def require_public_destination(url: str) -> None:
    hostname = urlsplit(url).hostname
    if not hostname:
        raise HTTPException(status_code=422, detail="base_url must be a public HTTPS URL")
    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, hostname, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise HTTPException(status_code=409, detail="source hostname could not be resolved") from exc
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise HTTPException(status_code=422, detail="source destination is not public")


@router.get("")
async def operations(_: Annotated[CurrentUser, Depends(require("read"))]) -> dict:
    async with pool.connection() as connection:
        jobs_result = await connection.execute(
            """SELECT j.id, j.job_type, j.status, j.attempt_count, j.max_attempts,
                      j.created_at, j.started_at, j.finished_at, j.last_error,
                      j.result, j.requested_via, j.heartbeat_at, j.lease_expires_at,
                      u.username AS requested_by
                 FROM core.jobs j LEFT JOIN core.users u ON u.id=j.requested_by
                ORDER BY j.created_at DESC LIMIT 100"""
        )
        settings_result = await connection.execute("SELECT key, value, updated_at FROM core.system_settings ORDER BY key")
        audit_result = await connection.execute(
            """SELECT id, occurred_at, actor_username, actor_role, action,
                      target_type, target_id, outcome, details
                 FROM core.audit_log ORDER BY occurred_at DESC LIMIT 100"""
        )
        sources_result = await connection.execute(
            """SELECT id, code, name, source_type, provider, base_url, capabilities,
                      enabled, priority, reliability_score,
                      (secret_ciphertext IS NOT NULL) AS secret_configured,
                      requests_used_today, last_success_at, last_failure_at, updated_at
                 FROM core.data_sources ORDER BY priority DESC, code"""
        )
    return {
        "jobs": await jobs_result.fetchall(),
        "settings": {row["key"]: row["value"] for row in await settings_result.fetchall()},
        "audit": await audit_result.fetchall(),
        "sources": await sources_result.fetchall(),
    }


@router.post("/sources", status_code=201)
async def create_source(payload: SourceWrite, request: Request, actor: Annotated[CurrentUser, Depends(require("admin", csrf=True))]) -> dict:
    validate_source(payload)
    key = encryption_key() if payload.secret else None
    async with pool.connection() as connection:
        try:
            result = await connection.execute(
                """INSERT INTO core.data_sources
               (code,name,source_type,provider,base_url,priority,capabilities,enabled,secret_ciphertext)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,
                       CASE WHEN %s::text IS NULL THEN NULL ELSE pgp_sym_encrypt(%s::text,%s::text) END)
               RETURNING id,code,name,source_type,provider,base_url,priority,capabilities,enabled,
                         (secret_ciphertext IS NOT NULL) AS secret_configured""",
                (payload.code,payload.name,payload.source_type,payload.provider,payload.base_url,
                 payload.priority,payload.capabilities,payload.enabled,payload.secret,payload.secret,key),
            )
        except UniqueViolation as exc:
            raise HTTPException(status_code=409, detail="source code already exists") from exc
        row = await result.fetchone()
        await audit(connection, action="sources.create", outcome="success", request=request, actor=actor, target_type="source", target_id=str(row["id"]), details={"code":payload.code,"capabilities":payload.capabilities})
    return row


@router.put("/sources/{source_id}")
async def replace_source(source_id: str, payload: SourceWrite, request: Request, actor: Annotated[CurrentUser, Depends(require("admin", csrf=True))]) -> dict:
    validate_source(payload)
    key = encryption_key() if payload.secret else None
    async with pool.connection() as connection:
        result = await connection.execute(
            """UPDATE core.data_sources SET code=%s,name=%s,source_type=%s,provider=%s,
                      base_url=%s,priority=%s,capabilities=%s,enabled=%s,
                      secret_ciphertext=CASE WHEN %s::text IS NULL THEN secret_ciphertext ELSE pgp_sym_encrypt(%s::text,%s::text) END,
                      updated_at=NOW() WHERE id=%s
               RETURNING id,code,name,source_type,provider,base_url,priority,capabilities,enabled,
                         (secret_ciphertext IS NOT NULL) AS secret_configured""",
            (payload.code,payload.name,payload.source_type,payload.provider,payload.base_url,
             payload.priority,payload.capabilities,payload.enabled,payload.secret,payload.secret,key,source_id),
        )
        row = await result.fetchone()
        if not row: raise HTTPException(status_code=404, detail="source not found")
        await audit(connection, action="sources.update", outcome="success", request=request, actor=actor, target_type="source", target_id=source_id, details={"fields":["code","name","source_type","provider","base_url","priority","capabilities","enabled"],"secret_replaced":payload.secret is not None})
    return row


@router.post("/sources/{source_id}/test")
async def test_source(
    source_id: str,
    request: Request,
    actor: Annotated[CurrentUser, Depends(require("admin", csrf=True))],
) -> dict:
    async with pool.connection() as connection:
        result = await connection.execute(
            """
            SELECT id, provider, base_url, secret_ciphertext
            FROM core.data_sources
            WHERE id = %s
            """,
            (source_id,),
        )
        row = await result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="source not found")

        if not row["provider"] or not row["base_url"]:
            raise HTTPException(
                status_code=409,
                detail="source connection is incomplete",
            )

        await require_public_destination(row["base_url"])

        secret = None
        if row["secret_ciphertext"] is not None:
            decrypted = await connection.execute(
                "SELECT pgp_sym_decrypt(%s, %s) AS value",
                (
                    row["secret_ciphertext"],
                    encryption_key(),
                ),
            )
            secret = (await decrypted.fetchone())["value"]

        try:
            endpoint = row["base_url"].rstrip("/")

            if row["provider"] == "api_football":
                endpoint = f"{endpoint}/status"

            status, payload = await provider_manager.fetch(
                provider=row["provider"],
                endpoint=endpoint,
                params={},
                api_key=secret or "",
            )

            if row["provider"] == "api_football":
                provider_errors = (
                    payload.get("errors")
                    if isinstance(payload, dict)
                    else None
                )

                response_data = (
                    payload.get("response", {})
                    if isinstance(payload, dict)
                    else {}
                )

                subscription = (
                    response_data.get("subscription", {})
                    if isinstance(response_data, dict)
                    else {}
                )

                ok = (
                    status == 200
                    and not provider_errors
                    and subscription.get("active") is True
                )
            else:
                ok = 200 <= status < 400

            if ok:
                reason = "ok"
            elif status in (401, 403):
                reason = "authentication_failure"
            else:
                reason = "http_status"

        except Exception:
            logger.exception(
                "Source connection test failed for source_id=%s",
                source_id,
            )
            ok = False
            status = None
            reason = "connection_failure"

        await audit(
            connection,
            action="sources.test",
            outcome="success" if ok else "failure",
            request=request,
            actor=actor,
            target_type="source",
            target_id=source_id,
            details={
                "reason": reason,
                "http_status": status,
            },
        )

    return {
        "ok": ok,
        "reason": reason,
        "http_status": status,
    }

@router.post("/actions/{action}", status_code=202)
async def enqueue_action(
    action: Literal["sync", "snapshots", "predictions", "evaluation"],
    payload: ActionRequest, request: Request,
    actor: Annotated[CurrentUser, Depends(require("operate", csrf=True))],
) -> dict:
    job_types = {
        "sync": "sync_pipeline", "snapshots": "build_snapshots",
        "predictions": "run_predictions", "evaluation": "evaluate_predictions",
    }
    job_type = job_types[action]
    key = f"web:{actor.id}:{uuid4()}"
    job_payload: dict[str, Any] = {
        "limit": payload.limit, "window_size": payload.window_size,
        "fixture_days": payload.fixture_days, "calculation_version": "v1-product",
    }
    async with pool.connection() as connection:
        if job_type == "sync_pipeline" and not await JobQueue.reserve_sync_slot(connection):
            raise HTTPException(status_code=409, detail="a sync pipeline is already active")
        result = await connection.execute(
            """INSERT INTO core.jobs
               (job_type, idempotency_key, payload, timeout_seconds, requested_by, requested_via)
               VALUES (%s, %s, %s, 1800, %s, 'web') RETURNING id, status""",
            (job_type, key, Jsonb(job_payload), actor.id),
        )
        row = await result.fetchone()
        await audit(connection, action=f"operations.{action}", outcome="success", request=request, actor=actor, target_type="job", target_id=str(row["id"]))
    return {"id": row["id"], "status": row["status"], "job_type": job_type}


@router.post("/jobs/{job_id}/retry", status_code=202)
async def retry_job(job_id: str, request: Request, actor: Annotated[CurrentUser, Depends(require("operate", csrf=True))]) -> dict:
    async with pool.connection() as connection:
        result = await connection.execute(
            """UPDATE core.jobs SET status='retry', attempt_count=0, run_after=NOW(), finished_at=NULL,
                      last_error=NULL, result=NULL, updated_at=NOW(), requested_by=%s,
                      requested_via='web'
                 WHERE id=%s AND status IN ('failed', 'dead_letter')
                 RETURNING id, status""",
            (actor.id, job_id),
        )
        row = await result.fetchone()
        if not row:
            raise HTTPException(status_code=409, detail="job is not retryable")
        await audit(connection, action="operations.retry", outcome="success", request=request, actor=actor, target_type="job", target_id=job_id)
    return row


@router.patch("/sources/{source_id}")
async def update_source(source_id: str, enabled: bool, request: Request, actor: Annotated[CurrentUser, Depends(require("admin", csrf=True))]) -> dict:
    async with pool.connection() as connection:
        result = await connection.execute(
            "UPDATE core.data_sources SET enabled=%s, updated_at=NOW() WHERE id=%s RETURNING id, code, enabled",
            (enabled, source_id),
        )
        row = await result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="source not found")
        await audit(connection, action="sources.update", outcome="success", request=request, actor=actor, target_type="source", target_id=source_id, details={"enabled": enabled})
    return row


@router.patch("/settings")
async def update_settings(payload: SettingsUpdate, request: Request, actor: Annotated[CurrentUser, Depends(require("admin", csrf=True))]) -> dict:
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=422, detail="no settings supplied")
    async with pool.connection() as connection:
        for key, value in changes.items():
            await connection.execute(
                "UPDATE core.system_settings SET value=%s, updated_at=NOW(), updated_by=%s WHERE key=%s",
                (Jsonb(value), actor.id, key),
            )
        await audit(connection, action="settings.update", outcome="success", request=request, actor=actor, target_type="settings", details={"keys": sorted(changes)})
    return {"updated": sorted(changes)}
