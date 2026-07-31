from datetime import date
from math import ceil
from uuid import UUID

from app.db.connection import pool
from app.repositories.fixtures_query_repository import (
    FixturesQueryRepository,
)
from app.schemas.fixtures import (
    CompetitionSummary,
    FixtureScoreSummary,
    FixtureSummary,
    FixturesResponse,
    TeamSummary,
)
from app.schemas.pagination import PaginationResponse


class FixturesQueryService:
    def __init__(self) -> None:
        self.repository = FixturesQueryRepository()

    async def list_fixtures(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        competition_id: UUID | None = None,
        team_id: UUID | None = None,
        fixture_date: date | None = None,
        search: str | None = None,
        sort: str = "newest",
    ) -> FixturesResponse:
        offset = (page - 1) * page_size

        async with pool.connection() as connection:
            rows, total = await self.repository.get_fixtures(
                connection,
                offset=offset,
                limit=page_size,
                status=status,
                competition_id=competition_id,
                team_id=team_id,
                fixture_date=fixture_date,
                search=search,
                sort=sort,
            )

        items = [
            self._map_fixture(row)
            for row in rows
        ]

        total_pages = (
            ceil(total / page_size)
            if total > 0
            else 0
        )

        return FixturesResponse(
            items=items,
            pagination=PaginationResponse(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
            ),
        )

    @staticmethod
    def _map_fixture(row: dict) -> FixtureSummary:
        competition = None

        if row["competition_id"] is not None:
            competition = CompetitionSummary(
                id=row["competition_id"],
                name=row["competition_name"],
                country_code=row[
                    "competition_country_code"
                ],
                competition_type=row[
                    "competition_type"
                ],
            )

        return FixtureSummary(
            id=row["id"],
            kickoff_at=row["kickoff_at"],
            status=row["fixture_status"],
            venue_name=row["venue_name"],
            venue_city=row["venue_city"],
            neutral_venue=row["neutral_venue"],
            result_confirmed=row["result_confirmed"],
            selected_for_analysis=row[
                "selected_for_analysis"
            ],
            home_team=TeamSummary(
                id=row["home_team_id"],
                name=row["home_team_name"],
                short_name=row[
                    "home_team_short_name"
                ],
                country_code=row[
                    "home_team_country_code"
                ],
                logo_url=row[
                    "home_team_logo_url"
                ],
            ),
            away_team=TeamSummary(
                id=row["away_team_id"],
                name=row["away_team_name"],
                short_name=row[
                    "away_team_short_name"
                ],
                country_code=row[
                    "away_team_country_code"
                ],
                logo_url=row[
                    "away_team_logo_url"
                ],
            ),
            competition=competition,
            score=FixtureScoreSummary(
                home=row["home_score"],
                away=row["away_score"],
                extra_time_home=row[
                    "extra_time_home"
                ],
                extra_time_away=row[
                    "extra_time_away"
                ],
                penalties_home=row[
                    "penalties_home"
                ],
                penalties_away=row[
                    "penalties_away"
                ],
            ),
        )


fixtures_query_service = FixturesQueryService()
