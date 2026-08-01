from __future__ import annotations

from datetime import datetime
from typing import Any

from psycopg.types.json import Jsonb


class WorkerOperations:
    @staticmethod
    async def heartbeat(
        pool: Any,
        *,
        worker_id: str,
        status: str,
        schedule_interval_seconds: int,
        next_sync_at: datetime,
        current_job_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        async with pool.connection() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO core.worker_heartbeats (
                        worker_id, status, heartbeat_at, current_job_id,
                        scheduler_enabled, schedule_interval_seconds,
                        next_sync_at, metadata, updated_at
                    )
                    VALUES (%s, %s, NOW(), %s, TRUE, %s, %s, %s, NOW())
                    ON CONFLICT (worker_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        heartbeat_at = NOW(),
                        current_job_id = EXCLUDED.current_job_id,
                        scheduler_enabled = EXCLUDED.scheduler_enabled,
                        schedule_interval_seconds = EXCLUDED.schedule_interval_seconds,
                        next_sync_at = EXCLUDED.next_sync_at,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    (
                        worker_id,
                        status,
                        current_job_id,
                        schedule_interval_seconds,
                        next_sync_at,
                        Jsonb(metadata or {}),
                    ),
                )
