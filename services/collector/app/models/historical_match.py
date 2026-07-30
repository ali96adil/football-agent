from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class HistoricalMatch:
    fixture_id: UUID

    kickoff_at: datetime

    home_team_id: UUID
    away_team_id: UUID

    home_score: int
    away_score: int

    is_home: bool

    goals_for: int
    goals_against: int

    won: bool
    drawn: bool
    lost: bool

    clean_sheet: bool
    failed_to_score: bool

    both_teams_scored: bool
    over_2_5: bool