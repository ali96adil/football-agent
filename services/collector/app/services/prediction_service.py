from app.db.connection import pool
from app.repositories.prediction_query_repository import (
    PredictionQueryRepository,
)


class PredictionService:
    def __init__(self) -> None:
        self.repository = PredictionQueryRepository()

    async def get_predictions(
        self,
        limit: int = 50,
        offset: int = 0,
        view: str = "upcoming",
    ):
        async with pool.connection() as connection:
            return await self.repository.get_predictions(
                connection,
                limit=limit,
                offset=offset,
                view=view,
            )

    async def get_prediction(
        self,
        fixture_id: str,
    ):
        async with pool.connection() as connection:
            return await self.repository.get_prediction_by_fixture(
                connection,
                fixture_id,
            )


prediction_service = PredictionService()