from __future__ import annotations

import asyncio
import os
import unittest

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import build_database_url
from app.jobs import JobQueue


@unittest.skipUnless(
    os.getenv("RUN_POSTGRES_INTEGRATION") == "1",
    "set RUN_POSTGRES_INTEGRATION=1 against an ephemeral migrated PostgreSQL database",
)
class PostgreSQLJobQueueIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.pool = AsyncConnectionPool(
            conninfo=build_database_url(),
            min_size=1,
            max_size=6,
            open=False,
            kwargs={"row_factory": dict_row},
        )
        await self.pool.open()
        await self.pool.wait()
        async with self.pool.connection() as connection:
            async with connection.transaction():
                await connection.execute("DELETE FROM core.jobs")

    async def asyncTearDown(self) -> None:
        await self.pool.close()

    async def enqueue(self, key: str = "test", *, max_attempts: int = 3) -> None:
        created = await JobQueue.enqueue(
            self.pool,
            job_type="noop",
            idempotency_key=key,
            max_attempts=max_attempts,
        )
        self.assertTrue(created)

    async def row(self) -> dict:
        async with self.pool.connection() as connection:
            result = await connection.execute("SELECT * FROM core.jobs")
            return await result.fetchone()

    async def make_due(self) -> None:
        async with self.pool.connection() as connection:
            async with connection.transaction():
                await connection.execute("UPDATE core.jobs SET run_after = NOW()")

    async def expire_lease(self) -> None:
        async with self.pool.connection() as connection:
            async with connection.transaction():
                await connection.execute(
                    "UPDATE core.jobs SET lease_expires_at = NOW() - INTERVAL '1 second'"
                )

    async def test_two_workers_cannot_claim_the_same_job(self) -> None:
        await self.enqueue()
        claims = await asyncio.gather(
            JobQueue.claim(self.pool, worker_id="worker-a", lease_seconds=30),
            JobQueue.claim(self.pool, worker_id="worker-b", lease_seconds=30),
        )
        claimed = [job for job in claims if job is not None]
        self.assertEqual(len(claimed), 1)
        self.assertEqual((await self.row())["attempt_count"], 1)

    async def test_heartbeat_extends_a_committed_lease(self) -> None:
        await self.enqueue()
        job = await JobQueue.claim(self.pool, worker_id="worker-a", lease_seconds=2)
        self.assertIsNotNone(job)
        before = (await self.row())["lease_expires_at"]
        self.assertTrue(await JobQueue.heartbeat(self.pool, job=job, lease_seconds=60))
        after = (await self.row())["lease_expires_at"]
        self.assertGreater(after, before)

    async def test_expired_lease_is_recovered_without_losing_attempt(self) -> None:
        await self.enqueue()
        await JobQueue.claim(self.pool, worker_id="worker-a", lease_seconds=30)
        await self.expire_lease()
        self.assertEqual(await JobQueue.recover_expired(self.pool), 1)
        row = await self.row()
        self.assertEqual(row["status"], "retry")
        self.assertEqual(row["attempt_count"], 1)
        self.assertIsNone(row["locked_by"])

    async def test_retry_then_dead_letter_honors_max_attempts(self) -> None:
        await self.enqueue(max_attempts=2)
        first = await JobQueue.claim(self.pool, worker_id="worker-a", lease_seconds=30)
        self.assertTrue(await JobQueue.fail(self.pool, job=first, error="first failure"))
        self.assertEqual((await self.row())["status"], "retry")
        await self.make_due()
        second = await JobQueue.claim(self.pool, worker_id="worker-b", lease_seconds=30)
        self.assertTrue(await JobQueue.fail(self.pool, job=second, error="second failure"))
        row = await self.row()
        self.assertEqual(row["status"], "dead_letter")
        self.assertEqual(row["attempt_count"], 2)

    async def test_claim_is_visible_before_handler_would_start(self) -> None:
        await self.enqueue()
        job = await JobQueue.claim(self.pool, worker_id="worker-a", lease_seconds=30)
        row = await self.row()
        self.assertEqual(str(row["id"]), str(job.id))
        self.assertEqual(row["status"], "running")
        self.assertEqual(row["attempt_count"], 1)
        self.assertEqual(row["locked_by"], job.owner_token)

    async def test_power_loss_after_claim_keeps_attempt_count(self) -> None:
        await self.enqueue(max_attempts=1)
        await JobQueue.claim(self.pool, worker_id="worker-a", lease_seconds=30)
        await self.expire_lease()
        await JobQueue.recover_expired(self.pool)
        row = await self.row()
        self.assertEqual(row["attempt_count"], 1)
        self.assertEqual(row["status"], "dead_letter")

    async def test_enqueue_idempotency_rejects_duplicate_side_effect_key(self) -> None:
        await self.enqueue(key="provider-operation-42")
        duplicate = await JobQueue.enqueue(
            self.pool,
            job_type="noop",
            idempotency_key="provider-operation-42",
        )
        self.assertFalse(duplicate)

    async def test_sync_pipeline_cannot_overlap_across_distinct_keys(self) -> None:
        first = await JobQueue.enqueue(
            self.pool, job_type="sync_pipeline", idempotency_key="manual-a"
        )
        second = await JobQueue.enqueue(
            self.pool, job_type="sync_pipeline", idempotency_key="scheduled-b"
        )
        self.assertTrue(first)
        self.assertFalse(second)
