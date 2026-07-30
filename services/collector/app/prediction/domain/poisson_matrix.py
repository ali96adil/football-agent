from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class PoissonMatrix:
    """
    Joint score probability matrix produced by the Poisson model.

    matrix[home_goals][away_goals] = probability
    """

    matrix: tuple[tuple[Decimal, ...], ...]

    max_goals: int

    model_version: str = "poisson-v1"

    def __post_init__(self) -> None:
        if self.max_goals < 1:
            raise ValueError("max_goals must be greater than zero.")

        expected_size = self.max_goals + 1

        if len(self.matrix) != expected_size:
            raise ValueError(
                "Matrix height does not match max_goals."
            )

        for row in self.matrix:
            if len(row) != expected_size:
                raise ValueError(
                    "Matrix width does not match max_goals."
                )

        total = self.total_probability

        if total <= Decimal("0"):
            raise ValueError(
                "Total probability must be greater than zero."
            )

    @property
    def total_probability(self) -> Decimal:
        return sum(
            (
                sum(row, Decimal("0"))
                for row in self.matrix
            ),
            Decimal("0"),
        )

    def probability(
        self,
        home_goals: int,
        away_goals: int,
    ) -> Decimal:
        return self.matrix[home_goals][away_goals]

    def as_dict(self) -> dict[str, Any]:
        return {
            "max_goals": self.max_goals,
            "model_version": self.model_version,
            "total_probability": float(
                self.total_probability
            ),
            "matrix": [
                [
                    float(value)
                    for value in row
                ]
                for row in self.matrix
            ],
        }