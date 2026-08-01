from __future__ import annotations

import unittest
from datetime import datetime, timezone
from typing import Any

from psycopg.types.json import Jsonb

from app.operations import WorkerOperations


class _AsyncContext:
    def __init__(self, value: Any = None) -> None:
        self.value = value

    async def __aenter__(self) -> Any:
        return self.value

    async def __aexit__(self, *_args: Any) -> None:
        return None


class _Connection:
    def __init__(self) -> None:
        self.parameters: tuple[Any, ...] | None = None

    def transaction(self) -> _AsyncContext:
        return _AsyncContext()

    async def execute(self, _query: str, parameters: tuple[Any, ...]) -> None:
        self.parameters = parameters


class _Pool:
    def __init__(self) -> None:
        self.connection_value = _Connection()

    def connection(self) -> _AsyncContext:
        return _AsyncContext(self.connection_value)


class WorkerOperationsTests(unittest.IsolatedAsyncioTestCase):
    async def test_heartbeat_persists_scheduler_metadata_as_jsonb(self) -> None:
        pool = _Pool()
        next_sync_at = datetime(2026, 8, 1, 11, 0, tzinfo=timezone.utc)
        await WorkerOperations.heartbeat(
            pool, worker_id="worker-1", status="idle",
            schedule_interval_seconds=3600, next_sync_at=next_sync_at,
            metadata={"scheduler": "postgres-idempotent"},
        )
        parameters = pool.connection_value.parameters
        self.assertIsNotNone(parameters)
        self.assertEqual(parameters[:5], ("worker-1", "idle", None, 3600, next_sync_at))
        self.assertIsInstance(parameters[5], Jsonb)
        self.assertEqual(parameters[5].obj, {"scheduler": "postgres-idempotent"})


if __name__ == "__main__":
    unittest.main()
