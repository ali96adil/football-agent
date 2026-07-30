from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.feature_engineering.domain.feature_vector import (
    FeatureVector,
)
from app.prediction.domain.match_prediction import (
    MatchPrediction,
)
from app.prediction.domain.prediction_record import (
    PredictionRecord,
)


class PredictionRecordFactory:
    """
    Convert an in-memory prediction into a persistable
    PredictionRecord.
    """

    @classmethod
    def build(
        cls,
        *,
        feature_vector: FeatureVector,
        prediction: MatchPrediction,
        fixture_id: UUID | None = None,
        kickoff_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PredictionRecord:
        top_score = (
            prediction.most_likely_scores[0]
            if prediction.most_likely_scores
            else None
        )

        expected_goals = prediction.expected_goals

        return PredictionRecord(
            fixture_id=fixture_id,
            competition_id=feature_vector.competition_id,
            season_id=feature_vector.season_id,
            home_team_id=feature_vector.home_team_id,
            away_team_id=feature_vector.away_team_id,
            home_snapshot_id=feature_vector.home_snapshot_id,
            away_snapshot_id=feature_vector.away_snapshot_id,
            kickoff_at=kickoff_at,
            home_expected_goals=expected_goals.home,
            away_expected_goals=expected_goals.away,
            total_expected_goals=expected_goals.total,
            home_win_probability=(
                prediction.home_win_probability
            ),
            draw_probability=prediction.draw_probability,
            away_win_probability=(
                prediction.away_win_probability
            ),
            btts_yes_probability=(
                prediction.btts_yes_probability
            ),
            btts_no_probability=(
                prediction.btts_no_probability
            ),
            over_2_5_probability=(
                prediction.over_2_5_probability
            ),
            under_2_5_probability=(
                prediction.under_2_5_probability
            ),
            predicted_outcome=(
                prediction.predicted_outcome
            ),
            most_likely_home_goals=(
                top_score.home_goals
                if top_score is not None
                else None
            ),
            most_likely_away_goals=(
                top_score.away_goals
                if top_score is not None
                else None
            ),
            most_likely_score_probability=(
                top_score.probability
                if top_score is not None
                else None
            ),
            confidence=expected_goals.confidence,
            expected_goals_model_version=(
                expected_goals.model_version
            ),
            probability_model_version=(
                prediction.model_version
            ),
            feature_vector=feature_vector.as_dict(),
            most_likely_scores=[
                score.as_dict()
                for score in prediction.most_likely_scores
            ],
            metadata=dict(metadata or {}),
        )
