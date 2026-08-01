"""Durable PostgreSQL job queue primitives used by the worker only."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class Job:
    id: str
    job_type: str
    idempotency_key: str
    payload: dict[str, Any]
    attempt_count: int
    max_attempts: int
    timeout_seconds: int
    owner_token: str


class JobQueue:
    """Lease-based queue safe for more than one worker process."""

    @staticmethod
    async def reserve_sync_slot(connection: Any) -> bool:
        """Serialize checks and reject any overlapping sync pipeline."""
        await connection.execute(
            "SELECT pg_advisory_xact_lock(hashtext('football-agent:sync-pipeline'))"
        )
        active = await connection.execute(
            """SELECT 1 FROM core.jobs
                 WHERE job_type='sync_pipeline'
                   AND status IN ('queued','running','retry')
                 LIMIT 1"""
        )
        return await active.fetchone() is None

    @staticmethod
    async def enqueue(
        pool: Any,
        *,
        job_type: str,
        idempotency_key: str,
        payload: dict[str, Any] | None = None,
        max_attempts: int = 3,
        timeout_seconds: int = 300,
    ) -> bool:
        """Insert once for a stable external-operation idempotency key."""
        async with pool.connection() as connection:
            async with connection.transaction():
                if job_type == "sync_pipeline":
                    # Serialize manual and scheduled syncs, whose external side
                    # effects are idempotent but expensive and rate limited.
                    if not await JobQueue.reserve_sync_slot(connection):
                        return False
                result = await connection.execute(
                    """
                    INSERT INTO core.jobs (job_type, idempotency_key, payload, max_attempts, timeout_seconds)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (job_type, idempotency_key) DO NOTHING
                    """,
                    (
                        job_type,
                        idempotency_key,
                        Jsonb(payload or {}),
                        max_attempts,
                        timeout_seconds,
                    ),
                )
        return result.rowcount == 1

    @staticmethod
    async def recover_expired(pool: Any) -> int:
        """Recover jobs stranded by a reboot or a killed worker."""
        async with pool.connection() as connection:
            async with connection.transaction():
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
    async def claim(pool: Any, *, worker_id: str, lease_seconds: int) -> Job | None:
        """Claim and commit exactly one job before returning it to a handler."""
        owner_token = f"{worker_id}:{uuid4()}"
        async with pool.connection() as connection:
            # This is the first operation on a freshly checked-out connection,
            # so this is a real outer transaction, never a nested savepoint.
            async with connection.transaction():
                result = await connection.execute(
                    """
                    WITH candidate AS (
                        SELECT id
                          FROM core.jobs
                         WHERE status IN ('queued', 'retry')
                           AND attempt_count < max_attempts
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
                    RETURNING jobs.id, jobs.job_type, jobs.idempotency_key, jobs.payload,
                              jobs.attempt_count, jobs.max_attempts, jobs.timeout_seconds
                    """,
                    (owner_token, lease_seconds),
                )
                row = await result.fetchone()
        return Job(**row, owner_token=owner_token) if row else None

    @staticmethod
    async def heartbeat(pool: Any, *, job: Job, lease_seconds: int) -> bool:
        async with pool.connection() as connection:
            async with connection.transaction():
                result = await connection.execute(
                    """
                    UPDATE core.jobs
                       SET heartbeat_at = NOW(), lease_expires_at = NOW() + (%s * INTERVAL '1 second'),
                           updated_at = NOW()
                     WHERE id = %s AND status = 'running' AND locked_by = %s
                       AND lease_expires_at > NOW()
                    """,
                    (lease_seconds, job.id, job.owner_token),
                )
        return result.rowcount == 1

    @staticmethod
    async def complete(pool: Any, *, job: Job, result_payload: dict[str, Any] | None = None) -> bool:
        async with pool.connection() as connection:
            async with connection.transaction():
                result = await connection.execute(
                    """UPDATE core.jobs SET status='succeeded', finished_at=NOW(), result=%s, locked_by=NULL,
                           lease_expires_at=NULL, heartbeat_at=NULL, updated_at=NOW()
                         WHERE id=%s AND status='running' AND locked_by=%s""",
                    (Jsonb(result_payload or {}), job.id, job.owner_token),
                )
        return result.rowcount == 1

    @staticmethod
    async def fail(
        pool: Any, *, job: Job, error: str,
        failure_payload: dict[str, Any] | None = None,
    ) -> bool:
        """Commit a retry or dead-letter transition in its own transaction."""
        async with pool.connection() as connection:
            async with connection.transaction():
                result = await connection.execute(
                    """
                    UPDATE core.jobs
                       SET status = CASE WHEN attempt_count >= max_attempts THEN 'dead_letter' ELSE 'retry' END,
                           run_after = CASE WHEN attempt_count >= max_attempts THEN run_after
                                            ELSE NOW() + (LEAST(300, 5 * attempt_count) * INTERVAL '1 second') END,
                           finished_at = CASE WHEN attempt_count >= max_attempts THEN NOW() ELSE NULL END,
                           locked_by = NULL, lease_expires_at = NULL, heartbeat_at = NULL,
                           last_error = %s, result = %s, updated_at = NOW()
                     WHERE id = %s AND status = 'running' AND locked_by = %s
                    """,
                    (error[:4000], Jsonb(failure_payload or {}), job.id, job.owner_token),
                )
        return result.rowcount == 1
