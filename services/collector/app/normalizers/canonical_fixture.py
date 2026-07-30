from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True, frozen=True)
class CanonicalCompetition:
    external_id: str
    name: str
    country_name: str | None
    country_code: str | None
    competition_type: str = "LEAGUE"
    gender: str = "MALE"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CanonicalSeason:
    label: str
    starts_on: str | None = None
    ends_on: str | None = None
    is_current: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CanonicalTeam:
    external_id: str
    name: str
    short_name: str | None
    country_code: str | None
    logo_url: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CanonicalFixture:
    external_id: str

    competition: CanonicalCompetition
    season: CanonicalSeason

    home_team: CanonicalTeam
    away_team: CanonicalTeam

    kickoff_at: datetime

    venue_name: str | None
    venue_city: str | None
    neutral_venue: bool

    status: str
    source_status: str | None

    home_score: int | None
    away_score: int | None

    extra_time_home: int | None
    extra_time_away: int | None

    penalties_home: int | None
    penalties_away: int | None

    winner_external_team_id: str | None
    result_confirmed: bool

    metadata: dict[str, Any] = field(default_factory=dict)
