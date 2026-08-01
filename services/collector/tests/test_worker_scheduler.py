from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/collector"))

from app.jobs import Job  # noqa: E402
from app.job_errors import JobExecutionError  # noqa: E402
from scripts.worker import execute, keep_lease_sync, sync_schedule  # noqa: E402


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
    def job(payload: dict | None = None, job_type: str = "sync_pipeline") -> Job:
        return Job(
            id="job-1", job_type=job_type, idempotency_key="scheduled:1",
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
        with patch("app.api.routes.sync.sync_all", sync_all), self.assertRaises(
            JobExecutionError
        ) as raised:
            await execute(self.job())
        self.assertEqual(raised.exception.stage, "competitions")

    async def test_snapshot_target_scope_is_always_explicit(self) -> None:
        connection = MagicMock()
        connection_context = AsyncMock()
        connection_context.__aenter__.return_value = connection
        get_team_targets = AsyncMock(return_value=[])
        with (
            patch("app.db.connection.pool.connection", return_value=connection_context),
            patch("scripts.build_all_snapshots.get_team_targets", get_team_targets),
        ):
            await execute(self.job({"limit": 12}, "build_snapshots"))
        get_team_targets.assert_awaited_once_with(
            connection, competition_id=None, season_id=None, limit=12
        )

    async def test_prediction_partial_success_is_not_marked_successful(self) -> None:
        service = AsyncMock(return_value={"status": "partial_success", "failed": 1})
        connection_context = AsyncMock()
        connection_context.__aenter__.return_value = MagicMock()
        with (
            patch("app.db.connection.pool.connection", return_value=connection_context),
            patch("app.services.scheduled_prediction_service.ScheduledPredictionService.run", service),
            self.assertRaisesRegex(RuntimeError, "completed with failures"),
        ):
            await execute(self.job({}, "run_predictions"))

    def test_long_job_renews_lease_outside_event_loop(self) -> None:
        connection = MagicMock()
        renewal = MagicMock(rowcount=1)
        connection.execute.side_effect = [renewal, MagicMock()]
        context = MagicMock()
        context.__enter__.return_value = connection
        stop = MagicMock()
        stop.wait.side_effect = [False, True]
        with patch("scripts.worker.psycopg.connect", return_value=context):
            keep_lease_sync(
                self.job(), worker_id="worker-a", lease_seconds=3, stop=stop
            )
        self.assertEqual(connection.execute.call_count, 2)
        self.assertIn("lease_expires_at", connection.execute.call_args_list[0].args[0])


if __name__ == "__main__":
    unittest.main()
