from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PredictionFixture:
    fixture_id: UUID
    competition_id: UUID
    season_id: UUID
    home_team_id: UUID
    away_team_id: UUID
    kickoff_at: datetime
    fixture_status: str

    def __post_init__(self) -> None:
        if self.kickoff_at.tzinfo is None:
            raise ValueError(
                "kickoff_at must be timezone-aware."
            )

        if not self.fixture_status.strip():
            raise ValueError(
                "fixture_status must not be empty."
            )
