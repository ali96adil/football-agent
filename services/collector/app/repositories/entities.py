import json
from datetime import date
from typing import Any


async def upsert_competition(
    connection: Any,
    competition_data: dict[str, Any],
    area_data: dict[str, Any],
) -> str:
    canonical_name = competition_data.get("name")

    if not canonical_name:
        raise ValueError("Competition name is missing")

    country_code = area_data.get("code")

    result = await connection.execute(
        """
        INSERT INTO core.competitions (
            canonical_name,
            country_code,
            competition_type,
            metadata,
            updated_at
        )
        VALUES (
            %s,
            %s,
            %s,
            %s::jsonb,
            NOW()
        )
        ON CONFLICT (
            canonical_name,
            country_code
        )
        DO UPDATE SET
            competition_type = EXCLUDED.competition_type,
            metadata = core.competitions.metadata || EXCLUDED.metadata,
            updated_at = NOW()
        RETURNING id
        """,
        (
            canonical_name,
            country_code,
            competition_data.get("type"),
            json.dumps(
                {
                    "football_data_id": competition_data.get("id"),
                    "football_data_code": competition_data.get("code"),
                    "emblem": competition_data.get("emblem"),
                    "area": area_data,
                },
                ensure_ascii=False,
            ),
        ),
    )

    row = await result.fetchone()
    return str(row["id"])


async def upsert_season(
    connection: Any,
    competition_id: str,
    season_data: dict[str, Any],
) -> str | None:
    start_date = season_data.get("startDate")
    end_date = season_data.get("endDate")

    if not start_date and not end_date:
        return None

    if start_date and end_date:
        label = f"{start_date[:4]}/{end_date[:4]}"
    elif start_date:
        label = start_date[:4]
    else:
        label = end_date[:4]

    today = date.today()

    is_current = False

    if start_date and end_date:
        try:
            is_current = (
                date.fromisoformat(start_date)
                <= today
                <= date.fromisoformat(end_date)
            )
        except ValueError:
            is_current = False

    result = await connection.execute(
        """
        INSERT INTO core.seasons (
            competition_id,
            label,
            starts_on,
            ends_on,
            is_current,
            metadata
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s::jsonb
        )
        ON CONFLICT (
            competition_id,
            label
        )
        DO UPDATE SET
            starts_on = EXCLUDED.starts_on,
            ends_on = EXCLUDED.ends_on,
            is_current = EXCLUDED.is_current,
            metadata = core.seasons.metadata || EXCLUDED.metadata
        RETURNING id
        """,
        (
            competition_id,
            label,
            start_date,
            end_date,
            is_current,
            json.dumps(
                {
                    "football_data_season_id": season_data.get("id"),
                    "current_matchday": season_data.get(
                        "currentMatchday"
                    ),
                    "winner": season_data.get("winner"),
                },
                ensure_ascii=False,
            ),
        ),
    )

    row = await result.fetchone()
    return str(row["id"])


async def upsert_team(
    connection: Any,
    source_id: int,
    team_data: dict[str, Any],
    country_code: str | None,
) -> str:
    external_team_id = team_data.get("id")
    canonical_name = team_data.get("name")

    if external_team_id is None:
        raise ValueError("External team ID is missing")

    if not canonical_name:
        raise ValueError(
            f"Team name is missing for ID {external_team_id}"
        )

    existing_result = await connection.execute(
        """
        SELECT team_id
        FROM core.team_source_ids
        WHERE source_id = %s
          AND external_team_id = %s
        LIMIT 1
        """,
        (
            source_id,
            str(external_team_id),
        ),
    )

    existing = await existing_result.fetchone()

    if existing:
        team_id = existing["team_id"]

        await connection.execute(
            """
            UPDATE core.teams
            SET
                canonical_name = %s,
                short_name = %s,
                country_code = COALESCE(%s, country_code),
                logo_url = %s,
                metadata = metadata || %s::jsonb,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                canonical_name,
                team_data.get("shortName"),
                country_code,
                team_data.get("crest"),
                json.dumps(
                    {
                        "tla": team_data.get("tla"),
                    },
                    ensure_ascii=False,
                ),
                team_id,
            ),
        )

        return str(team_id)

    team_result = await connection.execute(
        """
        INSERT INTO core.teams (
            canonical_name,
            short_name,
            country_code,
            logo_url,
            metadata
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s::jsonb
        )
        RETURNING id
        """,
        (
            canonical_name,
            team_data.get("shortName"),
            country_code,
            team_data.get("crest"),
            json.dumps(
                {
                    "tla": team_data.get("tla"),
                },
                ensure_ascii=False,
            ),
        ),
    )

    created_team = await team_result.fetchone()
    team_id = created_team["id"]

    await connection.execute(
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
        """,
        (
            team_id,
            source_id,
            str(external_team_id),
            canonical_name,
        ),
    )

    return str(team_id)
