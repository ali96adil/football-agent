from __future__ import annotations

import math
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

from app.prediction.domain.prediction_evaluation import (
    PredictionEvaluation,
)
from app.prediction.domain.prediction_record import (
    PredictionRecord,
)


class PredictionEvaluator:
    """
    Evaluate one stored prediction against the real result.

    Metrics:
    - outcome accuracy
    - exact-score accuracy
    - multiclass Brier score
    - logarithmic loss
    - absolute probability error per outcome
    """

    LOG_LOSS_EPSILON = Decimal("0.000000000000001")

    @classmethod
    def evaluate(
        cls,
        *,
        prediction: PredictionRecord,
        actual_home_goals: int,
        actual_away_goals: int,
    ) -> PredictionEvaluation:
        cls._validate_actual_score(
            actual_home_goals=actual_home_goals,
            actual_away_goals=actual_away_goals,
        )

        actual_outcome = cls.determine_outcome(
            home_goals=actual_home_goals,
            away_goals=actual_away_goals,
        )

        targets = cls._outcome_targets(
            actual_outcome
        )

        probabilities = {
            "home_win": prediction.home_win_probability,
            "draw": prediction.draw_probability,
            "away_win": prediction.away_win_probability,
        }

        cls._validate_outcome_probabilities(
            probabilities
        )

        errors = {
            outcome: abs(
                probabilities[outcome]
                - targets[outcome]
            )
            for outcome in probabilities
        }

        brier_score = sum(
            (
                probabilities[outcome]
                - targets[outcome]
            ) ** 2
            for outcome in probabilities
        )

        actual_probability = probabilities[
            actual_outcome
        ]

        clipped_probability = max(
            cls.LOG_LOSS_EPSILON,
            min(
                Decimal("1"),
                actual_probability,
            ),
        )

        log_loss = Decimal(
            str(
                -math.log(
                    float(clipped_probability)
                )
            )
        )

        exact_score_correct = (
            prediction.most_likely_home_goals
            == actual_home_goals
            and prediction.most_likely_away_goals
            == actual_away_goals
        )

        return PredictionEvaluation(
            actual_home_goals=actual_home_goals,
            actual_away_goals=actual_away_goals,
            actual_outcome=actual_outcome,
            outcome_correct=(
                prediction.predicted_outcome
                == actual_outcome
            ),
            exact_score_correct=exact_score_correct,
            brier_score=brier_score.quantize(
                Decimal("0.00000001")
            ),
            log_loss=log_loss.quantize(
                Decimal("0.00000001")
            ),
            home_probability_error=errors[
                "home_win"
            ].quantize(
                Decimal("0.00000001")
            ),
            draw_probability_error=errors[
                "draw"
            ].quantize(
                Decimal("0.00000001")
            ),
            away_probability_error=errors[
                "away_win"
            ].quantize(
                Decimal("0.00000001")
            ),
            actual_outcome_probability=(
                actual_probability.quantize(
                    Decimal("0.00000001")
                )
            ),
        )

    @classmethod
    def apply_evaluation(
        cls,
        *,
        prediction: PredictionRecord,
        actual_home_goals: int,
        actual_away_goals: int,
        evaluated_at: datetime | None = None,
    ) -> PredictionRecord:
        evaluation = cls.evaluate(
            prediction=prediction,
            actual_home_goals=actual_home_goals,
            actual_away_goals=actual_away_goals,
        )

        timestamp = (
            evaluated_at
            or datetime.now(timezone.utc)
        )

        if timestamp.tzinfo is None:
            raise ValueError(
                "evaluated_at must be timezone-aware."
            )

        return replace(
            prediction,
            actual_home_goals=(
                evaluation.actual_home_goals
            ),
            actual_away_goals=(
                evaluation.actual_away_goals
            ),
            actual_outcome=(
                evaluation.actual_outcome
            ),
            result_confirmed=True,
            evaluated_at=timestamp,
            outcome_correct=(
                evaluation.outcome_correct
            ),
            exact_score_correct=(
                evaluation.exact_score_correct
            ),
            brier_score=evaluation.brier_score,
            log_loss=evaluation.log_loss,
            home_probability_error=(
                evaluation.home_probability_error
            ),
            draw_probability_error=(
                evaluation.draw_probability_error
            ),
            away_probability_error=(
                evaluation.away_probability_error
            ),
        )

    @staticmethod
    def determine_outcome(
        *,
        home_goals: int,
        away_goals: int,
    ) -> str:
        if home_goals > away_goals:
            return "home_win"

        if home_goals < away_goals:
            return "away_win"

        return "draw"

    @staticmethod
    def _outcome_targets(
        actual_outcome: str,
    ) -> dict[str, Decimal]:
        return {
            "home_win": Decimal(
                "1"
                if actual_outcome == "home_win"
                else "0"
            ),
            "draw": Decimal(
                "1"
                if actual_outcome == "draw"
                else "0"
            ),
            "away_win": Decimal(
                "1"
                if actual_outcome == "away_win"
                else "0"
            ),
        }

    @staticmethod
    def _validate_actual_score(
        *,
        actual_home_goals: int,
        actual_away_goals: int,
    ) -> None:
        if not isinstance(actual_home_goals, int):
            raise TypeError(
                "actual_home_goals must be an integer."
            )

        if not isinstance(actual_away_goals, int):
            raise TypeError(
                "actual_away_goals must be an integer."
            )

        if actual_home_goals < 0:
            raise ValueError(
                "actual_home_goals cannot be negative."
            )

        if actual_away_goals < 0:
            raise ValueError(
                "actual_away_goals cannot be negative."
            )

    @staticmethod
    def _validate_outcome_probabilities(
        probabilities: dict[str, Decimal],
    ) -> None:
        for name, probability in probabilities.items():
            if not (
                Decimal("0")
                <= probability
                <= Decimal("1")
            ):
                raise ValueError(
                    f"{name} probability must be "
                    "between 0 and 1."
                )

        total = sum(
            probabilities.values(),
            Decimal("0"),
        )

        tolerance = Decimal("0.0010")

        if abs(total - Decimal("1")) > tolerance:
            raise ValueError(
                "Outcome probabilities must sum "
                "approximately to 1."
            )
