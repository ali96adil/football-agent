"""Durable PostgreSQL job queue primitives used by the worker only."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Job:
    id: str
    job_type: str
    payload: dict[str, Any]
    attempt_count: int
    max_attempts: int
    timeout_seconds: int


class JobQueue:
    """Lease-based queue safe for more than one worker process."""

    @staticmethod
    async def enqueue(
        connection: Any,
        *,
        job_type: str,
        idempotency_key: str,
        payload: dict[str, Any] | None = None,
        max_attempts: int = 3,
        timeout_seconds: int = 300,
    ) -> None:
        await connection.execute(
            """
            INSERT INTO core.jobs (job_type, idempotency_key, payload, max_attempts, timeout_seconds)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (job_type, idempotency_key) DO NOTHING
            """,
            (job_type, idempotency_key, payload or {}, max_attempts, timeout_seconds),
        )

    @staticmethod
    async def recover_expired(connection: Any) -> int:
        """Recover jobs stranded by a reboot or a killed worker."""
        result = await connection.execute(
            """
            UPDATE core.jobs
               SET status = CASE WHEN attempt_count >= max_attempts
                                 THEN 'dead_letter' ELSE 'retry' END,
                   finished_at = CASE WHEN attempt_count >= max_attempts THEN NOW() ELSE NULL END,
                   locked_by = NULL,
                   lease_expires_at = NULL,
                   heartbeat_at = NULL,
                   last_error = COALESCE(last_error, 'worker lease expired'),
                   updated_at = NOW()
             WHERE status = 'running'
               AND lease_expires_at <= NOW()
            """
        )
        return result.rowcount

    @staticmethod
    async def claim(connection: Any, *, worker_id: str, lease_seconds: int) -> Job | None:
        """Claim exactly one available job without blocking other workers."""
        async with connection.transaction():
            result = await connection.execute(
                """
                WITH candidate AS (
                    SELECT id
                      FROM core.jobs
                     WHERE status IN ('queued', 'retry')
                       AND run_after <= NOW()
                     ORDER BY created_at
                     FOR UPDATE SKIP LOCKED
                     LIMIT 1
                )
                UPDATE core.jobs AS jobs
                   SET status = 'running',
                       attempt_count = jobs.attempt_count + 1,
                       locked_by = %s,
                       started_at = COALESCE(jobs.started_at, NOW()),
                       heartbeat_at = NOW(),
                       lease_expires_at = NOW() + (%s * INTERVAL '1 second'),
                       updated_at = NOW()
                  FROM candidate
                 WHERE jobs.id = candidate.id
                RETURNING jobs.id, jobs.job_type, jobs.payload, jobs.attempt_count,
                          jobs.max_attempts, jobs.timeout_seconds
                """,
                (worker_id, lease_seconds),
            )
            row = await result.fetchone()
        return Job(**row) if row else None

    @staticmethod
    async def heartbeat(connection: Any, *, job_id: str, worker_id: str, lease_seconds: int) -> bool:
        result = await connection.execute(
            """
            UPDATE core.jobs
               SET heartbeat_at = NOW(), lease_expires_at = NOW() + (%s * INTERVAL '1 second'),
                   updated_at = NOW()
             WHERE id = %s AND status = 'running' AND locked_by = %s
            """,
            (lease_seconds, job_id, worker_id),
        )
        return result.rowcount == 1

    @staticmethod
    async def finish(connection: Any, *, job: Job, worker_id: str, error: str | None = None) -> None:
        if error is None:
            await connection.execute(
                """UPDATE core.jobs SET status='succeeded', finished_at=NOW(), locked_by=NULL,
                       lease_expires_at=NULL, heartbeat_at=NULL, updated_at=NOW()
                     WHERE id=%s AND status='running' AND locked_by=%s""",
                (job.id, worker_id),
            )
            return
        await connection.execute(
            """
            UPDATE core.jobs
               SET status = CASE WHEN attempt_count >= max_attempts THEN 'dead_letter' ELSE 'retry' END,
                   run_after = CASE WHEN attempt_count >= max_attempts THEN run_after
                                    ELSE NOW() + (LEAST(300, 5 * attempt_count) * INTERVAL '1 second') END,
                   finished_at = CASE WHEN attempt_count >= max_attempts THEN NOW() ELSE NULL END,
                   locked_by = NULL, lease_expires_at = NULL, heartbeat_at = NULL,
                   last_error = %s, updated_at = NOW()
             WHERE id = %s AND status = 'running' AND locked_by = %s
            """,
            (error[:4000], job.id, worker_id),
        )
