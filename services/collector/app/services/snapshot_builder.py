from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.team_intelligence import (
    StandingContext,
    TeamRatings,
    TeamStatistics,
)
from app.domain.team_snapshot import TeamSnapshot


class SnapshotBuilder:
    """
    Build a deterministic team-intelligence snapshot.

    This class does not read from or write to PostgreSQL. It combines the
    calculated statistics, ratings and optional standing context into one
    TeamSnapshot object that can later be saved by a repository.
    """

    DEFAULT_CALCULATION_VERSION = "v1"

    @classmethod
    def build(
        cls,
        *,
        team_id: UUID,
        competition_id: UUID,
        season_id: UUID,
        statistics: TeamStatistics,
        ratings: TeamRatings,
        standing: StandingContext | None = None,
        snapshot_at: datetime | None = None,
        data_cutoff_at: datetime | None = None,
        calculation_version: str = DEFAULT_CALCULATION_VERSION,
        metadata: dict[str, Any] | None = None,
    ) -> TeamSnapshot:
        cls._validate_identifiers(
            team_id=team_id,
            competition_id=competition_id,
            season_id=season_id,
            statistics=statistics,
        )

        if statistics.window_size <= 0:
            raise ValueError("statistics.window_size must be greater than zero.")

        if statistics.matches_played < 0:
            raise ValueError("statistics.matches_played cannot be negative.")

        snapshot_at = snapshot_at or datetime.now(timezone.utc)
        data_cutoff_at = data_cutoff_at or snapshot_at

        cls._validate_datetime(
            snapshot_at,
            field_name="snapshot_at",
        )
        cls._validate_datetime(
            data_cutoff_at,
            field_name="data_cutoff_at",
        )

        calculation_version = calculation_version.strip()

        if not calculation_version:
            raise ValueError("calculation_version cannot be empty.")

        days_since_last_match = cls._calculate_days_since_last_match(
            last_match_at=statistics.last_match_at,
            reference_at=data_cutoff_at,
        )

        data_completeness = cls._calculate_data_completeness(
            matches_played=statistics.matches_played,
            window_size=statistics.window_size,
        )

        snapshot_metadata = cls._build_metadata(
            statistics=statistics,
            supplied_metadata=metadata,
        )

        snapshot = TeamSnapshot(
            team_id=team_id,
            competition_id=competition_id,
            season_id=season_id,
            snapshot_at=snapshot_at,
            data_cutoff_at=data_cutoff_at,
            window_size=statistics.window_size,

            matches_played=statistics.matches_played,
            wins=statistics.wins,
            draws=statistics.draws,
            losses=statistics.losses,

            points=statistics.points,
            points_per_game=statistics.points_per_game,

            goals_for=statistics.goals_for,
            goals_against=statistics.goals_against,
            goal_difference=statistics.goal_difference,

            goals_for_per_game=statistics.goals_for_per_game,
            goals_against_per_game=statistics.goals_against_per_game,

            clean_sheets=statistics.clean_sheets,
            failed_to_score=statistics.failed_to_score,
            btts_count=statistics.btts_count,
            over_2_5_count=statistics.over_2_5_count,

            btts_rate=statistics.btts_rate,
            over_2_5_rate=statistics.over_2_5_rate,
            clean_sheet_rate=statistics.clean_sheet_rate,
            failed_to_score_rate=statistics.failed_to_score_rate,

            home_matches=statistics.home.matches,
            home_wins=statistics.home.wins,
            home_draws=statistics.home.draws,
            home_losses=statistics.home.losses,
            home_points=statistics.home.points,

            home_points_per_game=statistics.home.points_per_game,
            home_goals_for_per_game=statistics.home.goals_for_per_game,
            home_goals_against_per_game=(
                statistics.home.goals_against_per_game
            ),

            away_matches=statistics.away.matches,
            away_wins=statistics.away.wins,
            away_draws=statistics.away.draws,
            away_losses=statistics.away.losses,
            away_points=statistics.away.points,

            away_points_per_game=statistics.away.points_per_game,
            away_goals_for_per_game=statistics.away.goals_for_per_game,
            away_goals_against_per_game=(
                statistics.away.goals_against_per_game
            ),

            current_position=(
                standing.position
                if standing is not None
                else None
            ),
            current_league_points=(
                standing.points
                if standing is not None
                else None
            ),

            days_since_last_match=days_since_last_match,

            attack_rating=ratings.attack_rating,
            defence_rating=ratings.defence_rating,
            home_rating=ratings.home_rating,
            away_rating=ratings.away_rating,
            form_rating=ratings.form_rating,
            overall_rating=ratings.overall_rating,
            elo_rating=ratings.elo_rating,

            form_sequence=statistics.form_sequence,

            data_completeness=data_completeness,
            calculation_version=calculation_version,
            metadata=snapshot_metadata,
        )

        snapshot_hash = cls._generate_snapshot_hash(snapshot)

        return replace(
            snapshot,
            snapshot_hash=snapshot_hash,
        )

    @staticmethod
    def _validate_identifiers(
        *,
        team_id: UUID,
        competition_id: UUID,
        season_id: UUID,
        statistics: TeamStatistics,
    ) -> None:
        if statistics.team_id != team_id:
            raise ValueError(
                "statistics.team_id does not match the supplied team_id."
            )

        if not isinstance(team_id, UUID):
            raise TypeError("team_id must be a UUID.")

        if not isinstance(competition_id, UUID):
            raise TypeError("competition_id must be a UUID.")

        if not isinstance(season_id, UUID):
            raise TypeError("season_id must be a UUID.")

    @staticmethod
    def _validate_datetime(
        value: datetime,
        *,
        field_name: str,
    ) -> None:
        if value.tzinfo is None:
            raise ValueError(
                f"{field_name} must be timezone-aware."
            )

    @staticmethod
    def _calculate_days_since_last_match(
        *,
        last_match_at: datetime | None,
        reference_at: datetime,
    ) -> Decimal | None:
        if last_match_at is None:
            return None

        if last_match_at.tzinfo is None:
            raise ValueError(
                "statistics.last_match_at must be timezone-aware."
            )

        elapsed_seconds = (
            reference_at - last_match_at
        ).total_seconds()

        if elapsed_seconds < 0:
            elapsed_seconds = 0

        days = Decimal(str(elapsed_seconds)) / Decimal("86400")

        return days.quantize(Decimal("0.01"))

    @staticmethod
    def _calculate_data_completeness(
        *,
        matches_played: int,
        window_size: int,
    ) -> Decimal:
        if window_size <= 0:
            return Decimal("0.0000")

        completeness = (
            Decimal(matches_played) / Decimal(window_size)
        )

        completeness = min(
            Decimal("1.0000"),
            max(Decimal("0.0000"), completeness),
        )

        return completeness.quantize(Decimal("0.0001"))

    @staticmethod
    def _build_metadata(
        *,
        statistics: TeamStatistics,
        supplied_metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = dict(supplied_metadata or {})

        result["fixture_ids"] = [
            str(fixture_id)
            for fixture_id in statistics.fixture_ids
        ]

        if statistics.last_match_at is not None:
            result["last_match_at"] = (
                statistics.last_match_at.isoformat()
            )

        return result

    @classmethod
    def _generate_snapshot_hash(
        cls,
        snapshot: TeamSnapshot,
    ) -> str:
        """
        Generate a content hash without snapshot_at, created_at or id.

        Identical calculated data produces the same hash even when the
        builder runs at a different time.
        """

        hash_payload = {
            "team_id": snapshot.team_id,
            "competition_id": snapshot.competition_id,
            "season_id": snapshot.season_id,
            
            "window_size": snapshot.window_size,

            "matches_played": snapshot.matches_played,
            "wins": snapshot.wins,
            "draws": snapshot.draws,
            "losses": snapshot.losses,
            "points": snapshot.points,
            "points_per_game": snapshot.points_per_game,

            "goals_for": snapshot.goals_for,
            "goals_against": snapshot.goals_against,
            "goal_difference": snapshot.goal_difference,
            "goals_for_per_game": snapshot.goals_for_per_game,
            "goals_against_per_game": (
                snapshot.goals_against_per_game
            ),

            "clean_sheets": snapshot.clean_sheets,
            "failed_to_score": snapshot.failed_to_score,
            "btts_count": snapshot.btts_count,
            "over_2_5_count": snapshot.over_2_5_count,

            "btts_rate": snapshot.btts_rate,
            "over_2_5_rate": snapshot.over_2_5_rate,
            "clean_sheet_rate": snapshot.clean_sheet_rate,
            "failed_to_score_rate": (
                snapshot.failed_to_score_rate
            ),

            "home_matches": snapshot.home_matches,
            "home_wins": snapshot.home_wins,
            "home_draws": snapshot.home_draws,
            "home_losses": snapshot.home_losses,
            "home_points": snapshot.home_points,
            "home_points_per_game": (
                snapshot.home_points_per_game
            ),
            "home_goals_for_per_game": (
                snapshot.home_goals_for_per_game
            ),
            "home_goals_against_per_game": (
                snapshot.home_goals_against_per_game
            ),

            "away_matches": snapshot.away_matches,
            "away_wins": snapshot.away_wins,
            "away_draws": snapshot.away_draws,
            "away_losses": snapshot.away_losses,
            "away_points": snapshot.away_points,
            "away_points_per_game": (
                snapshot.away_points_per_game
            ),
            "away_goals_for_per_game": (
                snapshot.away_goals_for_per_game
            ),
            "away_goals_against_per_game": (
                snapshot.away_goals_against_per_game
            ),

            "current_position": snapshot.current_position,
            "current_league_points": (
                snapshot.current_league_points
            ),
            "days_since_last_match": (
                snapshot.days_since_last_match
            ),

            "attack_rating": snapshot.attack_rating,
            "defence_rating": snapshot.defence_rating,
            "home_rating": snapshot.home_rating,
            "away_rating": snapshot.away_rating,
            "form_rating": snapshot.form_rating,
            "overall_rating": snapshot.overall_rating,
            "elo_rating": snapshot.elo_rating,

            "form_sequence": snapshot.form_sequence,
            "data_completeness": snapshot.data_completeness,
            "calculation_version": (
                snapshot.calculation_version
            ),
            "metadata": snapshot.metadata,
        }

        serialized = json.dumps(
            hash_payload,
            sort_keys=True,
            separators=(",", ":"),
            default=cls._serialize_hash_value,
        )

        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _serialize_hash_value(value: Any) -> str:
        if isinstance(value, Decimal):
            return format(value, "f")

        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, datetime):
            return value.isoformat()

        raise TypeError(
            f"Unsupported snapshot hash value: {type(value)!r}"
        )