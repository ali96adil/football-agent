from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.team_snapshot import TeamSnapshot
from app.feature_engineering.domain.feature_vector import FeatureVector
from app.prediction.domain.prediction_record import PredictionRecord
from app.prediction.record_factory import PredictionRecordFactory
from app.prediction.service import PredictionService
from app.repositories.match_predictions_repository import (
    save_prediction,
)


class PredictionPersistenceService:
    """
    Coordinate prediction creation and persistence.

    This service keeps PredictionService independent from PostgreSQL,
    while providing one operation that predicts and saves.
    """

    @classmethod
    async def predict_and_save(
        cls,
        connection: Any,
        *,
        home_snapshot: TeamSnapshot,
        away_snapshot: TeamSnapshot,
        fixture_id: UUID | None = None,
        kickoff_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        max_goals: int | None = None,
        top_scores: int | None = None,
    ) -> PredictionRecord:
        feature_vector = PredictionService.build_feature_vector(
            home_snapshot=home_snapshot,
            away_snapshot=away_snapshot,
            metadata=metadata,
        )

        return await cls.predict_feature_vector_and_save(
            connection,
            feature_vector=feature_vector,
            fixture_id=fixture_id,
            kickoff_at=kickoff_at,
            metadata=metadata,
            max_goals=max_goals,
            top_scores=top_scores,
        )

    @classmethod
    async def predict_feature_vector_and_save(
        cls,
        connection: Any,
        *,
        feature_vector: FeatureVector,
        fixture_id: UUID | None = None,
        kickoff_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        max_goals: int | None = None,
        top_scores: int | None = None,
    ) -> PredictionRecord:
        prediction_arguments: dict[str, Any] = {
            "feature_vector": feature_vector,
        }

        if max_goals is not None:
            prediction_arguments["max_goals"] = max_goals

        if top_scores is not None:
            prediction_arguments["top_scores"] = top_scores

        prediction = PredictionService.predict_from_feature_vector(
            **prediction_arguments,
        )

        record = PredictionRecordFactory.build(
            feature_vector=feature_vector,
            prediction=prediction,
            fixture_id=fixture_id,
            kickoff_at=kickoff_at,
            metadata=metadata,
        )

        return await save_prediction(
            connection,
            prediction=record,
        )
