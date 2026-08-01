"""Background worker entrypoint. The API process never consumes queue jobs."""
from __future__ import annotations

import asyncio
import logging
import os

from app.db.connection import close_connection_pool, open_connection_pool, pool
from app.jobs import Job, JobQueue

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
    raise RuntimeError(f"unsupported job_type: {job.job_type}")


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
    await open_connection_pool()
    try:
        while True:
            recovered = await JobQueue.recover_expired(pool)
            if recovered:
                logger.warning("recovered %s expired job lease(s)", recovered)
            # claim() returns only after attempt_count and lease ownership have
            # committed. No connection or row lock is held during execute().
            job = await JobQueue.claim(pool, worker_id=worker_id, lease_seconds=lease_seconds)
            if job is None:
                await asyncio.sleep(poll_seconds)
                continue
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
        await close_connection_pool()


if __name__ == "__main__":
    asyncio.run(run())
