from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CompletedFixture:
    """
    Normalized completed fixture used by the statistics engine.

    Scores must represent the final score used for team-form calculations.
    """

    fixture_id: UUID
    kickoff_at: datetime

    home_team_id: UUID
    away_team_id: UUID

    home_score: int
    away_score: int

    competition_id: UUID | None = None
    season_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.home_team_id == self.away_team_id:
            raise ValueError("Home and away teams cannot be identical.")

        if self.home_score < 0 or self.away_score < 0:
            raise ValueError("Fixture scores cannot be negative.")

        if self.kickoff_at.tzinfo is None:
            raise ValueError("kickoff_at must be timezone-aware.")


@dataclass(frozen=True, slots=True)
class VenueStatistics:
    matches: int = 0

    wins: int = 0
    draws: int = 0
    losses: int = 0

    points: int = 0

    goals_for: int = 0
    goals_against: int = 0

    @property
    def points_per_game(self) -> Decimal | None:
        return _safe_average(self.points, self.matches)

    @property
    def goals_for_per_game(self) -> Decimal | None:
        return _safe_average(self.goals_for, self.matches)

    @property
    def goals_against_per_game(self) -> Decimal | None:
        return _safe_average(self.goals_against, self.matches)


@dataclass(frozen=True, slots=True)
class TeamStatistics:
    team_id: UUID
    window_size: int

    matches_played: int

    wins: int
    draws: int
    losses: int
    points: int

    goals_for: int
    goals_against: int

    clean_sheets: int
    failed_to_score: int
    btts_count: int
    over_2_5_count: int

    home: VenueStatistics
    away: VenueStatistics

    form_sequence: str

    fixture_ids: tuple[UUID, ...] = field(default_factory=tuple)
    last_match_at: datetime | None = None

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def points_per_game(self) -> Decimal | None:
        return _safe_average(self.points, self.matches_played)

    @property
    def goals_for_per_game(self) -> Decimal | None:
        return _safe_average(self.goals_for, self.matches_played)

    @property
    def goals_against_per_game(self) -> Decimal | None:
        return _safe_average(self.goals_against, self.matches_played)

    @property
    def win_rate(self) -> Decimal | None:
        return _safe_rate(self.wins, self.matches_played)

    @property
    def draw_rate(self) -> Decimal | None:
        return _safe_rate(self.draws, self.matches_played)

    @property
    def loss_rate(self) -> Decimal | None:
        return _safe_rate(self.losses, self.matches_played)

    @property
    def clean_sheet_rate(self) -> Decimal | None:
        return _safe_rate(self.clean_sheets, self.matches_played)

    @property
    def failed_to_score_rate(self) -> Decimal | None:
        return _safe_rate(self.failed_to_score, self.matches_played)

    @property
    def btts_rate(self) -> Decimal | None:
        return _safe_rate(self.btts_count, self.matches_played)

    @property
    def over_2_5_rate(self) -> Decimal | None:
        return _safe_rate(self.over_2_5_count, self.matches_played)

    def as_dict(self) -> dict[str, Any]:
        return {
            "team_id": str(self.team_id),
            "window_size": self.window_size,
            "matches_played": self.matches_played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "points": self.points,
            "points_per_game": self.points_per_game,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "goals_for_per_game": self.goals_for_per_game,
            "goals_against_per_game": self.goals_against_per_game,
            "clean_sheets": self.clean_sheets,
            "failed_to_score": self.failed_to_score,
            "btts_count": self.btts_count,
            "over_2_5_count": self.over_2_5_count,
            "clean_sheet_rate": self.clean_sheet_rate,
            "failed_to_score_rate": self.failed_to_score_rate,
            "btts_rate": self.btts_rate,
            "over_2_5_rate": self.over_2_5_rate,
            "home_matches": self.home.matches,
            "home_wins": self.home.wins,
            "home_draws": self.home.draws,
            "home_losses": self.home.losses,
            "home_points": self.home.points,
            "home_points_per_game": self.home.points_per_game,
            "home_goals_for_per_game": self.home.goals_for_per_game,
            "home_goals_against_per_game": (
                self.home.goals_against_per_game
            ),
            "away_matches": self.away.matches,
            "away_wins": self.away.wins,
            "away_draws": self.away.draws,
            "away_losses": self.away.losses,
            "away_points": self.away.points,
            "away_points_per_game": self.away.points_per_game,
            "away_goals_for_per_game": self.away.goals_for_per_game,
            "away_goals_against_per_game": (
                self.away.goals_against_per_game
            ),
            "form_sequence": self.form_sequence,
            "fixture_ids": [str(value) for value in self.fixture_ids],
            "last_match_at": self.last_match_at,
        }


@dataclass(frozen=True, slots=True)
class StandingContext:
    position: int | None = None
    points: int | None = None
    played_games: int | None = None
    goal_difference: int | None = None

    snapshot_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class TeamRatings:
    attack_rating: Decimal | None = None
    defence_rating: Decimal | None = None

    form_rating: Decimal | None = None
    home_rating: Decimal | None = None
    away_rating: Decimal | None = None
    overall_rating: Decimal | None = None

    elo_rating: Decimal | None = None
    def as_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


def _safe_average(value: int, total: int) -> Decimal | None:
    if total <= 0:
        return None

    return (Decimal(value) / Decimal(total)).quantize(
        Decimal("0.0001")
    )


def _safe_rate(value: int, total: int) -> Decimal | None:
    return _safe_average(value, total)