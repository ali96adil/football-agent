from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

from app.domain.team_snapshot import TeamSnapshot


async def save_snapshot(
    connection: Any,
    *,
    snapshot: TeamSnapshot,
) -> TeamSnapshot:
    """
    Persist a team-intelligence snapshot and return the stored row.

    When another snapshot with the same deterministic snapshot_hash already
    exists, the existing database row is returned instead of creating a
    duplicate.
    """

    _validate_snapshot(snapshot)

    query = """
        INSERT INTO core.team_snapshots (
            team_id,
            competition_id,
            season_id,
            snapshot_at,
            data_cutoff_at,
            window_size,

            matches_played,
            wins,
            draws,
            losses,
            points,
            points_per_game,

            goals_for,
            goals_against,
            goal_difference,
            goals_for_per_game,
            goals_against_per_game,

            clean_sheets,
            failed_to_score,
            btts_count,
            over_2_5_count,

            btts_rate,
            over_2_5_rate,
            clean_sheet_rate,
            failed_to_score_rate,

            home_matches,
            home_wins,
            home_draws,
            home_losses,
            home_points,
            home_points_per_game,
            home_goals_for_per_game,
            home_goals_against_per_game,

            away_matches,
            away_wins,
            away_draws,
            away_losses,
            away_points,
            away_points_per_game,
            away_goals_for_per_game,
            away_goals_against_per_game,

            current_position,
            current_league_points,
            days_since_last_match,

            attack_rating,
            defence_rating,
            home_rating,
            away_rating,
            form_rating,
            overall_rating,
            elo_rating,

            form_sequence,

            data_completeness,
            calculation_version,
            snapshot_hash,
            metadata
        )
        VALUES (
            %s, %s, %s, %s, %s, %s,

            %s, %s, %s, %s, %s, %s,

            %s, %s, %s, %s, %s,

            %s, %s, %s, %s,

            %s, %s, %s, %s,

            %s, %s, %s, %s, %s, %s, %s, %s,

            %s, %s, %s, %s, %s, %s, %s, %s,

            %s, %s, %s,

            %s, %s, %s, %s, %s, %s, %s,

            %s,

            %s, %s, %s, %s
        )
        ON CONFLICT (snapshot_hash)
        WHERE snapshot_hash IS NOT NULL
        DO UPDATE SET
            snapshot_hash = EXCLUDED.snapshot_hash
        RETURNING *
    """

    parameters = (
        snapshot.team_id,
        snapshot.competition_id,
        snapshot.season_id,
        snapshot.snapshot_at,
        snapshot.data_cutoff_at,
        snapshot.window_size,

        snapshot.matches_played,
        snapshot.wins,
        snapshot.draws,
        snapshot.losses,
        snapshot.points,
        snapshot.points_per_game,

        snapshot.goals_for,
        snapshot.goals_against,
        snapshot.goal_difference,
        snapshot.goals_for_per_game,
        snapshot.goals_against_per_game,

        snapshot.clean_sheets,
        snapshot.failed_to_score,
        snapshot.btts_count,
        snapshot.over_2_5_count,

        snapshot.btts_rate,
        snapshot.over_2_5_rate,
        snapshot.clean_sheet_rate,
        snapshot.failed_to_score_rate,

        snapshot.home_matches,
        snapshot.home_wins,
        snapshot.home_draws,
        snapshot.home_losses,
        snapshot.home_points,
        snapshot.home_points_per_game,
        snapshot.home_goals_for_per_game,
        snapshot.home_goals_against_per_game,

        snapshot.away_matches,
        snapshot.away_wins,
        snapshot.away_draws,
        snapshot.away_losses,
        snapshot.away_points,
        snapshot.away_points_per_game,
        snapshot.away_goals_for_per_game,
        snapshot.away_goals_against_per_game,

        snapshot.current_position,
        snapshot.current_league_points,
        snapshot.days_since_last_match,

        snapshot.attack_rating,
        snapshot.defence_rating,
        snapshot.home_rating,
        snapshot.away_rating,
        snapshot.form_rating,
        snapshot.overall_rating,
        snapshot.elo_rating,

        snapshot.form_sequence,

        snapshot.data_completeness,
        snapshot.calculation_version,
        snapshot.snapshot_hash,
        Jsonb(snapshot.metadata),
    )

    result = await connection.execute(
        query,
        parameters,
    )

    row = await result.fetchone()

    if row is None:
        raise RuntimeError("Snapshot insert did not return a database row.")

    return _row_to_team_snapshot(row)


async def get_snapshot_by_id(
    connection: Any,
    *,
    snapshot_id: UUID,
) -> TeamSnapshot | None:
    query = """
        SELECT *
        FROM core.team_snapshots
        WHERE id = %s
        LIMIT 1
    """

    result = await connection.execute(
        query,
        (snapshot_id,),
    )

    row = await result.fetchone()

    if row is None:
        return None

    return _row_to_team_snapshot(row)


async def get_snapshot_by_hash(
    connection: Any,
    *,
    snapshot_hash: str,
) -> TeamSnapshot | None:
    if not snapshot_hash.strip():
        raise ValueError("snapshot_hash must not be empty.")

    query = """
        SELECT *
        FROM core.team_snapshots
        WHERE snapshot_hash = %s
        LIMIT 1
    """

    result = await connection.execute(
        query,
        (snapshot_hash,),
    )

    row = await result.fetchone()

    if row is None:
        return None

    return _row_to_team_snapshot(row)


async def get_latest_snapshot(
    connection: Any,
    *,
    team_id: UUID,
    competition_id: UUID,
    season_id: UUID,
    window_size: int,
    calculation_version: str | None = None,
) -> TeamSnapshot | None:
    if window_size <= 0:
        raise ValueError("window_size must be greater than zero.")

    conditions = [
        "team_id = %s",
        "competition_id = %s",
        "season_id = %s",
        "window_size = %s",
    ]

    parameters: list[Any] = [
        team_id,
        competition_id,
        season_id,
        window_size,
    ]

    if calculation_version is not None:
        if not calculation_version.strip():
            raise ValueError("calculation_version must not be empty.")

        conditions.append("calculation_version = %s")
        parameters.append(calculation_version)

    query = f"""
        SELECT *
        FROM core.team_snapshots
        WHERE {" AND ".join(conditions)}
        ORDER BY
            snapshot_at DESC,
            created_at DESC,
            id DESC
        LIMIT 1
    """

    result = await connection.execute(
        query,
        tuple(parameters),
    )

    row = await result.fetchone()

    if row is None:
        return None

    return _row_to_team_snapshot(row)


async def get_latest_snapshots_for_competition(
    connection: Any,
    *,
    competition_id: UUID,
    season_id: UUID,
    window_size: int,
    calculation_version: str | None = None,
) -> list[TeamSnapshot]:
    """
    Return the latest snapshot for every team in one competition and season.
    """

    if window_size <= 0:
        raise ValueError("window_size must be greater than zero.")

    conditions = [
        "competition_id = %s",
        "season_id = %s",
        "window_size = %s",
    ]

    parameters: list[Any] = [
        competition_id,
        season_id,
        window_size,
    ]

    if calculation_version is not None:
        if not calculation_version.strip():
            raise ValueError("calculation_version must not be empty.")

        conditions.append("calculation_version = %s")
        parameters.append(calculation_version)

    query = f"""
        SELECT DISTINCT ON (team_id)
            *
        FROM core.team_snapshots
        WHERE {" AND ".join(conditions)}
        ORDER BY
            team_id,
            snapshot_at DESC,
            created_at DESC,
            id DESC
    """

    result = await connection.execute(
        query,
        tuple(parameters),
    )

    rows = await result.fetchall()

    return [
        _row_to_team_snapshot(row)
        for row in rows
    ]


def _validate_snapshot(snapshot: TeamSnapshot) -> None:
    if snapshot.team_id is None:
        raise ValueError("snapshot.team_id is required.")

    if snapshot.competition_id is None:
        raise ValueError("snapshot.competition_id is required.")

    if snapshot.season_id is None:
        raise ValueError("snapshot.season_id is required.")

    if snapshot.snapshot_at is None:
        raise ValueError("snapshot.snapshot_at is required.")

    if snapshot.snapshot_at.tzinfo is None:
        raise ValueError("snapshot.snapshot_at must be timezone-aware.")

    if snapshot.data_cutoff_at is None:
        raise ValueError("snapshot.data_cutoff_at is required.")

    if snapshot.data_cutoff_at.tzinfo is None:
        raise ValueError("snapshot.data_cutoff_at must be timezone-aware.")

    if snapshot.window_size <= 0:
        raise ValueError("snapshot.window_size must be greater than zero.")

    if snapshot.matches_played < 0:
        raise ValueError("snapshot.matches_played cannot be negative.")

    if snapshot.wins < 0 or snapshot.draws < 0 or snapshot.losses < 0:
        raise ValueError("Snapshot result counts cannot be negative.")

    if (
        snapshot.wins
        + snapshot.draws
        + snapshot.losses
        > snapshot.matches_played
    ):
        raise ValueError(
            "wins + draws + losses cannot exceed matches_played."
        )

    if snapshot.data_completeness < 0 or snapshot.data_completeness > 1:
        raise ValueError(
            "snapshot.data_completeness must be between zero and one."
        )

    if not snapshot.calculation_version.strip():
        raise ValueError("snapshot.calculation_version must not be empty.")


def _row_to_team_snapshot(
    row: dict[str, Any],
) -> TeamSnapshot:
    metadata = row.get("metadata")

    if not isinstance(metadata, dict):
        metadata = {}

    return TeamSnapshot(
        id=_to_uuid(row.get("id")),
        team_id=_to_uuid(row.get("team_id")),
        competition_id=_to_uuid(row.get("competition_id")),
        season_id=_to_uuid(row.get("season_id")),

        snapshot_at=row.get("snapshot_at"),
        data_cutoff_at=row.get("data_cutoff_at"),

        window_size=int(row.get("window_size") or 0),

        matches_played=int(row.get("matches_played") or 0),
        wins=int(row.get("wins") or 0),
        draws=int(row.get("draws") or 0),
        losses=int(row.get("losses") or 0),

        points=int(row.get("points") or 0),
        points_per_game=row.get("points_per_game"),

        goals_for=int(row.get("goals_for") or 0),
        goals_against=int(row.get("goals_against") or 0),
        goal_difference=int(row.get("goal_difference") or 0),

        goals_for_per_game=row.get("goals_for_per_game"),
        goals_against_per_game=row.get("goals_against_per_game"),

        clean_sheets=int(row.get("clean_sheets") or 0),
        failed_to_score=int(row.get("failed_to_score") or 0),
        btts_count=int(row.get("btts_count") or 0),
        over_2_5_count=int(row.get("over_2_5_count") or 0),

        btts_rate=row.get("btts_rate"),
        over_2_5_rate=row.get("over_2_5_rate"),
        clean_sheet_rate=row.get("clean_sheet_rate"),
        failed_to_score_rate=row.get("failed_to_score_rate"),

        home_matches=int(row.get("home_matches") or 0),
        home_wins=int(row.get("home_wins") or 0),
        home_draws=int(row.get("home_draws") or 0),
        home_losses=int(row.get("home_losses") or 0),
        home_points=int(row.get("home_points") or 0),

        home_points_per_game=row.get("home_points_per_game"),
        home_goals_for_per_game=row.get(
            "home_goals_for_per_game"
        ),
        home_goals_against_per_game=row.get(
            "home_goals_against_per_game"
        ),

        away_matches=int(row.get("away_matches") or 0),
        away_wins=int(row.get("away_wins") or 0),
        away_draws=int(row.get("away_draws") or 0),
        away_losses=int(row.get("away_losses") or 0),
        away_points=int(row.get("away_points") or 0),

        away_points_per_game=row.get("away_points_per_game"),
        away_goals_for_per_game=row.get(
            "away_goals_for_per_game"
        ),
        away_goals_against_per_game=row.get(
            "away_goals_against_per_game"
        ),

        current_position=_to_optional_int(
            row.get("current_position")
        ),
        current_league_points=_to_optional_int(
            row.get("current_league_points")
        ),

        days_since_last_match=row.get("days_since_last_match"),

        attack_rating=row.get("attack_rating"),
        defence_rating=row.get("defence_rating"),
        home_rating=row.get("home_rating"),
        away_rating=row.get("away_rating"),
        form_rating=row.get("form_rating"),
        overall_rating=row.get("overall_rating"),
        elo_rating=row.get("elo_rating"),

        form_sequence=str(row.get("form_sequence") or ""),

        data_completeness=row["data_completeness"],
        calculation_version=str(
            row.get("calculation_version") or "v1"
        ),
        snapshot_hash=row.get("snapshot_hash"),

        metadata=metadata,

        created_at=row.get("created_at"),
    )


def _to_uuid(value: Any) -> UUID | None:
    if value is None:
        return None

    if isinstance(value, UUID):
        return value

    return UUID(str(value))


def _to_optional_int(value: Any) -> int | None:
    if value is None:
        return None

    return int(value)