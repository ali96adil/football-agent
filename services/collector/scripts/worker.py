"""Background worker entrypoint. The API process never consumes queue jobs."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from app.db.connection import close_connection_pool, open_connection_pool, pool
from app.jobs import Job, JobQueue
from app.operations import WorkerOperations

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("football-worker")


async def execute(job: Job) -> None:
    """Run an idempotent handler keyed by job.idempotency_key.

    A database lease provides at-least-once delivery, not distributed exactly
    once semantics. Future external side effects must pass the stable key to a
    provider that supports idempotency, or persist an outbox/result first.
    """
    if job.job_type == "noop":
        return
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
            stages = ", ".join(sorted(failed_collection_stages))
            raise RuntimeError(f"sync pipeline collection failed at: {stages}")
        logger.info(
            "sync pipeline finished with status=%s duration=%s",
            result["status"],
            result["duration_seconds"],
        )
        return
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


async def keep_lease(job: Job, *, worker_id: str, lease_seconds: int) -> None:
    """Renew a long-running job lease without sharing its execution connection."""
    while True:
        await asyncio.sleep(max(1, lease_seconds // 3))
        renewed = await JobQueue.heartbeat(pool, job=job, lease_seconds=lease_seconds)
        if not renewed:
            logger.warning("job %s lease ownership was lost", job.id)
            return


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
            lease_task = asyncio.create_task(
                keep_lease(job, worker_id=worker_id, lease_seconds=lease_seconds)
            )
            try:
                await asyncio.wait_for(execute(job), timeout=job.timeout_seconds)
            except TimeoutError:
                logger.error("job %s exceeded its %s second timeout", job.id, job.timeout_seconds)
                saved = await JobQueue.fail(pool, job=job, error="job timeout")
            except Exception as exc:
                logger.exception("job %s failed", job.id)
                saved = await JobQueue.fail(pool, job=job, error=str(exc))
            else:
                saved = await JobQueue.complete(pool, job=job)
            finally:
                lease_task.cancel()
                try:
                    await lease_task
                except asyncio.CancelledError:
                    pass
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
