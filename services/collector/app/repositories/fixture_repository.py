from typing import Any
from uuid import UUID
from psycopg.types.json import Jsonb
from app.normalizers.canonical_fixture import CanonicalFixture


def _row_value(row: Any, key: str, position: int = 0):
    if row is None:
        return None

    if isinstance(row, dict):
        return row.get(key)

    try:
        return row[key]
    except Exception:
        return row[position]


class FixtureRepository:
    """
    Repository responsible for:

    - core.fixtures
    - core.fixture_source_ids
    - linking raw.api_payloads -> fixture_id
    """

    async def upsert_fixture(
        self,
        connection: Any,
        *,
        fixture: CanonicalFixture,
        competition_id: UUID,
        season_id: UUID,
        home_team_id: UUID,
        away_team_id: UUID,
        winner_team_id: UUID | None,
    ) -> UUID:

        result = await connection.execute(
            """
            INSERT INTO core.fixtures (
                competition_id,
                season_id,
                home_team_id,
                away_team_id,
                kickoff_at,
                venue_name,
                venue_city,
                neutral_venue,
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
                %s,
                %s::jsonb,
                NOW()
            )
            ON CONFLICT (
                competition_id,
                kickoff_at,
                home_team_id,
                away_team_id
            )
            DO UPDATE SET

                season_id = EXCLUDED.season_id,

                venue_name = EXCLUDED.venue_name,
                venue_city = EXCLUDED.venue_city,

                neutral_venue = EXCLUDED.neutral_venue,

                fixture_status = EXCLUDED.fixture_status,

                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score,

                extra_time_home = EXCLUDED.extra_time_home,
                extra_time_away = EXCLUDED.extra_time_away,

                penalties_home = EXCLUDED.penalties_home,
                penalties_away = EXCLUDED.penalties_away,

                winner_team_id = EXCLUDED.winner_team_id,

                result_confirmed = EXCLUDED.result_confirmed,

                metadata =
                    core.fixtures.metadata
                    || EXCLUDED.metadata,

                updated_at = NOW()

            RETURNING id
            """,
            (
                competition_id,
                season_id,
                home_team_id,
                away_team_id,
                fixture.kickoff_at,
                fixture.venue_name,
                fixture.venue_city,
                fixture.neutral_venue,
                fixture.status,
                fixture.home_score,
                fixture.away_score,
                fixture.extra_time_home,
                fixture.extra_time_away,
                fixture.penalties_home,
                fixture.penalties_away,
                winner_team_id,
                fixture.result_confirmed,
                Jsonb(fixture.metadata or {}),
            ),
        )

        row = await result.fetchone()

        if row is None:
            raise RuntimeError(
                "Fixture UPSERT returned no id."
            )

        return UUID(str(_row_value(row, "id")))

    async def upsert_fixture_source_mapping(
        self,
        connection: Any,
        *,
        fixture_id: UUID,
        source_id: int,
        external_fixture_id: str,
        source_status: str,
        source_kickoff_at,
        payload_hash: str | None = None,
    ) -> None:
###
        result = await connection.execute(
           """
            SELECT fixture_id
            FROM core.fixture_source_ids
            WHERE source_id = %s
              AND external_fixture_id = %s
            """,
            (
                source_id,
                external_fixture_id,
            ),
        )

        row = await result.fetchone()

        if row is not None:
            existing_fixture_id = UUID(str(_row_value(row, "fixture_id")))

            if existing_fixture_id != fixture_id:
                raise RuntimeError(
                    f"External fixture {external_fixture_id} "
                    f"is already linked to fixture "
                    f"{existing_fixture_id}, cannot relink to {fixture_id}."
                )
#####

        await connection.execute(
            """
            INSERT INTO core.fixture_source_ids (
                fixture_id,
                source_id,
                external_fixture_id,
                source_status,
                source_kickoff_at,
                payload_hash,
                last_synced_at
            )
            VALUES (
                %s,
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
                fixture_id = EXCLUDED.fixture_id,
                source_status = EXCLUDED.source_status,
                source_kickoff_at = EXCLUDED.source_kickoff_at,
                payload_hash = EXCLUDED.payload_hash,
                last_synced_at = NOW()
            """,
            (
                fixture_id,
                source_id,
                external_fixture_id,
                source_status,
                source_kickoff_at,
                payload_hash,
            ),
        )

    async def attach_raw_payload(
        self,
        connection: Any,
        *,
        raw_payload_id: int,
        fixture_id: UUID,
    ) -> None:

        await connection.execute(
            """
            UPDATE raw.api_payloads
            SET
                fixture_id = %s
            WHERE id = %s
            """,
            (
                fixture_id,
                raw_payload_id,
            ),
        )