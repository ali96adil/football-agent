from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


FeatureValue = Decimal | float | int | bool | str | None


@dataclass(frozen=True, slots=True)
class Feature:
    """
    Represents one engineered feature.

    A feature contains both its numeric/value representation and metadata
    describing where it came from and how it should be interpreted.
    """

    name: str
    value: FeatureValue

    category: str
    source: str

    importance: str = "normal"
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Feature name cannot be empty.")

        if not self.category or not self.category.strip():
            raise ValueError("Feature category cannot be empty.")

        if not self.source or not self.source.strip():
            raise ValueError("Feature source cannot be empty.")

        allowed_importance = {
            "low",
            "normal",
            "high",
            "critical",
        }

        if self.importance not in allowed_importance:
            raise ValueError(
                "Feature importance must be one of: "
                "low, normal, high, critical."
            )

    def as_dict(self) -> dict[str, Any]:
        value: Any = self.value

        if isinstance(value, Decimal):
            value = float(value)

        return {
            "name": self.name,
            "value": value,
            "category": self.category,
            "source": self.source,
            "importance": self.importance,
            "description": self.description,
        }
