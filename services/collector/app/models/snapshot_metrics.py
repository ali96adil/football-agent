from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class SnapshotMetrics:

    matches_played: int

    wins: int
    draws: int
    losses: int

    points: int

    goals_for: int
    goals_against: int
    goal_difference: int

    clean_sheets: int
    failed_to_score: int
    btts_count: int
    over_2_5_count: int

    home_matches: int
    home_wins: int
    home_draws: int
    home_losses: int
    home_points: int

    away_matches: int
    away_wins: int
    away_draws: int
    away_losses: int
    away_points: int

    form_sequence: str

    points_per_game: Decimal
    goals_for_per_game: Decimal
    goals_against_per_game: Decimal

    clean_sheet_rate: Decimal
    failed_to_score_rate: Decimal
    btts_rate: Decimal
    over_2_5_rate: Decimal

    data_completeness: Decimal