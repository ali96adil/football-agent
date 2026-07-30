from __future__ import annotations

from typing import Any

from app.domain.team_snapshot import TeamSnapshot
from app.feature_engineering.builders.match_feature_builder import (
    MatchFeatureBuilder,
)
from app.feature_engineering.domain.feature_vector import (
    FeatureVector,
)


class FeatureEngineeringService:
    """
    Orchestrates feature engineering for prediction.

    This service does not calculate features itself.
    It coordinates feature generation from validated team snapshots.
    """

    @staticmethod
    async def build_feature_vector(
        *,
        home_snapshot: TeamSnapshot,
        away_snapshot: TeamSnapshot,
        metadata: dict[str, Any] | None = None,
    ) -> FeatureVector:
        return MatchFeatureBuilder.build(
            home_snapshot=home_snapshot,
            away_snapshot=away_snapshot,
            metadata=metadata,
        )