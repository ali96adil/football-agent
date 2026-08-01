from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import AsyncMock, patch

from app.services.dashboard_service import DashboardService


class _ConnectionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_args: Any) -> None:
        return None


class DashboardOperationsTests(unittest.IsolatedAsyncioTestCase):
    async def test_dashboard_marks_only_the_native_pipeline_source_as_scheduled(self) -> None:
        service = DashboardService()
        service.repository.get_dashboard_stats = AsyncMock(return_value={"fixtures": 0})
        service.repository.get_operations = AsyncMock(return_value={
            "sources": [
                {"code": "football_data", "name": "Football Data"},
                {"code": "api_football", "name": "API Football"},
            ],
            "worker": None,
            "jobs": {},
            "last_data_update_at": None,
        })

        with patch("app.services.dashboard_service.pool.connection", return_value=_ConnectionContext()), patch.dict(
            "os.environ",
            {"FOOTBALL_DATA_API_KEY": "configured", "API_FOOTBALL_KEY": "configured"},
            clear=False,
        ):
            dashboard = await service.get_dashboard()

        sources = {source["code"]: source for source in dashboard["operations"]["sources"]}
        self.assertTrue(sources["football_data"]["scheduled"])
        self.assertFalse(sources["api_football"]["scheduled"])
        self.assertEqual(dashboard["operations"]["data_mode"], "unverified")
        self.assertEqual(dashboard["system"]["release_stage"], "development")


if __name__ == "__main__":
    unittest.main()
