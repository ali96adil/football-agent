from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.prediction.domain.expected_goals import ExpectedGoals
from app.prediction.domain.score_probability import ScoreProbability


@dataclass(frozen=True, slots=True)
class MatchPrediction:
    expected_goals: ExpectedGoals

    home_win_probability: Decimal
    draw_probability: Decimal
    away_win_probability: Decimal

    btts_yes_probability: Decimal
    over_2_5_probability: Decimal
    under_2_5_probability: Decimal

    most_likely_scores: tuple[ScoreProbability, ...] = field(
        default_factory=tuple
    )

    model_version: str = "poisson-v1"

    def __post_init__(self) -> None:
        probabilities = (
            self.home_win_probability,
            self.draw_probability,
            self.away_win_probability,
            self.btts_yes_probability,
            self.over_2_5_probability,
            self.under_2_5_probability,
        )

        for probability in probabilities:
            if not Decimal("0") <= probability <= Decimal("1"):
                raise ValueError(
                    "All probabilities must be between 0 and 1."
                )

    @property
    def btts_no_probability(self) -> Decimal:
        return (
            Decimal("1") - self.btts_yes_probability
        ).quantize(Decimal("0.0001"))

    @property
    def predicted_outcome(self) -> str:
        outcomes = {
            "home_win": self.home_win_probability,
            "draw": self.draw_probability,
            "away_win": self.away_win_probability,
        }

        return max(
            outcomes,
            key=outcomes.get,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "expected_goals": self.expected_goals.as_dict(),
            "outcome_probabilities": {
                "home_win": float(self.home_win_probability),
                "draw": float(self.draw_probability),
                "away_win": float(self.away_win_probability),
            },
            "goals_probabilities": {
                "btts_yes": float(self.btts_yes_probability),
                "btts_no": float(self.btts_no_probability),
                "over_2_5": float(self.over_2_5_probability),
                "under_2_5": float(self.under_2_5_probability),
            },
            "predicted_outcome": self.predicted_outcome,
            "most_likely_scores": [
                score.as_dict()
                for score in self.most_likely_scores
            ],
            "model_version": self.model_version,
        }
