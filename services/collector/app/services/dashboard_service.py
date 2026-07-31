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

        return {
            "system": {
                "status": "online",
                "version": "0.2.0",
            },
            "stats": stats,
        }


dashboard_service = DashboardService()
