import json
from datetime import datetime, timezone
from typing import Any

from app.repositories.entities import (
    upsert_competition,
    upsert_season,
    upsert_team,
)


def map_fixture_status(source_status: str | None) -> str:
    status_mapping = {
        "SCHEDULED": "scheduled",
        "TIMED": "scheduled",
        "IN_PLAY": "live",
        "PAUSED": "live",
        "EXTRA_TIME": "live",
        "PENALTY_SHOOTOUT": "live",
        "FINISHED": "finished",
        "POSTPONED": "postponed",
        "SUSPENDED": "suspended",
        "CANCELLED": "cancelled",
        "AWARDED": "finished",
    }

    return status_mapping.get(
        (source_status or "").upper(),
        "unknown",
    )


async def normalize_fixture(
    connection: Any,
    source_id: int,
    raw_payload_id: int,
    match: dict[str, Any],
) -> str:
    external_fixture_id = match.get("id")

    if external_fixture_id is None:
        raise ValueError("External fixture ID is missing")

    competition_data = match.get("competition") or {}
    area_data = match.get("area") or {}
    season_data = match.get("season") or {}
    home_team_data = match.get("homeTeam") or {}
    away_team_data = match.get("awayTeam") or {}
    score_data = match.get("score") or {}
    full_time_score = score_data.get("fullTime") or {}

    competition_id = await upsert_competition(
        connection,
        competition_data,
        area_data,
    )

    season_id = await upsert_season(
        connection,
        competition_id,
        season_data,
    )

    home_team_id = await upsert_team(
        connection,
        source_id,
        home_team_data,
        area_data.get("code"),
    )

    away_team_id = await upsert_team(
        connection,
        source_id,
        away_team_data,
        area_data.get("code"),
    )

    existing_fixture_result = await connection.execute(
        """
        SELECT fixture_id
        FROM core.fixture_source_ids
        WHERE source_id = %s
          AND external_fixture_id = %s
        LIMIT 1
        """,
        (
            source_id,
            str(external_fixture_id),
        ),
    )

    existing_fixture = await existing_fixture_result.fetchone()

    source_status = match.get("status")
    fixture_status = map_fixture_status(source_status)
    kickoff_at = match.get("utcDate")

    winner_code = score_data.get("winner")
    winner_team_id = None

    if winner_code == "HOME_TEAM":
        winner_team_id = home_team_id
    elif winner_code == "AWAY_TEAM":
        winner_team_id = away_team_id

    result_confirmed = fixture_status == "finished"

    fixture_metadata = json.dumps(
        {
            "football_data_match_id": external_fixture_id,
            "stage": match.get("stage"),
            "group": match.get("group"),
            "matchday": match.get("matchday"),
            "last_updated": match.get("lastUpdated"),
            "duration": score_data.get("duration"),
            "half_time_score": score_data.get("halfTime"),
            "referees": match.get("referees", []),
            "raw_payload_id": raw_payload_id,
        },
        ensure_ascii=False,
    )

    if existing_fixture:
        fixture_id = existing_fixture["fixture_id"]

        await connection.execute(
            """
            UPDATE core.fixtures
            SET
                competition_id = %s,
                season_id = %s,
                home_team_id = %s,
                away_team_id = %s,
                kickoff_at = %s,
                fixture_status = %s,
                home_score = %s,
                away_score = %s,
                winner_team_id = %s,
                result_confirmed = %s,
                metadata = metadata || %s::jsonb,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                competition_id,
                season_id,
                home_team_id,
                away_team_id,
                kickoff_at,
                fixture_status,
                full_time_score.get("home"),
                full_time_score.get("away"),
                winner_team_id,
                result_confirmed,
                fixture_metadata,
                fixture_id,
            ),
        )

        await connection.execute(
            """
            UPDATE core.fixture_source_ids
            SET
                source_status = %s,
                source_kickoff_at = %s,
                last_synced_at = NOW()
            WHERE source_id = %s
              AND external_fixture_id = %s
            """,
            (
                source_status,
                kickoff_at,
                source_id,
                str(external_fixture_id),
            ),
        )

    else:
        fixture_result = await connection.execute(
            """
            INSERT INTO core.fixtures (
                competition_id,
                season_id,
                home_team_id,
                away_team_id,
                kickoff_at,
                fixture_status,
                home_score,
                away_score,
                winner_team_id,
                result_confirmed,
                metadata
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s::jsonb
            )
            RETURNING id
            """,
            (
                competition_id,
                season_id,
                home_team_id,
                away_team_id,
                kickoff_at,
                fixture_status,
                full_time_score.get("home"),
                full_time_score.get("away"),
                winner_team_id,
                result_confirmed,
                fixture_metadata,
            ),
        )

        created_fixture = await fixture_result.fetchone()
        fixture_id = created_fixture["id"]

        await connection.execute(
            """
            INSERT INTO core.fixture_source_ids (
                fixture_id,
                source_id,
                external_fixture_id,
                source_status,
                source_kickoff_at,
                last_synced_at
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                NOW()
            )
            """,
            (
                fixture_id,
                source_id,
                str(external_fixture_id),
                source_status,
                kickoff_at,
            ),
        )

    await connection.execute(
        """
        UPDATE raw.api_payloads
        SET fixture_id = %s
        WHERE id = %s
          AND fixture_id IS NULL
        """,
        (
            fixture_id,
            raw_payload_id,
        ),
    )

    return str(fixture_id)
