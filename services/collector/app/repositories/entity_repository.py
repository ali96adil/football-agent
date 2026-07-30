import json
from typing import Any
from uuid import UUID

from app.normalizers.canonical_fixture import (
    CanonicalCompetition,
    CanonicalSeason,
    CanonicalTeam,
)


def _json(value: dict[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _row_value(
    row: Any,
    key: str,
    position: int = 0,
) -> Any:
    if row is None:
        return None

    if isinstance(row, dict):
        return row.get(key)

    try:
        return row[key]
    except (TypeError, KeyError):
        return row[position]


class EntityRepository:
    """
    Persists canonical competitions, seasons, teams and their
    provider-specific identifiers.

    The caller is responsible for opening the database transaction.
    """

    async def upsert_competition(
        self,
        connection: Any,
        competition: CanonicalCompetition,
    ) -> UUID:
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
                competition_type = COALESCE(
                    EXCLUDED.competition_type,
                    core.competitions.competition_type
                ),
                gender = COALESCE(
                    EXCLUDED.gender,
                    core.competitions.gender
                ),
                metadata = core.competitions.metadata
                    || EXCLUDED.metadata,
                updated_at = NOW()
            RETURNING id
            """,
            (
                competition.name,
                competition.country_code,
                competition.competition_type,
                competition.gender,
                _json(competition.metadata),
            ),
        )

        row = await result.fetchone()

        if row is None:
            raise RuntimeError(
                "Competition UPSERT did not return an ID"
            )

        return UUID(str(_row_value(row, "id")))

    async def upsert_season(
        self,
        connection: Any,
        competition_id: UUID,
        season: CanonicalSeason,
    ) -> UUID:
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
                starts_on = COALESCE(
                    EXCLUDED.starts_on,
                    core.seasons.starts_on
                ),
                ends_on = COALESCE(
                    EXCLUDED.ends_on,
                    core.seasons.ends_on
                ),
                is_current = (
                    core.seasons.is_current
                    OR EXCLUDED.is_current
                ),
                metadata = core.seasons.metadata
                    || EXCLUDED.metadata
            RETURNING id
            """,
            (
                competition_id,
                season.label,
                season.starts_on,
                season.ends_on,
                season.is_current,
                _json(season.metadata),
            ),
        )

        row = await result.fetchone()

        if row is None:
            raise RuntimeError(
                "Season UPSERT did not return an ID"
            )

        return UUID(str(_row_value(row, "id")))

    async def upsert_team(
        self,
        connection: Any,
        *,
        source_id: int,
        team: CanonicalTeam,
    ) -> UUID:
        """
        Resolve a team in this order:

        1. Existing mapping for provider + external team ID.
        2. Existing canonical team with normalized name/country.
        3. Create a new canonical team.

        Finally, attach or update core.team_source_ids.
        """

        mapped_result = await connection.execute(
            """
            SELECT
                tsi.team_id
            FROM core.team_source_ids AS tsi
            WHERE tsi.source_id = %s
              AND tsi.external_team_id = %s
            LIMIT 1
            """,
            (
                source_id,
                team.external_id,
            ),
        )

        mapped_row = await mapped_result.fetchone()
        team_id = _row_value(mapped_row, "team_id")

        if team_id is not None:
            resolved_team_id = UUID(str(team_id))

            await self._update_team(
                connection,
                team_id=resolved_team_id,
                team=team,
            )

            await self._upsert_team_source_mapping(
                connection,
                team_id=resolved_team_id,
                source_id=source_id,
                team=team,
            )

            return resolved_team_id

        canonical_result = await connection.execute(
            """
            SELECT
                t.id
            FROM core.teams AS t
            WHERE LOWER(TRIM(t.canonical_name))
                  = LOWER(TRIM(%s))
              AND t.country_code IS NOT DISTINCT FROM %s
            ORDER BY t.created_at ASC
            LIMIT 1
            """,
            (
                team.name,
                team.country_code,
            ),
        )

        canonical_row = await canonical_result.fetchone()
        canonical_team_id = _row_value(
            canonical_row,
            "id",
        )

        if canonical_team_id is None:
            insert_result = await connection.execute(
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
                    team.name,
                    team.short_name,
                    team.country_code,
                    team.logo_url,
                    _json(team.metadata),
                ),
            )

            inserted_row = await insert_result.fetchone()

            if inserted_row is None:
                raise RuntimeError(
                    "Team INSERT did not return an ID"
                )

            resolved_team_id = UUID(
                str(_row_value(inserted_row, "id"))
            )
        else:
            resolved_team_id = UUID(
                str(canonical_team_id)
            )

            await self._update_team(
                connection,
                team_id=resolved_team_id,
                team=team,
            )

        await self._upsert_team_source_mapping(
            connection,
            team_id=resolved_team_id,
            source_id=source_id,
            team=team,
        )

        return resolved_team_id

    async def _update_team(
        self,
        connection: Any,
        *,
        team_id: UUID,
        team: CanonicalTeam,
    ) -> None:
        await connection.execute(
            """
            UPDATE core.teams
            SET
                short_name = COALESCE(
                    %s,
                    short_name
                ),
                country_code = COALESCE(
                    country_code,
                    %s
                ),
                logo_url = COALESCE(
                    %s,
                    logo_url
                ),
                metadata = metadata || %s::jsonb,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                team.short_name,
                team.country_code,
                team.logo_url,
                _json(team.metadata),
                team_id,
            ),
        )

    async def _upsert_team_source_mapping(
        self,
        connection: Any,
        *,
        team_id: UUID,
        source_id: int,
        team: CanonicalTeam,
    ) -> UUID:
        result = await connection.execute(
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
                1.0000,
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
                team_id,
                source_id,
                team.external_id,
                team.name,
            ),
        )

        row = await result.fetchone()

        if row is None:
            raise RuntimeError(
                "Team source mapping UPSERT did not return a team ID"
            )

        mapped_team_id = UUID(
            str(_row_value(row, "team_id"))
        )

        if mapped_team_id != team_id:
            raise RuntimeError(
                "Provider team mapping points to a different "
                f"canonical team: expected={team_id}, "
                f"actual={mapped_team_id}"
            )

        return mapped_team_id
