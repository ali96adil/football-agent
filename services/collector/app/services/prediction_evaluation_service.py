from __future__ import annotations

import logging
from typing import Any

from app.prediction.evaluator import PredictionEvaluator
from app.repositories.match_predictions_repository import (
    get_pending_prediction_evaluations,
    save_evaluation,
)


logger = logging.getLogger(__name__)


class PredictionEvaluationService:
    """
    Evaluate stored predictions after their fixtures receive
    confirmed final scores.

    One failed prediction does not interrupt the remaining batch.
    """

    DEFAULT_LIMIT = 500

    @classmethod
    async def run(
        cls,
        connection: Any,
        *,
        limit: int = DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero.")

        pending = await get_pending_prediction_evaluations(
            connection,
            limit=limit,
        )

        evaluated = 0
        failed = 0
        errors: list[dict[str, Any]] = []

        for prediction, home_score, away_score in pending:
            try:
                evaluated_prediction = (
                    PredictionEvaluator.apply_evaluation(
                        prediction=prediction,
                        actual_home_goals=home_score,
                        actual_away_goals=away_score,
                    )
                )

                await save_evaluation(
                    connection,
                    prediction=evaluated_prediction,
                )

                evaluated += 1

            except Exception as error:
                failed += 1

                error_item = {
                    "prediction_id": (
                        str(prediction.id)
                        if prediction.id is not None
                        else None
                    ),
                    "fixture_id": (
                        str(prediction.fixture_id)
                        if prediction.fixture_id is not None
                        else None
                    ),
                    "error_type": type(error).__name__,
                    "message": str(error),
                }

                errors.append(error_item)

                logger.exception(
                    "Prediction evaluation failed: "
                    "prediction_id=%s fixture_id=%s",
                    prediction.id,
                    prediction.fixture_id,
                )

        status = cls._determine_status(
            total=len(pending),
            evaluated=evaluated,
            failed=failed,
        )

        return {
            "status": status,
            "pending_found": len(pending),
            "evaluated": evaluated,
            "failed": failed,
            "errors": errors,
        }

    @classmethod
    async def evaluate_pending(
        cls,
        connection: Any,
        *,
        limit: int = DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        """
        Compatibility alias for callers using evaluate_pending().
        """

        return await cls.run(
            connection,
            limit=limit,
        )

    @staticmethod
    def _determine_status(
        *,
        total: int,
        evaluated: int,
        failed: int,
    ) -> str:
        if total == 0:
            return "success"

        if failed == 0:
            return "success"

        if evaluated > 0:
            return "partial_success"

        return "failed"
