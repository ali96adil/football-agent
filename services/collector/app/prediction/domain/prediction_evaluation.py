from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


VALID_OUTCOMES = {
    "home_win",
    "draw",
    "away_win",
}


@dataclass(frozen=True, slots=True)
class PredictionEvaluation:
    actual_home_goals: int
    actual_away_goals: int
    actual_outcome: str

    outcome_correct: bool
    exact_score_correct: bool

    brier_score: Decimal
    log_loss: Decimal

    home_probability_error: Decimal
    draw_probability_error: Decimal
    away_probability_error: Decimal

    actual_outcome_probability: Decimal

    def __post_init__(self) -> None:
        if self.actual_home_goals < 0:
            raise ValueError(
                "actual_home_goals cannot be negative."
            )

        if self.actual_away_goals < 0:
            raise ValueError(
                "actual_away_goals cannot be negative."
            )

        if self.actual_outcome not in VALID_OUTCOMES:
            raise ValueError(
                "actual_outcome must be home_win, "
                "draw or away_win."
            )

        if self.brier_score < Decimal("0"):
            raise ValueError(
                "brier_score cannot be negative."
            )

        if self.log_loss < Decimal("0"):
            raise ValueError(
                "log_loss cannot be negative."
            )

        if not (
            Decimal("0")
            <= self.actual_outcome_probability
            <= Decimal("1")
        ):
            raise ValueError(
                "actual_outcome_probability must be "
                "between 0 and 1."
            )

    @property
    def actual_scoreline(self) -> str:
        return (
            f"{self.actual_home_goals}-"
            f"{self.actual_away_goals}"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "actual_result": {
                "home_goals": self.actual_home_goals,
                "away_goals": self.actual_away_goals,
                "scoreline": self.actual_scoreline,
                "outcome": self.actual_outcome,
            },
            "accuracy": {
                "outcome_correct": self.outcome_correct,
                "exact_score_correct": (
                    self.exact_score_correct
                ),
            },
            "scores": {
                "brier_score": float(self.brier_score),
                "log_loss": float(self.log_loss),
            },
            "probability_errors": {
                "home_win": float(
                    self.home_probability_error
                ),
                "draw": float(
                    self.draw_probability_error
                ),
                "away_win": float(
                    self.away_probability_error
                ),
            },
            "actual_outcome_probability": float(
                self.actual_outcome_probability
            ),
        }
