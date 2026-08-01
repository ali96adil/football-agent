from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.team_intelligence import CompletedFixture


async def get_completed_fixtures_for_team(
    connection: Any,
    *,
    team_id: UUID,
    competition_id: UUID | None = None,
    season_id: UUID | None = None,
    window_size: int = 10,
    cutoff_at: datetime | None = None,
    analysis_only: bool = False,
) -> list[CompletedFixture]:
    """
    Return the newest confirmed fixtures for one team.

    Results are returned newest first. The statistics engine may reorder
    them internally when generating the form sequence.
    """

    if window_size <= 0:
        raise ValueError("window_size must be greater than zero.")

    conditions = [
        "(home_team_id = %s OR away_team_id = %s)",
        "result_confirmed = TRUE",
        "home_score IS NOT NULL",
        "away_score IS NOT NULL",
    ]

    parameters: list[Any] = [
        team_id,
        team_id,
    ]

    if competition_id is not None:
        conditions.append("competition_id = %s")
        parameters.append(competition_id)

    if season_id is not None:
        conditions.append("season_id = %s")
        parameters.append(season_id)

    if cutoff_at is not None:
        if cutoff_at.tzinfo is None:
            raise ValueError("cutoff_at must be timezone-aware.")

        conditions.append("kickoff_at <= %s")
        parameters.append(cutoff_at)

    if analysis_only:
        conditions.append("selected_for_analysis = TRUE")

    parameters.append(window_size)

    query = f"""
        SELECT
            id,
            competition_id,
            season_id,
            kickoff_at,
            home_team_id,
            away_team_id,
            home_score,
            away_score
        FROM core.fixtures
        WHERE {" AND ".join(conditions)}
        ORDER BY kickoff_at DESC NULLS LAST, id DESC
        LIMIT %s
    """

    result = await connection.execute(
        query,
        tuple(parameters),
    )

    rows = await result.fetchall()

    return [
        _row_to_completed_fixture(row)
        for row in rows
    ]


async def get_last_completed_fixture_for_team(
    connection: Any,
    *,
    team_id: UUID,
    competition_id: UUID | None = None,
    season_id: UUID | None = None,
    cutoff_at: datetime | None = None,
) -> CompletedFixture | None:
    fixtures = await get_completed_fixtures_for_team(
        connection,
        team_id=team_id,
        competition_id=competition_id,
        season_id=season_id,
        window_size=1,
        cutoff_at=cutoff_at,
    )

    return fixtures[0] if fixtures else None


async def get_completed_fixture_count_for_team(
    connection: Any,
    *,
    team_id: UUID,
    competition_id: UUID | None = None,
    season_id: UUID | None = None,
    cutoff_at: datetime | None = None,
) -> int:
    conditions = [
        "(home_team_id = %s OR away_team_id = %s)",
        "result_confirmed = TRUE",
        "home_score IS NOT NULL",
        "away_score IS NOT NULL",
    ]

    parameters: list[Any] = [
        team_id,
        team_id,
    ]

    if competition_id is not None:
        conditions.append("competition_id = %s")
        parameters.append(competition_id)

    if season_id is not None:
        conditions.append("season_id = %s")
        parameters.append(season_id)

    if cutoff_at is not None:
        if cutoff_at.tzinfo is None:
            raise ValueError("cutoff_at must be timezone-aware.")

        conditions.append("kickoff_at <= %s")
        parameters.append(cutoff_at)

    query = f"""
        SELECT COUNT(*) AS fixture_count
        FROM core.fixtures
        WHERE {" AND ".join(conditions)}
    """

    result = await connection.execute(
        query,
        tuple(parameters),
    )

    row = await result.fetchone()

    return int(row["fixture_count"])


def _row_to_completed_fixture(
    row: dict[str, Any],
) -> CompletedFixture:
    return CompletedFixture(
        fixture_id=UUID(str(row["id"])),
        competition_id=(
            UUID(str(row["competition_id"]))
            if row["competition_id"] is not None
            else None
        ),
        season_id=(
            UUID(str(row["season_id"]))
            if row["season_id"] is not None
            else None
        ),
        kickoff_at=row["kickoff_at"],
        home_team_id=UUID(str(row["home_team_id"])),
        away_team_id=UUID(str(row["away_team_id"])),
        home_score=int(row["home_score"]),
        away_score=int(row["away_score"]),
    )

async def get_scheduled_fixtures(
    connection: Any,
    *,
    kickoff_from: datetime | None = None,
    kickoff_to: datetime | None = None,
    competition_id: UUID | None = None,
    season_id: UUID | None = None,
    limit: int = 100,
) -> list["PredictionFixture"]:
    """
    Return scheduled fixtures ordered by kickoff time.

    Postponed and finished fixtures are intentionally excluded.
    """

    from app.prediction.domain.prediction_fixture import (
        PredictionFixture,
    )

    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    conditions = [
        "fixture_status = 'scheduled'",
        "result_confirmed = FALSE",
        "home_team_id IS NOT NULL",
        "away_team_id IS NOT NULL",
        "competition_id IS NOT NULL",
        "season_id IS NOT NULL",
        "kickoff_at IS NOT NULL",
    ]

    parameters: list[Any] = []

    if kickoff_from is not None:
        if kickoff_from.tzinfo is None:
            raise ValueError(
                "kickoff_from must be timezone-aware."
            )

        conditions.append("kickoff_at >= %s")
        parameters.append(kickoff_from)

    if kickoff_to is not None:
        if kickoff_to.tzinfo is None:
            raise ValueError(
                "kickoff_to must be timezone-aware."
            )

        conditions.append("kickoff_at <= %s")
        parameters.append(kickoff_to)

    if (
        kickoff_from is not None
        and kickoff_to is not None
        and kickoff_to < kickoff_from
    ):
        raise ValueError(
            "kickoff_to cannot be earlier than kickoff_from."
        )

    if competition_id is not None:
        conditions.append("competition_id = %s")
        parameters.append(competition_id)

    if season_id is not None:
        conditions.append("season_id = %s")
        parameters.append(season_id)

    parameters.append(limit)

    query = f"""
        SELECT
            id,
            competition_id,
            season_id,
            home_team_id,
            away_team_id,
            kickoff_at,
            fixture_status
        FROM core.fixtures
        WHERE {" AND ".join(conditions)}
        ORDER BY kickoff_at ASC NULLS LAST, id ASC
        LIMIT %s
    """

    result = await connection.execute(
        query,
        tuple(parameters),
    )

    rows = await result.fetchall()

    return [
        PredictionFixture(
            fixture_id=UUID(str(row["id"])),
            competition_id=UUID(
                str(row["competition_id"])
            ),
            season_id=UUID(str(row["season_id"])),
            home_team_id=UUID(
                str(row["home_team_id"])
            ),
            away_team_id=UUID(
                str(row["away_team_id"])
            ),
            kickoff_at=row["kickoff_at"],
            fixture_status=row["fixture_status"],
        )
        for row in rows
    ]
