from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class SnapshotFullResponse(BaseModel):
    id: UUID

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
    points_per_game: Decimal | None

    goals_for: int
    goals_against: int
    goal_difference: int

    goals_for_per_game: Decimal | None
    goals_against_per_game: Decimal | None

    clean_sheets: int
    failed_to_score: int
    btts_count: int
    over_2_5_count: int

    btts_rate: Decimal | None
    over_2_5_rate: Decimal | None
    clean_sheet_rate: Decimal | None
    failed_to_score_rate: Decimal | None

    home_matches: int
    home_wins: int
    home_draws: int
    home_losses: int
    home_points: int

    home_points_per_game: Decimal | None
    home_goals_for_per_game: Decimal | None
    home_goals_against_per_game: Decimal | None

    away_matches: int
    away_wins: int
    away_draws: int
    away_losses: int
    away_points: int

    away_points_per_game: Decimal | None
    away_goals_for_per_game: Decimal | None
    away_goals_against_per_game: Decimal | None

    current_position: int | None
    current_league_points: int | None
    days_since_last_match: Decimal | None

    attack_rating: Decimal | None
    defence_rating: Decimal | None
    home_rating: Decimal | None
    away_rating: Decimal | None
    form_rating: Decimal | None
    overall_rating: Decimal | None
    elo_rating: Decimal | None

    form_sequence: str

    data_completeness: Decimal
    calculation_version: str
    snapshot_hash: str | None

    metadata: dict[str, Any]
    created_at: datetime | None

    model_config = {
        "from_attributes": True,
    }
    