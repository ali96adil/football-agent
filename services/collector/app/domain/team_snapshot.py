from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TeamSnapshot:
    id: UUID | None = None

    team_id: UUID | None = None
    competition_id: UUID | None = None
    season_id: UUID | None = None

    snapshot_at: datetime | None = None
    data_cutoff_at: datetime | None = None

    window_size: int = 0

    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0

    points: int = 0
    points_per_game: Decimal | None = None

    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0

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

    home_points_per_game: Decimal | None = None
    home_goals_for_per_game: Decimal | None = None
    home_goals_against_per_game: Decimal | None = None

    away_matches: int = 0
    away_wins: int = 0
    away_draws: int = 0
    away_losses: int = 0
    away_points: int = 0

    away_points_per_game: Decimal | None = None
    away_goals_for_per_game: Decimal | None = None
    away_goals_against_per_game: Decimal | None = None

    current_position: int | None = None
    current_league_points: int | None = None

    days_since_last_match: Decimal | None = None

    attack_rating: Decimal | None = None
    defence_rating: Decimal | None = None
    home_rating: Decimal | None = None
    away_rating: Decimal | None = None
    form_rating: Decimal | None = None
    overall_rating: Decimal | None = None
    elo_rating: Decimal | None = None

    form_sequence: str = ""

    data_completeness: Decimal = Decimal("1.0000")
    calculation_version: str = "v1"
    snapshot_hash: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        from dataclasses import asdict

        return asdict(self)