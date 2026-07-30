from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class ScoreProbability:
    home_goals: int
    away_goals: int
    probability: Decimal

    def __post_init__(self) -> None:
        if self.home_goals < 0:
            raise ValueError("home_goals cannot be negative.")

        if self.away_goals < 0:
            raise ValueError("away_goals cannot be negative.")

        if not Decimal("0") <= self.probability <= Decimal("1"):
            raise ValueError(
                "probability must be between 0 and 1."
            )

    @property
    def scoreline(self) -> str:
        return f"{self.home_goals}-{self.away_goals}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "scoreline": self.scoreline,
            "probability": float(self.probability),
        }
