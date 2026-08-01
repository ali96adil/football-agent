from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/collector"))

from app.jobs import Job  # noqa: E402
from scripts.worker import execute, sync_schedule  # noqa: E402


class WorkerSchedulerTests(unittest.IsolatedAsyncioTestCase):
    def test_schedule_uses_stable_utc_interval_bucket(self) -> None:
        first = datetime(2026, 8, 1, 10, 0, 1, tzinfo=timezone.utc)
        later = datetime(2026, 8, 1, 10, 59, 59, tzinfo=timezone.utc)
        first_key, first_next = sync_schedule(first, 3600)
        later_key, later_next = sync_schedule(later, 3600)
        self.assertEqual(first_key, later_key)
        self.assertEqual(first_next, datetime(2026, 8, 1, 11, 0, tzinfo=timezone.utc))
        self.assertEqual(later_next, first_next)

    @staticmethod
    def job(payload: dict | None = None) -> Job:
        return Job(
            id="job-1", job_type="sync_pipeline", idempotency_key="scheduled:1",
            payload=payload or {}, attempt_count=1, max_attempts=3,
            timeout_seconds=900, owner_token="worker:test",
        )

    async def test_sync_job_dispatches_the_real_pipeline(self) -> None:
        payload = {
            "fixture_days": 7, "prediction_limit": 25, "evaluation_limit": 30,
            "window_size": 8, "calculation_version": "v1-dev-test",
        }
        sync_all = AsyncMock(
            return_value={"status": "success", "errors": [], "duration_seconds": 1.25}
        )
        with patch("app.api.routes.sync.sync_all", sync_all):
            await execute(self.job(payload))
        sync_all.assert_awaited_once_with(
            fixture_days=7, prediction_limit=25, evaluation_limit=30,
            window_size=8, calculation_version="v1-dev-test",
        )

    async def test_collection_failure_is_retried_by_the_queue(self) -> None:
        sync_all = AsyncMock(return_value={
            "status": "partial_success", "errors": [{"stage": "competitions"}],
            "duration_seconds": 0.5,
        })
        with patch("app.api.routes.sync.sync_all", sync_all), self.assertRaisesRegex(
            RuntimeError, "competitions"
        ):
            await execute(self.job())


if __name__ == "__main__":
    unittest.main()
