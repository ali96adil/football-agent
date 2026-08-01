from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb

from app.auth import CurrentUser, audit, require
from app.db.connection import pool
from app.jobs import JobQueue


router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


class ActionRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=1000)
    window_size: int = Field(default=10, ge=1, le=100)
    fixture_days: int = Field(default=14, ge=1, le=60)


class SettingsUpdate(BaseModel):
    sync_interval_seconds: int | None = Field(default=None, ge=60, le=86400)
    stale_data_minutes: int | None = Field(default=None, ge=15, le=10080)
    telegram_success_alerts: bool | None = None


@router.get("")
async def operations(_: Annotated[CurrentUser, Depends(require("read"))]) -> dict:
    async with pool.connection() as connection:
        jobs_result = await connection.execute(
            """SELECT j.id, j.job_type, j.status, j.attempt_count, j.max_attempts,
                      j.created_at, j.started_at, j.finished_at, j.last_error,
                      j.result, j.requested_via, u.username AS requested_by
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
            """SELECT id, code, name, enabled, priority, reliability_score,
                      requests_used_today, last_success_at, last_failure_at, updated_at
                 FROM core.data_sources ORDER BY priority DESC, code"""
        )
    return {
        "jobs": await jobs_result.fetchall(),
        "settings": {row["key"]: row["value"] for row in await settings_result.fetchall()},
        "audit": await audit_result.fetchall(),
        "sources": await sources_result.fetchall(),
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
            """UPDATE core.jobs SET status='retry', run_after=NOW(), finished_at=NULL,
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
