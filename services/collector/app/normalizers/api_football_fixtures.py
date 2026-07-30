import json
from typing import Any


STATUS_MAPPING = {
    "TBD": "scheduled",
    "NS": "scheduled",
    "1H": "live",
    "HT": "live",
    "2H": "live",
    "ET": "live",
    "BT": "live",
    "P": "live",
    "SUSP": "suspended",
    "INT": "suspended",
    "PST": "postponed",
    "CANC": "cancelled",
    "ABD": "cancelled",
    "AWD": "finished",
    "WO": "finished",
    "FT": "finished",
    "AET": "finished",
    "PEN": "finished",
}


COUNTRY_CODE_MAPPING = {
    "England": "ENG",
    "Germany": "DEU",
    "France": "FRA",
    "Italy": "ITA",
    "Spain": "ESP",
    "Portugal": "POR",
    "Netherlands": "NLD",
    "Brazil": "BRA",
    "World": "INT",
}


def map_api_football_status(status_short: str | None) -> str:
    return STATUS_MAPPING.get(
        (status_short or "").upper(),
        "unknown",
    )


async def upsert_api_football_competition(
    connection: Any,
    league: dict[str, Any],
) -> str:
    league_id = league.get("id")
    name = league.get("name")
    country = league.get("country")

    if league_id is None:
        raise ValueError("API-Football league ID is missing")

    if not name:
        raise ValueError("API-Football league name is missing")

    country_code = COUNTRY_CODE_MAPPING.get(country)

    metadata = json.dumps(
        {
            "api_football_id": league_id,
            "api_football_logo": league.get("logo"),
            "api_football_flag": league.get("flag"),
            "api_football_country": country,
            "standings_supported": league.get("standings"),
        },
        ensure_ascii=False,
    )

    result = await connection.execute(
        """
        INSERT INTO core.competitions (
            canonical_name,
            country_code,
            competition_type,
            gender,
            metadata,
            created_at,
            updated_at
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s::jsonb,
            NOW(),
            NOW()
        )
        ON CONFLICT (
            canonical_name,
            country_code
        )
        DO UPDATE SET
            metadata = core.competitions.metadata
                || EXCLUDED.metadata,
            updated_at = NOW()
        RETURNING id
        """,
        (
            name,
            country_code,
            "LEAGUE",
            "MALE",
            metadata,
        ),
    )

    row = await result.fetchone()
    return str(row["id"])


async def upsert_api_football_season(
    connection: Any,
    competition_id: str,
    league: dict[str, Any],
) -> str:
    season_year = league.get("season")

    if season_year is None:
        raise ValueError("API-Football season is missing")

    label = str(season_year)

    metadata = json.dumps(
        {
            "api_football_season": season_year,
        },
        ensure_ascii=False,
    )

    result = await connection.execute(
        """
        INSERT INTO core.seasons (
            competition_id,
            label,
            is_current,
            metadata
        )
        VALUES (
            %s,
            %s,
            FALSE,
            %s::jsonb
        )
        ON CONFLICT (
            competition_id,
            label
        )
        DO UPDATE SET
            metadata = core.seasons.metadata
                || EXCLUDED.metadata
        RETURNING id
        """,
        (
            competition_id,
            label,
            metadata,
        ),
    )

    row = await result.fetchone()
    return str(row["id"])


async def upsert_api_football_team(
    connection: Any,
    source_id: int,
    team: dict[str, Any],
    country_code: str | None,
) -> str:
    external_team_id = team.get("id")
    name = team.get("name")

    if external_team_id is None:
        raise ValueError("API-Football team ID is missing")

    if not name:
        raise ValueError("API-Football team name is missing")

    metadata = json.dumps(
        {
            "api_football_id": external_team_id,
        },
        ensure_ascii=False,
    )

    team_result = await connection.execute(
        """
        INSERT INTO core.teams (
            canonical_name,
            short_name,
            country_code,
            logo_url,
            metadata,
            created_at,
            updated_at
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s::jsonb,
            NOW(),
            NOW()
        )
        RETURNING id
        """,
        (
            name,
            name,
            country_code,
            team.get("logo"),
            metadata,
        ),
    )

    created_team = await team_result.fetchone()
    created_team_id = created_team["id"]

    mapping_result = await connection.execute(
        """
        INSERT INTO core.team_source_ids (
            team_id,
            source_id,
            external_team_id,
            source_name,
            confidence,
            verified
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            1,
            TRUE
        )
        ON CONFLICT (
            source_id,
            external_team_id
        )
        DO UPDATE SET
            source_name = EXCLUDED.source_name,
            confidence = EXCLUDED.confidence,
            verified = EXCLUDED.verified
        RETURNING team_id
        """,
        (
            created_team_id,
            source_id,
            str(external_team_id),
            name,
        ),
    )

    mapping = await mapping_result.fetchone()

    if mapping["team_id"] != created_team_id:
        await connection.execute(
            """
            DELETE FROM core.teams
            WHERE id = %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM core.team_source_ids
                  WHERE team_id = %s
              )
            """,
            (
                created_team_id,
                created_team_id,
            ),
        )

    return str(mapping["team_id"])


async def normalize_api_football_fixture(
    connection: Any,
    source_id: int,
    raw_payload_id: int,
    item: dict[str, Any],
) -> str:
    fixture = item.get("fixture") or {}
    league = item.get("league") or {}
    teams = item.get("teams") or {}
    score = item.get("score") or {}
    goals = item.get("goals") or {}

    home_team = teams.get("home") or {}
    away_team = teams.get("away") or {}
    venue = fixture.get("venue") or {}
    status = fixture.get("status") or {}

    external_fixture_id = fixture.get("id")

    if external_fixture_id is None:
        raise ValueError("API-Football fixture ID is missing")

    country_code = COUNTRY_CODE_MAPPING.get(
        league.get("country")
    )

    competition_id = await upsert_api_football_competition(
        connection,
        league,
    )

    season_id = await upsert_api_football_season(
        connection,
        competition_id,
        league,
    )

    home_team_id = await upsert_api_football_team(
        connection,
        source_id,
        home_team,
        country_code,
    )

    away_team_id = await upsert_api_football_team(
        connection,
        source_id,
        away_team,
        country_code,
    )

    status_short = status.get("short")
    fixture_status = map_api_football_status(status_short)

    winner_team_id = None

    if home_team.get("winner") is True:
        winner_team_id = home_team_id
    elif away_team.get("winner") is True:
        winner_team_id = away_team_id

    fulltime = score.get("fulltime") or {}
    extratime = score.get("extratime") or {}
    penalty = score.get("penalty") or {}

    home_score = fulltime.get("home")

    if home_score is None:
        home_score = goals.get("home")

    away_score = fulltime.get("away")

    if away_score is None:
        away_score = goals.get("away")

    result_confirmed = fixture_status == "finished"

    metadata = json.dumps(
        {
            "api_football_fixture_id": external_fixture_id,
            "league_id": league.get("id"),
            "round": league.get("round"),
            "referee": fixture.get("referee"),
            "timezone": fixture.get("timezone"),
            "timestamp": fixture.get("timestamp"),
            "elapsed": status.get("elapsed"),
            "status_long": status.get("long"),
            "periods": fixture.get("periods"),
            "half_time_score": score.get("halftime"),
            "raw_payload_id": raw_payload_id,
        },
        ensure_ascii=False,
    )

    fixture_result = await connection.execute(
        """
        INSERT INTO core.fixtures (
            competition_id,
            season_id,
            home_team_id,
            away_team_id,
            kickoff_at,
            venue_name,
            venue_city,
            fixture_status,
            home_score,
            away_score,
            extra_time_home,
            extra_time_away,
            penalties_home,
            penalties_away,
            winner_team_id,
            result_confirmed,
            metadata,
            created_at,
            updated_at
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
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s::jsonb,
            NOW(),
            NOW()
        )
        RETURNING id
        """,
        (
            competition_id,
            season_id,
            home_team_id,
            away_team_id,
            fixture.get("date"),
            venue.get("name"),
            venue.get("city"),
            fixture_status,
            home_score,
            away_score,
            extratime.get("home"),
            extratime.get("away"),
            penalty.get("home"),
            penalty.get("away"),
            winner_team_id,
            result_confirmed,
            metadata,
        ),
    )

    created_fixture = await fixture_result.fetchone()
    created_fixture_id = created_fixture["id"]

    source_mapping_result = await connection.execute(
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
        ON CONFLICT (
            source_id,
            external_fixture_id
        )
        DO UPDATE SET
            source_status = EXCLUDED.source_status,
            source_kickoff_at = EXCLUDED.source_kickoff_at,
            last_synced_at = NOW()
        RETURNING fixture_id
        """,
        (
            created_fixture_id,
            source_id,
            str(external_fixture_id),
            status_short,
            fixture.get("date"),
        ),
    )

    source_mapping = await source_mapping_result.fetchone()
    fixture_id = source_mapping["fixture_id"]

    if fixture_id != created_fixture_id:
        await connection.execute(
            """
            UPDATE core.fixtures
            SET
                competition_id = %s,
                season_id = %s,
                home_team_id = %s,
                away_team_id = %s,
                kickoff_at = %s,
                venue_name = %s,
                venue_city = %s,
                fixture_status = %s,
                home_score = %s,
                away_score = %s,
                extra_time_home = %s,
                extra_time_away = %s,
                penalties_home = %s,
                penalties_away = %s,
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
                fixture.get("date"),
                venue.get("name"),
                venue.get("city"),
                fixture_status,
                home_score,
                away_score,
                extratime.get("home"),
                extratime.get("away"),
                penalty.get("home"),
                penalty.get("away"),
                winner_team_id,
                result_confirmed,
                metadata,
                fixture_id,
            ),
        )

        await connection.execute(
            """
            DELETE FROM core.fixtures
            WHERE id = %s
            """,
            (created_fixture_id,),
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
