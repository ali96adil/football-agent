from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


VALID_OUTCOMES = {
    "home_win",
    "draw",
    "away_win",
}


@dataclass(frozen=True, slots=True)
class PredictionRecord:
    id: UUID | None = None
    fixture_id: UUID | None = None

    competition_id: UUID | None = None
    season_id: UUID | None = None

    home_team_id: UUID | None = None
    away_team_id: UUID | None = None

    home_snapshot_id: UUID | None = None
    away_snapshot_id: UUID | None = None

    predicted_at: datetime | None = None
    kickoff_at: datetime | None = None

    home_expected_goals: Decimal = Decimal("0")
    away_expected_goals: Decimal = Decimal("0")
    total_expected_goals: Decimal = Decimal("0")

    home_win_probability: Decimal = Decimal("0")
    draw_probability: Decimal = Decimal("0")
    away_win_probability: Decimal = Decimal("0")

    btts_yes_probability: Decimal = Decimal("0")
    btts_no_probability: Decimal = Decimal("0")

    over_2_5_probability: Decimal = Decimal("0")
    under_2_5_probability: Decimal = Decimal("0")

    predicted_outcome: str = "draw"

    most_likely_home_goals: int | None = None
    most_likely_away_goals: int | None = None
    most_likely_score_probability: Decimal | None = None

    confidence: Decimal = Decimal("0")

    expected_goals_model_version: str = ""
    probability_model_version: str = ""

    feature_vector: dict[str, Any] = field(
        default_factory=dict
    )

    most_likely_scores: list[dict[str, Any]] = field(
        default_factory=list
    )

    actual_home_goals: int | None = None
    actual_away_goals: int | None = None
    actual_outcome: str | None = None

    result_confirmed: bool = False
    evaluated_at: datetime | None = None

    outcome_correct: bool | None = None
    exact_score_correct: bool | None = None

    brier_score: Decimal | None = None
    log_loss: Decimal | None = None

    home_probability_error: Decimal | None = None
    draw_probability_error: Decimal | None = None
    away_probability_error: Decimal | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if (
            self.home_team_id is not None
            and self.away_team_id is not None
            and self.home_team_id == self.away_team_id
        ):
            raise ValueError(
                "Home and away teams cannot be the same."
            )

        if self.predicted_outcome not in VALID_OUTCOMES:
            raise ValueError(
                "predicted_outcome must be home_win, "
                "draw or away_win."
            )

        if (
            self.actual_outcome is not None
            and self.actual_outcome not in VALID_OUTCOMES
        ):
            raise ValueError(
                "actual_outcome must be home_win, "
                "draw or away_win."
            )

        expected_goals = (
            self.home_expected_goals,
            self.away_expected_goals,
            self.total_expected_goals,
        )

        if any(value < 0 for value in expected_goals):
            raise ValueError(
                "Expected-goals values cannot be negative."
            )

        probabilities = (
            self.home_win_probability,
            self.draw_probability,
            self.away_win_probability,
            self.btts_yes_probability,
            self.btts_no_probability,
            self.over_2_5_probability,
            self.under_2_5_probability,
            self.confidence,
        )

        for probability in probabilities:
            if not Decimal("0") <= probability <= Decimal("1"):
                raise ValueError(
                    "Probabilities must be between 0 and 1."
                )

        actual_scores = (
            self.actual_home_goals,
            self.actual_away_goals,
        )

        for score in actual_scores:
            if score is not None and score < 0:
                raise ValueError(
                    "Actual scores cannot be negative."
                )

    @property
    def most_likely_scoreline(self) -> str | None:
        if (
            self.most_likely_home_goals is None
            or self.most_likely_away_goals is None
        ):
            return None

        return (
            f"{self.most_likely_home_goals}-"
            f"{self.most_likely_away_goals}"
        )

    @property
    def actual_scoreline(self) -> str | None:
        if (
            self.actual_home_goals is None
            or self.actual_away_goals is None
        ):
            return None

        return (
            f"{self.actual_home_goals}-"
            f"{self.actual_away_goals}"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id) if self.id else None,
            "fixture_id": (
                str(self.fixture_id)
                if self.fixture_id
                else None
            ),
            "competition_id": (
                str(self.competition_id)
                if self.competition_id
                else None
            ),
            "season_id": (
                str(self.season_id)
                if self.season_id
                else None
            ),
            "home_team_id": (
                str(self.home_team_id)
                if self.home_team_id
                else None
            ),
            "away_team_id": (
                str(self.away_team_id)
                if self.away_team_id
                else None
            ),
            "home_snapshot_id": (
                str(self.home_snapshot_id)
                if self.home_snapshot_id
                else None
            ),
            "away_snapshot_id": (
                str(self.away_snapshot_id)
                if self.away_snapshot_id
                else None
            ),
            "predicted_at": (
                self.predicted_at.isoformat()
                if self.predicted_at
                else None
            ),
            "kickoff_at": (
                self.kickoff_at.isoformat()
                if self.kickoff_at
                else None
            ),
            "expected_goals": {
                "home": float(self.home_expected_goals),
                "away": float(self.away_expected_goals),
                "total": float(self.total_expected_goals),
            },
            "outcome_probabilities": {
                "home_win": float(
                    self.home_win_probability
                ),
                "draw": float(self.draw_probability),
                "away_win": float(
                    self.away_win_probability
                ),
            },
            "goals_probabilities": {
                "btts_yes": float(
                    self.btts_yes_probability
                ),
                "btts_no": float(
                    self.btts_no_probability
                ),
                "over_2_5": float(
                    self.over_2_5_probability
                ),
                "under_2_5": float(
                    self.under_2_5_probability
                ),
            },
            "predicted_outcome": self.predicted_outcome,
            "most_likely_scoreline": (
                self.most_likely_scoreline
            ),
            "most_likely_score_probability": (
                float(self.most_likely_score_probability)
                if self.most_likely_score_probability
                is not None
                else None
            ),
            "confidence": float(self.confidence),
            "model_versions": {
                "expected_goals": (
                    self.expected_goals_model_version
                ),
                "probability": (
                    self.probability_model_version
                ),
            },
            "actual_result": {
                "scoreline": self.actual_scoreline,
                "outcome": self.actual_outcome,
                "confirmed": self.result_confirmed,
            },
            "evaluation": {
                "outcome_correct": self.outcome_correct,
                "exact_score_correct": (
                    self.exact_score_correct
                ),
                "brier_score": (
                    float(self.brier_score)
                    if self.brier_score is not None
                    else None
                ),
                "log_loss": (
                    float(self.log_loss)
                    if self.log_loss is not None
                    else None
                ),
            },
            "feature_vector": self.feature_vector,
            "most_likely_scores": (
                self.most_likely_scores
            ),
            "metadata": self.metadata,
        }
