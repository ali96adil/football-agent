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
    """Foundation handler. Future PRs register sync/training/report job types here."""
    if job.job_type == "noop":
        return
    raise RuntimeError(f"unsupported job_type: {job.job_type}")


async def keep_lease(job: Job, *, worker_id: str, lease_seconds: int) -> None:
    """Renew a long-running job lease without sharing its execution connection."""
    while True:
        await asyncio.sleep(max(1, lease_seconds // 3))
        async with pool.connection() as heartbeat_connection:
            renewed = await JobQueue.heartbeat(
                heartbeat_connection,
                job_id=job.id,
                worker_id=worker_id,
                lease_seconds=lease_seconds,
            )
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
            async with pool.connection() as connection:
                recovered = await JobQueue.recover_expired(connection)
                if recovered:
                    logger.warning("recovered %s expired job lease(s)", recovered)
                job = await JobQueue.claim(connection, worker_id=worker_id, lease_seconds=lease_seconds)
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
                    await JobQueue.finish(connection, job=job, worker_id=worker_id, error="job timeout")
                except Exception as exc:
                    logger.exception("job %s failed", job.id)
                    await JobQueue.finish(connection, job=job, worker_id=worker_id, error=str(exc))
                else:
                    await JobQueue.finish(connection, job=job, worker_id=worker_id)
                finally:
                    lease_task.cancel()
                    try:
                        await lease_task
                    except asyncio.CancelledError:
                        pass
    finally:
        await close_connection_pool()


if __name__ == "__main__":
    asyncio.run(run())
