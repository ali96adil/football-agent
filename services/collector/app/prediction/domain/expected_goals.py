from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class ExpectedGoals:
    """
    Expected-goals output used as input for a probability model.

    The values represent the expected number of goals for the home
    and away teams.
    """

    home: Decimal
    away: Decimal

    model_version: str = "expected-goals-v1"
    confidence: Decimal = Decimal("1.0000")

    def __post_init__(self) -> None:
        if self.home < Decimal("0"):
            raise ValueError(
                "home expected goals cannot be negative."
            )

        if self.away < Decimal("0"):
            raise ValueError(
                "away expected goals cannot be negative."
            )

        if not (
            Decimal("0")
            <= self.confidence
            <= Decimal("1")
        ):
            raise ValueError(
                "confidence must be between 0 and 1."
            )

    @property
    def total(self) -> Decimal:
        return (
            self.home + self.away
        ).quantize(Decimal("0.0001"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "home_expected_goals": float(self.home),
            "away_expected_goals": float(self.away),
            "total_expected_goals": float(self.total),
            "model_version": self.model_version,
            "confidence": float(self.confidence),
        }
