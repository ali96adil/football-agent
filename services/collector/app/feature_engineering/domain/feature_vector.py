from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.feature_engineering.domain.feature import Feature


@dataclass(slots=True)
class FeatureVector:
    """
    Prediction-ready collection of engineered match features.

    One vector represents one comparison between a home team and an away team.
    """

    home_team_id: UUID
    away_team_id: UUID

    competition_id: UUID
    season_id: UUID

    home_snapshot_id: UUID | None = None
    away_snapshot_id: UUID | None = None

    generated_at: datetime | None = None

    features: list[Feature] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.home_team_id == self.away_team_id:
            raise ValueError(
                "home_team_id and away_team_id cannot be identical."
            )

    def add(self, feature: Feature) -> None:
        if self.get(feature.name) is not None:
            raise ValueError(
                f"Feature '{feature.name}' already exists in this vector."
            )

        self.features.append(feature)

    def extend(self, features: list[Feature]) -> None:
        for feature in features:
            self.add(feature)

    def get(self, name: str) -> Feature | None:
        return next(
            (
                feature
                for feature in self.features
                if feature.name == name
            ),
            None,
        )

    def get_value(
        self,
        name: str,
        default: Any = None,
    ) -> Any:
        feature = self.get(name)

        if feature is None:
            return default

        return feature.value
    def has(self, name: str) -> bool:
        return self.get(name) is not None    

    def values_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}

        for feature in self.features:
            value: Any = feature.value

            if isinstance(value, Decimal):
                value = float(value)

            result[feature.name] = value

        return result

    def as_dict(self) -> dict[str, Any]:
        return {
            "home_team_id": str(self.home_team_id),
            "away_team_id": str(self.away_team_id),
            "competition_id": str(self.competition_id),
            "season_id": str(self.season_id),
            "home_snapshot_id": (
                str(self.home_snapshot_id)
                if self.home_snapshot_id is not None
                else None
            ),
            "away_snapshot_id": (
                str(self.away_snapshot_id)
                if self.away_snapshot_id is not None
                else None
            ),
            "generated_at": (
                self.generated_at.isoformat()
                if self.generated_at is not None
                else None
            ),
            "feature_count": len(self.features),
            "features": [
                feature.as_dict()
                for feature in self.features
            ],
            "values": self.values_dict(),
            "metadata": self.metadata,
        }
