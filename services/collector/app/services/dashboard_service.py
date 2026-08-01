import os

from app.db.connection import pool
from app.repositories.dashboard_repository import DashboardRepository


class DashboardService:
    def __init__(self) -> None:
        self.repository = DashboardRepository()

    async def get_dashboard(self) -> dict:
        async with pool.connection() as connection:
            stats = await self.repository.get_dashboard_stats(
                connection
            )
            operations = await self.repository.get_operations(connection)

        configured_sources = {
            "football_data": bool(os.getenv("FOOTBALL_DATA_API_KEY", "").strip()),
            "api_football": bool(os.getenv("API_FOOTBALL_KEY", "").strip()),
            "sportmonks": bool(os.getenv("SPORTMONKS_API_KEY", "").strip()),
            "thesportsdb": bool(os.getenv("THESPORTSDB_API_KEY", "").strip()),
        }
        sources = [
            {
                **source,
                "configured": configured_sources.get(source["code"], False),
                "scheduled": source["code"] == "football_data",
            }
            for source in operations["sources"]
        ]
        data_mode = (
            "real"
            if operations["last_data_update_at"] is not None
            else "unverified"
        )

        return {
            "system": {
                "status": "online",
                "version": os.getenv("APP_VERSION", "1.0.0-dev.5"),
                "revision": os.getenv("GIT_REVISION", "unknown")[:12],
                "release_stage": "development",
            },
            "stats": stats,
            "operations": {
                **operations,
                "sources": sources,
                "data_mode": data_mode,
            },
        }


dashboard_service = DashboardService()
