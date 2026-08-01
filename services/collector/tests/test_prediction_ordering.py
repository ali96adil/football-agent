from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

from app.repositories.prediction_query_repository import PredictionQueryRepository
from app.repositories.fixtures_repository import get_scheduled_fixtures


class PredictionOrderingTests(unittest.IsolatedAsyncioTestCase):
    async def query(self, view: str) -> str:
        cursor = MagicMock()
        cursor.fetchall = AsyncMock(return_value=[])
        connection = MagicMock()
        connection.execute = AsyncMock(return_value=cursor)
        await PredictionQueryRepository().get_predictions(connection, view=view)
        return connection.execute.await_args.args[0]

    async def test_upcoming_is_nearest_first_with_stable_nulls_last_order(self) -> None:
        query = await self.query("upcoming")
        self.assertIn("mp.kickoff_at ASC NULLS LAST, mp.fixture_id ASC", query)
        self.assertIn("mp.kickoff_at > NOW()", query)

    async def test_completed_is_separate_and_newest_first(self) -> None:
        query = await self.query("completed")
        self.assertIn("mp.result_confirmed = TRUE", query)
        self.assertIn("mp.kickoff_at DESC NULLS LAST, mp.fixture_id ASC", query)

    async def test_fixture_pagination_orders_before_limit(self) -> None:
        cursor=MagicMock();cursor.fetchall=AsyncMock(return_value=[])
        connection=MagicMock();connection.execute=AsyncMock(return_value=cursor)
        await get_scheduled_fixtures(connection,limit=10)
        query=connection.execute.await_args.args[0]
        self.assertLess(query.index("ORDER BY kickoff_at ASC NULLS LAST, id ASC"),query.index("LIMIT %s"))


if __name__ == "__main__":
    unittest.main()
