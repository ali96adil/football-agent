from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.pagination import PaginationResponse


class TeamSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    short_name: str | None = None
    country_code: str | None = None
    logo_url: str | None = None


class CompetitionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    country_code: str | None = None
    competition_type: str | None = None


class FixtureScoreSummary(BaseModel):
    home: int | None = None
    away: int | None = None
    extra_time_home: int | None = None
    extra_time_away: int | None = None
    penalties_home: int | None = None
    penalties_away: int | None = None


class FixtureSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kickoff_at: datetime
    status: str

    venue_name: str | None = None
    venue_city: str | None = None
    neutral_venue: bool

    result_confirmed: bool
    selected_for_analysis: bool

    home_team: TeamSummary
    away_team: TeamSummary
    competition: CompetitionSummary | None = None
    score: FixtureScoreSummary


class FixturesResponse(BaseModel):
    items: list[FixtureSummary]
    pagination: PaginationResponse
