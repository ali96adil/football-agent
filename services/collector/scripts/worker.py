"""Background worker entrypoint. The API process never consumes queue jobs."""
from __future__ import annotations

import asyncio
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import psycopg

from app.db.connection import close_connection_pool, open_connection_pool, pool
from app.config import build_database_url
from app.jobs import Job, JobQueue
from app.job_errors import JobExecutionError, safe_failure
from app.operations import WorkerOperations

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("football-worker")


def optional_uuid(payload: dict[str, Any], key: str) -> UUID | None:
    """Parse an optional scope UUID without inventing collection context."""
    value = payload.get(key)
    if value in (None, ""):
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"invalid {key} in job payload") from exc


async def execute(job: Job) -> dict[str, Any]:
    """Run an idempotent handler keyed by job.idempotency_key.

    A database lease provides at-least-once delivery, not distributed exactly
    once semantics. Future external side effects must pass the stable key to a
    provider that supports idempotency, or persist an outbox/result first.
    """
    if job.job_type == "noop":
        return {"status": "success"}
    if job.job_type == "sync_pipeline":
        from app.api.routes.sync import sync_all

        result = await sync_all(
            fixture_days=int(job.payload.get("fixture_days", 14)),
            prediction_limit=int(job.payload.get("prediction_limit", 100)),
            evaluation_limit=int(job.payload.get("evaluation_limit", 100)),
            window_size=int(job.payload.get("window_size", 10)),
            calculation_version=str(job.payload.get("calculation_version", "v1-dev")),
        )
        failed_collection_stages = {
            item.get("stage")
            for item in result.get("errors", [])
            if item.get("stage") in {"competitions", "load_competitions", "fixtures"}
        }
        if failed_collection_stages:
            errors = [item for item in result.get("errors", []) if item.get("stage") in failed_collection_stages]
            first = errors[0] if errors else {}
            raise JobExecutionError(
                str(first.get("reason", "dependency_failure")),
                stage=", ".join(sorted(failed_collection_stages)),
            )
        logger.info(
            "sync pipeline finished with status=%s duration=%s",
            result["status"],
            result["duration_seconds"],
        )
        return result
    if job.job_type == "build_snapshots":
        from scripts.build_all_snapshots import get_team_targets
        from app.services.snapshot_service import SnapshotService

        successful, failed = 0, 0
        async with pool.connection() as connection:
            targets = await get_team_targets(
                connection,
                competition_id=optional_uuid(job.payload, "competition_id"),
                season_id=optional_uuid(job.payload, "season_id"),
                limit=int(job.payload.get("limit", 100)),
            )
            for target in targets:
                try:
                    await SnapshotService.build_and_save(
                        connection=connection, team_id=target.team_id,
                        competition_id=target.competition_id, season_id=target.season_id,
                        window_size=int(job.payload.get("window_size", 10)),
                        cutoff_at=target.data_cutoff_at,
                    )
                    successful += 1
                except Exception:
                    failed += 1
        if failed:
            raise RuntimeError(f"snapshot generation failed for {failed} target(s)")
        return {"status": "success", "successful": successful, "failed": failed}
    if job.job_type == "run_predictions":
        from app.services.scheduled_prediction_service import ScheduledPredictionService
        async with pool.connection() as connection:
            result = await ScheduledPredictionService.run(
                connection, days_ahead=int(job.payload.get("fixture_days", 14)),
                limit=int(job.payload.get("limit", 100)), window_size=int(job.payload.get("window_size", 10)),
                calculation_version=str(job.payload.get("calculation_version", "v1-product")),
            )
            if result.get("status") == "partial_success":
                raise RuntimeError("prediction generation completed with failures")
            return result
    if job.job_type == "evaluate_predictions":
        from app.services.prediction_evaluation_service import PredictionEvaluationService
        async with pool.connection() as connection:
            return await PredictionEvaluationService.run(connection, limit=int(job.payload.get("limit", 100)))
    raise RuntimeError(f"unsupported job_type: {job.job_type}")


def sync_schedule(now: datetime, interval_seconds: int) -> tuple[str, datetime]:
    bucket = int(now.timestamp()) // interval_seconds
    next_sync_at = datetime.fromtimestamp(
        (bucket + 1) * interval_seconds,
        tz=timezone.utc,
    )
    return f"scheduled:{bucket}", next_sync_at


def sync_payload() -> dict[str, Any]:
    return {
        "fixture_days": int(os.getenv("SYNC_FIXTURE_DAYS", "14")),
        "prediction_limit": int(os.getenv("SYNC_PREDICTION_LIMIT", "100")),
        "evaluation_limit": int(os.getenv("SYNC_EVALUATION_LIMIT", "100")),
        "window_size": int(os.getenv("SYNC_SNAPSHOT_WINDOW", "10")),
        "calculation_version": os.getenv("SYNC_CALCULATION_VERSION", "v1-dev"),
    }


async def configured_sync_interval(default_seconds: int) -> int:
    async with pool.connection() as connection:
        result = await connection.execute(
            "SELECT value FROM core.system_settings WHERE key='sync_interval_seconds'"
        )
        row = await result.fetchone()
    interval = int(row["value"]) if row else default_seconds
    if interval < 60:
        raise RuntimeError("configured sync interval must be at least 60 seconds")
    return interval


def keep_lease_sync(
    job: Job, *, worker_id: str, lease_seconds: int, stop: threading.Event,
) -> None:
    """Renew ownership outside the worker event loop.

    Prediction and snapshot calculation can temporarily monopolize the event
    loop. A dedicated PostgreSQL connection prevents that from expiring a live
    job and also keeps the worker heartbeat current during long handlers.
    """
    interval = max(1, lease_seconds // 3)
    while not stop.wait(interval):
        try:
            with psycopg.connect(build_database_url(), autocommit=True) as connection:
                result = connection.execute(
                    """UPDATE core.jobs
                          SET heartbeat_at=NOW(), lease_expires_at=NOW() + (%s * INTERVAL '1 second'),
                              updated_at=NOW()
                        WHERE id=%s AND status='running' AND locked_by=%s
                          AND lease_expires_at > NOW()""",
                    (lease_seconds, job.id, job.owner_token),
                )
                if result.rowcount != 1:
                    logger.warning("job %s lease ownership was lost", job.id)
                    return
                connection.execute(
                    """UPDATE core.worker_heartbeats SET heartbeat_at=NOW(), status='running',
                              current_job_id=%s, updated_at=NOW() WHERE worker_id=%s""",
                    (job.id, worker_id),
                )
        except Exception:
            logger.exception("unable to renew lease for job %s", job.id)


async def run() -> None:
    worker_id = os.getenv("WORKER_ID", "football-worker-1")
    poll_seconds = float(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "5"))
    lease_seconds = int(os.getenv("WORKER_LEASE_SECONDS", "120"))
    sync_interval_seconds = int(os.getenv("SYNC_INTERVAL_SECONDS", "3600"))
    if sync_interval_seconds < 60:
        raise RuntimeError("SYNC_INTERVAL_SECONDS must be at least 60")
    await open_connection_pool()
    try:
        while True:
            sync_interval_seconds = await configured_sync_interval(sync_interval_seconds)
            now = datetime.now(timezone.utc)
            idempotency_key, next_sync_at = sync_schedule(now, sync_interval_seconds)
            scheduled = await JobQueue.enqueue(
                pool,
                job_type="sync_pipeline",
                idempotency_key=idempotency_key,
                payload=sync_payload(),
                timeout_seconds=max(900, sync_interval_seconds),
            )
            if scheduled:
                logger.info("scheduled sync pipeline %s", idempotency_key)
            recovered = await JobQueue.recover_expired(pool)
            if recovered:
                logger.warning("recovered %s expired job lease(s)", recovered)
            # claim() returns only after attempt_count and lease ownership have
            # committed. No connection or row lock is held during execute().
            job = await JobQueue.claim(pool, worker_id=worker_id, lease_seconds=lease_seconds)
            if job is None:
                await WorkerOperations.heartbeat(
                    pool,
                    worker_id=worker_id,
                    status="idle",
                    schedule_interval_seconds=sync_interval_seconds,
                    next_sync_at=next_sync_at,
                    metadata={"scheduler": "postgres-idempotent"},
                )
                await asyncio.sleep(poll_seconds)
                continue
            await WorkerOperations.heartbeat(
                pool,
                worker_id=worker_id,
                status="running",
                schedule_interval_seconds=sync_interval_seconds,
                next_sync_at=next_sync_at,
                current_job_id=job.id,
                metadata={"job_type": job.job_type},
            )
            lease_stop = threading.Event()
            lease_task = asyncio.create_task(asyncio.to_thread(
                keep_lease_sync, job, worker_id=worker_id,
                lease_seconds=lease_seconds, stop=lease_stop,
            ))
            try:
                result_payload = await asyncio.wait_for(execute(job), timeout=job.timeout_seconds)
            except TimeoutError:
                logger.error("job %s exceeded its %s second timeout", job.id, job.timeout_seconds)
                saved = await JobQueue.fail(
                    pool, job=job, error="timeout",
                    failure_payload={"reason": "timeout"},
                )
            except Exception as exc:
                failure = safe_failure(exc)
                logger.error(
                    "job %s failed: error_type=%s reason=%s stage=%s",
                    job.id, type(exc).__name__, failure["reason"], failure.get("stage", "—"),
                )
                detail = failure["reason"]
                if failure.get("http_status"):
                    detail += f" (HTTP {failure['http_status']})"
                saved = await JobQueue.fail(pool, job=job, error=detail, failure_payload=failure)
            else:
                saved = await JobQueue.complete(pool, job=job, result_payload=result_payload)
            finally:
                lease_stop.set()
                await lease_task
            if not saved:
                logger.error("job %s completion was rejected because lease ownership was lost", job.id)
    finally:
        try:
            _, next_sync_at = sync_schedule(datetime.now(timezone.utc), sync_interval_seconds)
            await WorkerOperations.heartbeat(
                pool,
                worker_id=worker_id,
                status="stopping",
                schedule_interval_seconds=sync_interval_seconds,
                next_sync_at=next_sync_at,
            )
        except Exception:
            logger.exception("unable to record worker shutdown")
        await close_connection_pool()


if __name__ == "__main__":
    asyncio.run(run())
