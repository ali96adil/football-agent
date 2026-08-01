from __future__ import annotations

import unittest
from typing import Any

from psycopg.types.json import Jsonb

from app.jobs import JobQueue


class _AsyncContext:
    def __init__(self, value: Any = None) -> None:
        self.value = value

    async def __aenter__(self) -> Any:
        return self.value

    async def __aexit__(self, *_args: Any) -> None:
        return None


class _Result:
    rowcount = 1


class _Connection:
    def __init__(self) -> None:
        self.parameters: tuple[Any, ...] | None = None

    def transaction(self) -> _AsyncContext:
        return _AsyncContext()

    async def execute(self, _query: str, parameters: tuple[Any, ...]) -> _Result:
        self.parameters = parameters
        return _Result()


class _Pool:
    def __init__(self) -> None:
        self.connection_value = _Connection()

    def connection(self) -> _AsyncContext:
        return _AsyncContext(self.connection_value)


class JobQueueUnitTests(unittest.IsolatedAsyncioTestCase):
    async def test_enqueue_adapts_nested_payload_as_jsonb(self) -> None:
        pool = _Pool()
        payload = {"events": [{"id": 7}], "flags": [True, False]}

        self.assertTrue(
            await JobQueue.enqueue(
                pool,
                job_type="sync",
                idempotency_key="sync-7",
                payload=payload,
            )
        )

        self.assertIsNotNone(pool.connection_value.parameters)
        adapted_payload = pool.connection_value.parameters[2]
        self.assertIsInstance(adapted_payload, Jsonb)
        self.assertEqual(adapted_payload.obj, payload)
