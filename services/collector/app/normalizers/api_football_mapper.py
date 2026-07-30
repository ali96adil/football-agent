from datetime import datetime
from typing import Any

from app.normalizers.canonical_fixture import (
    CanonicalCompetition,
    CanonicalFixture,
    CanonicalSeason,
    CanonicalTeam,
)


STATUS_MAPPING = {
    "TBD": "scheduled",
    "NS": "scheduled",

    "1H": "live",
    "HT": "live",
    "2H": "live",
    "ET": "live",
    "BT": "live",
    "P": "live",
    "LIVE": "live",

    "SUSP": "suspended",
    "INT": "suspended",

    "PST": "postponed",

    "CANC": "cancelled",
    "ABD": "cancelled",

    "FT": "finished",
    "AET": "finished",
    "PEN": "finished",
    "AWD": "finished",
    "WO": "finished",
}


COUNTRY_CODE_MAPPING = {
    "England": "ENG",
    "Scotland": "SCO",
    "Wales": "WAL",
    "Northern Ireland": "NIR",
    "Ireland": "IRL",

    "Germany": "DEU",
    "France": "FRA",
    "Italy": "ITA",
    "Spain": "ESP",
    "Portugal": "POR",
    "Netherlands": "NLD",
    "Belgium": "BEL",
    "Austria": "AUT",
    "Switzerland": "CHE",
    "Denmark": "DNK",
    "Sweden": "SWE",
    "Norway": "NOR",
    "Finland": "FIN",
    "Poland": "POL",
    "Greece": "GRC",
    "Turkey": "TUR",
    "Czech-Republic": "CZE",
    "Czech Republic": "CZE",
    "Croatia": "HRV",
    "Serbia": "SRB",
    "Ukraine": "UKR",
    "Romania": "ROU",

    "Brazil": "BRA",
    "Argentina": "ARG",
    "Uruguay": "URY",
    "Colombia": "COL",
    "Chile": "CHL",
    "Mexico": "MEX",
    "USA": "USA",
    "United States": "USA",
    "Canada": "CAN",

    "Saudi-Arabia": "SAU",
    "Saudi Arabia": "SAU",
    "Qatar": "QAT",
    "United-Arab-Emirates": "ARE",
    "United Arab Emirates": "ARE",
    "Iraq": "IRQ",
    "Iran": "IRN",
    "Japan": "JPN",
    "China": "CHN",
    "South-Korea": "KOR",
    "South Korea": "KOR",

    "Australia": "AUS",
    "Egypt": "EGY",
    "Morocco": "MAR",
    "Algeria": "DZA",
    "Tunisia": "TUN",
    "South-Africa": "ZAF",
    "South Africa": "ZAF",

    "World": "INT",
}


FINISHED_STATUSES = {
    "FT",
    "AET",
    "PEN",
    "AWD",
    "WO",
}


def _required_mapping(
    item: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    value = item.get(key)

    if not isinstance(value, dict):
        raise ValueError(
            f"API-Football fixture field {key!r} must be an object"
        )

    return value


def _required_value(
    item: dict[str, Any],
    key: str,
    context: str,
) -> Any:
    value = item.get(key)

    if value is None or value == "":
        raise ValueError(
            f"API-Football {context} field {key!r} is missing"
        )

    return value


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None

    return int(value)


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)

    if parsed.tzinfo is None:
        raise ValueError(
            "API-Football fixture date must include timezone information"
        )

    return parsed


def map_api_football_status(
    status_short: str | None,
) -> str:
    normalized = (status_short or "").upper()
    return STATUS_MAPPING.get(normalized, "unknown")


def map_api_football_fixture(
    item: dict[str, Any],
) -> CanonicalFixture:
    if not isinstance(item, dict):
        raise ValueError(
            "API-Football fixture item must be an object"
        )

    fixture = _required_mapping(item, "fixture")
    league = _required_mapping(item, "league")
    teams = _required_mapping(item, "teams")

    home_team = _required_mapping(teams, "home")
    away_team = _required_mapping(teams, "away")

    venue = fixture.get("venue") or {}
    status = fixture.get("status") or {}

    goals = item.get("goals") or {}
    score = item.get("score") or {}

    fulltime = score.get("fulltime") or {}
    extratime = score.get("extratime") or {}
    penalty = score.get("penalty") or {}
    halftime = score.get("halftime") or {}

    fixture_external_id = str(
        _required_value(
            fixture,
            "id",
            "fixture",
        )
    )

    fixture_date = str(
        _required_value(
            fixture,
            "date",
            "fixture",
        )
    )

    league_external_id = str(
        _required_value(
            league,
            "id",
            "league",
        )
    )

    league_name = str(
        _required_value(
            league,
            "name",
            "league",
        )
    )

    season_year = _required_value(
        league,
        "season",
        "league",
    )

    home_external_id = str(
        _required_value(
            home_team,
            "id",
            "home team",
        )
    )

    away_external_id = str(
        _required_value(
            away_team,
            "id",
            "away team",
        )
    )

    home_name = str(
        _required_value(
            home_team,
            "name",
            "home team",
        )
    )

    away_name = str(
        _required_value(
            away_team,
            "name",
            "away team",
        )
    )

    country_name = league.get("country")
    country_code = COUNTRY_CODE_MAPPING.get(country_name)

    status_short = status.get("short")
    canonical_status = map_api_football_status(
        status_short
    )

    home_score = fulltime.get("home")
    away_score = fulltime.get("away")

    if home_score is None:
        home_score = goals.get("home")

    if away_score is None:
        away_score = goals.get("away")

    winner_external_team_id: str | None = None

    if home_team.get("winner") is True:
        winner_external_team_id = home_external_id
    elif away_team.get("winner") is True:
        winner_external_team_id = away_external_id

    normalized_status_short = (
        str(status_short).upper()
        if status_short is not None
        else None
    )

    competition = CanonicalCompetition(
        external_id=league_external_id,
        name=league_name,
        country_name=country_name,
        country_code=country_code,
        metadata={
            "api_football_id": int(league_external_id),
            "logo": league.get("logo"),
            "flag": league.get("flag"),
            "standings_supported": league.get(
                "standings"
            ),
        },
    )

    season = CanonicalSeason(
        label=str(season_year),
        metadata={
            "api_football_season": season_year,
        },
    )

    canonical_home_team = CanonicalTeam(
        external_id=home_external_id,
        name=home_name,
        short_name=home_name,
        country_code=country_code,
        logo_url=home_team.get("logo"),
        metadata={
            "api_football_id": int(home_external_id),
        },
    )

    canonical_away_team = CanonicalTeam(
        external_id=away_external_id,
        name=away_name,
        short_name=away_name,
        country_code=country_code,
        logo_url=away_team.get("logo"),
        metadata={
            "api_football_id": int(away_external_id),
        },
    )

    return CanonicalFixture(
        external_id=fixture_external_id,
        competition=competition,
        season=season,
        home_team=canonical_home_team,
        away_team=canonical_away_team,
        kickoff_at=_parse_datetime(fixture_date),
        venue_name=venue.get("name"),
        venue_city=venue.get("city"),
        neutral_venue=False,
        status=canonical_status,
        source_status=normalized_status_short,
        home_score=_optional_int(home_score),
        away_score=_optional_int(away_score),
        extra_time_home=_optional_int(
            extratime.get("home")
        ),
        extra_time_away=_optional_int(
            extratime.get("away")
        ),
        penalties_home=_optional_int(
            penalty.get("home")
        ),
        penalties_away=_optional_int(
            penalty.get("away")
        ),
        winner_external_team_id=winner_external_team_id,
        result_confirmed=(
            normalized_status_short in FINISHED_STATUSES
        ),
        metadata={
            "round": league.get("round"),
            "referee": fixture.get("referee"),
            "timezone": fixture.get("timezone"),
            "timestamp": fixture.get("timestamp"),
            "venue_id": venue.get("id"),
            "elapsed": status.get("elapsed"),
            "status_long": status.get("long"),
            "status_extra": status.get("extra"),
            "periods": fixture.get("periods"),
            "half_time_score": {
                "home": halftime.get("home"),
                "away": halftime.get("away"),
            },
        },
    )
