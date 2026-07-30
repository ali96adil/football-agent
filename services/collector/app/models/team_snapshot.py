from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(slots=True)
class TeamSnapshot:
    team_id: UUID
    competition_id: UUID
    season_id: UUID

    snapshot_at: datetime
    data_cutoff_at: datetime

    window_size: int

    matches_played: int
    wins: int
    draws: int
    losses: int
    points: int

    goals_for: int
    goals_against: int
    goal_difference: int

    points_per_game: Decimal | None = None
    goals_for_per_game: Decimal | None = None
    goals_against_per_game: Decimal | None = None

    clean_sheets: int = 0
    failed_to_score: int = 0
    btts_count: int = 0
    over_2_5_count: int = 0

    btts_rate: Decimal | None = None
    over_2_5_rate: Decimal | None = None
    clean_sheet_rate: Decimal | None = None
    failed_to_score_rate: Decimal | None = None

    home_matches: int = 0
    home_wins: int = 0
    home_draws: int = 0
    home_losses: int = 0
    home_points: int = 0

    away_matches: int = 0
    away_wins: int = 0
    away_draws: int = 0
    away_losses: int = 0
    away_points: int = 0

    form_sequence: str = ""

    data_completeness: Decimal = Decimal("1.0")

    calculation_version: str = "v1"

    snapshot_hash: str | None = None

    metadata: dict = field(default_factory=dict)