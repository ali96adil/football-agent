from __future__ import annotations

from typing import Any

from app.normalizers.canonical_fixture import CanonicalFixture
from app.repositories.entity_repository import EntityRepository
from app.repositories.fixture_repository import FixtureRepository


class NormalizationService:
    """
    Persist one canonical fixture into the database.

    This service owns the transaction and orchestrates:

    Competition
        ↓
    Season
        ↓
    Home Team
        ↓
    Away Team
        ↓
    Fixture
        ↓
    Fixture Source Mapping
        ↓
    Raw Payload Link
    """

    def __init__(self) -> None:
        self.entities = EntityRepository()
        self.fixtures = FixtureRepository()

    async def normalize_fixture(
        self,
        connection: Any,
        *,
        fixture: CanonicalFixture,
        source_id: int,
        raw_payload_id: int,
        payload_hash: str | None = None,
    ):
        async with connection.transaction():

            competition_id = await self.entities.upsert_competition(
                connection,
                fixture.competition,
            )

            season_id = await self.entities.upsert_season(
                connection,
                competition_id,
                fixture.season,
            )

            home_team_id = await self.entities.upsert_team(
                connection,
                source_id=source_id,
                team=fixture.home_team,
            )

            away_team_id = await self.entities.upsert_team(
                connection,
                source_id=source_id,
                team=fixture.away_team,
            )

            winner_team_id = None

            if fixture.winner_external_team_id:

                if (
                    fixture.winner_external_team_id
                    == fixture.home_team.external_id
                ):
                    winner_team_id = home_team_id

                elif (
                    fixture.winner_external_team_id
                    == fixture.away_team.external_id
                ):
                    winner_team_id = away_team_id

            fixture_id = await self.fixtures.upsert_fixture(
                connection,
                fixture=fixture,
                competition_id=competition_id,
                season_id=season_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                winner_team_id=winner_team_id,
            )

            await self.fixtures.upsert_fixture_source_mapping(
                connection,
                fixture_id=fixture_id,
                source_id=source_id,
                external_fixture_id=fixture.external_id,
                source_status=fixture.source_status,
                source_kickoff_at=fixture.kickoff_at,
                payload_hash=payload_hash,
            )

            await self.fixtures.attach_raw_payload(
                connection,
                raw_payload_id=raw_payload_id,
                fixture_id=fixture_id,
            )

            return fixture_id