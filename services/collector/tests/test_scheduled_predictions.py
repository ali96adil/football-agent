from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.services.scheduled_prediction_service import ScheduledPredictionService


class ScheduledPredictionFailureTests(unittest.IsolatedAsyncioTestCase):
    def fixture(self):
        return SimpleNamespace(
            fixture_id=uuid4(),competition_id=uuid4(),season_id=uuid4(),
            home_team_id=uuid4(),away_team_id=uuid4(),
            kickoff_at=datetime.now(timezone.utc)+timedelta(hours=2),
        )

    async def test_missing_history_is_a_safe_skip_not_a_failed_job(self) -> None:
        fixture=self.fixture()
        with (
            patch("app.services.scheduled_prediction_service.get_scheduled_fixtures",AsyncMock(return_value=[fixture])),
            patch.object(ScheduledPredictionService,"_predict_fixture",AsyncMock(side_effect=ValueError("No completed matches found for team secret-id."))),
        ):
            result=await ScheduledPredictionService.run(AsyncMock())
        self.assertEqual(result["status"],"success")
        self.assertEqual(result["skipped"],1)
        self.assertEqual(result["failed"],0)
        self.assertEqual(result["items"][0]["reason"],"insufficient_data")
        self.assertNotIn("secret-id",str(result))

    async def test_technical_failure_is_classified_without_raw_message(self) -> None:
        fixture=self.fixture()
        with (
            patch("app.services.scheduled_prediction_service.get_scheduled_fixtures",AsyncMock(return_value=[fixture])),
            patch.object(ScheduledPredictionService,"_predict_fixture",AsyncMock(side_effect=RuntimeError("postgresql://user:secret@host/db"))),
        ):
            result=await ScheduledPredictionService.run(AsyncMock())
        self.assertEqual(result["status"],"failed")
        self.assertNotIn("secret",str(result))


if __name__ == "__main__": unittest.main()
