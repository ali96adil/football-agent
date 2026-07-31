from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class TeamResponse(BaseModel):
    id: UUID
    name: str
    short_name: str | None = None
    logo_url: str | None = None


class CompetitionResponse(BaseModel):
    id: UUID
    name: str
    country_code: str | None = None


class PredictionResponse(BaseModel):
    id: UUID
    fixture_id: UUID | None = None

    predicted_at: datetime | None = None
    kickoff_at: datetime | None = None

    competition: CompetitionResponse
    home_team: TeamResponse
    away_team: TeamResponse

    predicted_outcome: str
    confidence: float

    home_expected_goals: float
    away_expected_goals: float
    total_expected_goals: float

    home_win_probability: float
    draw_probability: float
    away_win_probability: float

    btts_yes_probability: float
    btts_no_probability: float

    over_2_5_probability: float
    under_2_5_probability: float

    most_likely_home_goals: int | None = None
    most_likely_away_goals: int | None = None
    most_likely_score_probability: float | None = None
    
    actual_home_goals: int | None = None
    actual_away_goals: int | None = None
    actual_outcome: str | None = None

    result_confirmed: bool = False
    evaluated_at: datetime | None = None

    outcome_correct: bool | None = None
    exact_score_correct: bool | None = None

    brier_score: float | None = None
    log_loss: float | None = None    


def row_to_prediction_response(
    row: dict[str, Any],
) -> PredictionResponse:
    return PredictionResponse(
        id=row["id"],
        fixture_id=row["fixture_id"],
        predicted_at=row["predicted_at"],
        kickoff_at=row["kickoff_at"],

        competition=CompetitionResponse(
            id=row["competition_id"],
            name=row["competition_name"],
            country_code=row["competition_country_code"],
        ),

        home_team=TeamResponse(
            id=row["home_team_id"],
            name=row["home_team_name"],
            short_name=row["home_team_short_name"],
            logo_url=row["home_team_logo_url"],
        ),

        away_team=TeamResponse(
            id=row["away_team_id"],
            name=row["away_team_name"],
            short_name=row["away_team_short_name"],
            logo_url=row["away_team_logo_url"],
        ),

        predicted_outcome=row["predicted_outcome"],
        confidence=float(row["confidence"]),

        home_expected_goals=float(
            row["home_expected_goals"]
        ),
        away_expected_goals=float(
            row["away_expected_goals"]
        ),
        total_expected_goals=float(
            row["total_expected_goals"]
        ),

        home_win_probability=float(
            row["home_win_probability"]
        ),
        draw_probability=float(
            row["draw_probability"]
        ),
        away_win_probability=float(
            row["away_win_probability"]
        ),

        btts_yes_probability=float(
            row["btts_yes_probability"]
        ),
        btts_no_probability=float(
            row["btts_no_probability"]
        ),

        over_2_5_probability=float(
            row["over_2_5_probability"]
        ),
        under_2_5_probability=float(
            row["under_2_5_probability"]
        ),

        most_likely_home_goals=row[
            "most_likely_home_goals"
        ],
        most_likely_away_goals=row[
            "most_likely_away_goals"
        ],

        most_likely_score_probability=(
            float(row["most_likely_score_probability"])
            if row["most_likely_score_probability"] is not None
            else None
        ),
        actual_home_goals=row["actual_home_goals"],
        actual_away_goals=row["actual_away_goals"],
        actual_outcome=row["actual_outcome"],

        result_confirmed=row["result_confirmed"],
        evaluated_at=row["evaluated_at"],

        outcome_correct=row["outcome_correct"],
        exact_score_correct=row["exact_score_correct"],

        brier_score=(
            float(row["brier_score"])
            if row["brier_score"] is not None
            else None
        ),

        log_loss=(
            float(row["log_loss"])
            if row["log_loss"] is not None
            else None
        ),        
    )
