from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query

from app.schemas.fixtures import FixturesResponse
from app.services.fixtures_query_service import (
    fixtures_query_service,
)


router = APIRouter(
    prefix="/api/v1/fixtures",
    tags=["Fixtures Browser"],
)


@router.get(
    "",
    response_model=FixturesResponse,
    summary="List fixtures",
)
async def list_fixtures(
    page: int = Query(
        default=1,
        ge=1,
        description="Page number",
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of fixtures per page",
    ),
    status: str | None = Query(
        default=None,
        description=(
            "Fixture status, for example scheduled, live "
            "or finished"
        ),
    ),
    competition_id: UUID | None = Query(
        default=None,
        description="Competition UUID",
    ),
    team_id: UUID | None = Query(
        default=None,
        description="Home or away team UUID",
    ),
    fixture_date: date | None = Query(
        default=None,
        alias="date",
        description="Fixture date using YYYY-MM-DD",
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        description=(
            "Search teams, competitions and venues"
        ),
    ),
    sort: Literal[
        "newest",
        "oldest",
        "upcoming",
    ] = Query(
        default="newest",
        description="Fixture ordering",
    ),
) -> FixturesResponse:
    return await fixtures_query_service.list_fixtures(
        page=page,
        page_size=page_size,
        status=status,
        competition_id=competition_id,
        team_id=team_id,
        fixture_date=fixture_date,
        search=search,
        sort=sort,
    )
