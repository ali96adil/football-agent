from __future__ import annotations

from typing import Any

from app.domain.team_snapshot import TeamSnapshot
from app.feature_engineering.builders import MatchFeatureBuilder
from app.feature_engineering.domain.feature_vector import FeatureVector
from app.prediction.domain.match_prediction import MatchPrediction
from app.prediction.engines.expected_goals_engine import (
    ExpectedGoalsEngine,
)
from app.prediction.engines.poisson_engine import PoissonEngine


class PredictionService:
    """
    Orchestrate the complete match prediction pipeline.

    Team snapshots
        -> feature vector
        -> expected goals
        -> Poisson probabilities
        -> match prediction
    """

    @classmethod
    def predict(
        cls,
        *,
        home_snapshot: TeamSnapshot,
        away_snapshot: TeamSnapshot,
        metadata: dict[str, Any] | None = None,
        max_goals: int = PoissonEngine.DEFAULT_MAX_GOALS,
        top_scores: int = PoissonEngine.DEFAULT_TOP_SCORES,
    ) -> MatchPrediction:
        feature_vector = cls.build_feature_vector(
            home_snapshot=home_snapshot,
            away_snapshot=away_snapshot,
            metadata=metadata,
        )

        return cls.predict_from_feature_vector(
            feature_vector=feature_vector,
            max_goals=max_goals,
            top_scores=top_scores,
        )

    @staticmethod
    def build_feature_vector(
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

    @staticmethod
    def predict_from_feature_vector(
        *,
        feature_vector: FeatureVector,
        max_goals: int = PoissonEngine.DEFAULT_MAX_GOALS,
        top_scores: int = PoissonEngine.DEFAULT_TOP_SCORES,
    ) -> MatchPrediction:
        expected_goals = ExpectedGoalsEngine.calculate(
            feature_vector
        )

        return PoissonEngine.calculate(
            expected_goals,
            max_goals=max_goals,
            top_scores=top_scores,
        )

    @classmethod
    def predict_with_details(
        cls,
        *,
        home_snapshot: TeamSnapshot,
        away_snapshot: TeamSnapshot,
        metadata: dict[str, Any] | None = None,
        max_goals: int = PoissonEngine.DEFAULT_MAX_GOALS,
        top_scores: int = PoissonEngine.DEFAULT_TOP_SCORES,
    ) -> dict[str, Any]:
        feature_vector = cls.build_feature_vector(
            home_snapshot=home_snapshot,
            away_snapshot=away_snapshot,
            metadata=metadata,
        )

        prediction = cls.predict_from_feature_vector(
            feature_vector=feature_vector,
            max_goals=max_goals,
            top_scores=top_scores,
        )

        return {
            "home_team_id": str(feature_vector.home_team_id),
            "away_team_id": str(feature_vector.away_team_id),
            "competition_id": str(feature_vector.competition_id),
            "season_id": str(feature_vector.season_id),
            "home_snapshot_id": (
                str(feature_vector.home_snapshot_id)
                if feature_vector.home_snapshot_id is not None
                else None
            ),
            "away_snapshot_id": (
                str(feature_vector.away_snapshot_id)
                if feature_vector.away_snapshot_id is not None
                else None
            ),
            "feature_vector": feature_vector.as_dict(),
            "prediction": prediction.as_dict(),
        }
