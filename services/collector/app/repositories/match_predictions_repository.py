from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

from app.prediction.domain.prediction_record import (
    PredictionRecord,
)


def _row_to_prediction_record(
    row: Any,
) -> PredictionRecord:
    return PredictionRecord(
        id=row["id"],
        fixture_id=row["fixture_id"],
        competition_id=row["competition_id"],
        season_id=row["season_id"],
        home_team_id=row["home_team_id"],
        away_team_id=row["away_team_id"],
        home_snapshot_id=row["home_snapshot_id"],
        away_snapshot_id=row["away_snapshot_id"],
        predicted_at=row["predicted_at"],
        kickoff_at=row["kickoff_at"],
        home_expected_goals=row[
            "home_expected_goals"
        ],
        away_expected_goals=row[
            "away_expected_goals"
        ],
        total_expected_goals=row[
            "total_expected_goals"
        ],
        home_win_probability=row[
            "home_win_probability"
        ],
        draw_probability=row["draw_probability"],
        away_win_probability=row[
            "away_win_probability"
        ],
        btts_yes_probability=row[
            "btts_yes_probability"
        ],
        btts_no_probability=row[
            "btts_no_probability"
        ],
        over_2_5_probability=row[
            "over_2_5_probability"
        ],
        under_2_5_probability=row[
            "under_2_5_probability"
        ],
        predicted_outcome=row["predicted_outcome"],
        most_likely_home_goals=row[
            "most_likely_home_goals"
        ],
        most_likely_away_goals=row[
            "most_likely_away_goals"
        ],
        most_likely_score_probability=row[
            "most_likely_score_probability"
        ],
        confidence=row["confidence"],
        expected_goals_model_version=row[
            "expected_goals_model_version"
        ],
        probability_model_version=row[
            "probability_model_version"
        ],
        feature_vector=row["feature_vector"] or {},
        most_likely_scores=(
            row["most_likely_scores"] or []
        ),
        actual_home_goals=row["actual_home_goals"],
        actual_away_goals=row["actual_away_goals"],
        actual_outcome=row["actual_outcome"],
        result_confirmed=row["result_confirmed"],
        evaluated_at=row["evaluated_at"],
        outcome_correct=row["outcome_correct"],
        exact_score_correct=row[
            "exact_score_correct"
        ],
        brier_score=row["brier_score"],
        log_loss=row["log_loss"],
        home_probability_error=row[
            "home_probability_error"
        ],
        draw_probability_error=row[
            "draw_probability_error"
        ],
        away_probability_error=row[
            "away_probability_error"
        ],
        metadata=row["metadata"] or {},
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def save_prediction(
    connection: Any,
    *,
    prediction: PredictionRecord,
) -> PredictionRecord:
    query = """
        INSERT INTO core.match_predictions (
            fixture_id,
            competition_id,
            season_id,
            home_team_id,
            away_team_id,
            home_snapshot_id,
            away_snapshot_id,
            kickoff_at,

            home_expected_goals,
            away_expected_goals,
            total_expected_goals,

            home_win_probability,
            draw_probability,
            away_win_probability,

            btts_yes_probability,
            btts_no_probability,
            over_2_5_probability,
            under_2_5_probability,

            predicted_outcome,

            most_likely_home_goals,
            most_likely_away_goals,
            most_likely_score_probability,

            confidence,
            expected_goals_model_version,
            probability_model_version,

            feature_vector,
            most_likely_scores,
            metadata
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s,
            %s, %s, %s,
            %s, %s, %s,
            %s::jsonb,
            %s::jsonb,
            %s::jsonb
        )
        ON CONFLICT (
            fixture_id,
            expected_goals_model_version,
            probability_model_version
        )
        WHERE fixture_id IS NOT NULL
        DO UPDATE SET
            home_snapshot_id = EXCLUDED.home_snapshot_id,
            away_snapshot_id = EXCLUDED.away_snapshot_id,
            predicted_at = NOW(),
            kickoff_at = EXCLUDED.kickoff_at,

            home_expected_goals =
                EXCLUDED.home_expected_goals,
            away_expected_goals =
                EXCLUDED.away_expected_goals,
            total_expected_goals =
                EXCLUDED.total_expected_goals,

            home_win_probability =
                EXCLUDED.home_win_probability,
            draw_probability =
                EXCLUDED.draw_probability,
            away_win_probability =
                EXCLUDED.away_win_probability,

            btts_yes_probability =
                EXCLUDED.btts_yes_probability,
            btts_no_probability =
                EXCLUDED.btts_no_probability,
            over_2_5_probability =
                EXCLUDED.over_2_5_probability,
            under_2_5_probability =
                EXCLUDED.under_2_5_probability,

            predicted_outcome =
                EXCLUDED.predicted_outcome,

            most_likely_home_goals =
                EXCLUDED.most_likely_home_goals,
            most_likely_away_goals =
                EXCLUDED.most_likely_away_goals,
            most_likely_score_probability =
                EXCLUDED.most_likely_score_probability,

            confidence = EXCLUDED.confidence,
            feature_vector = EXCLUDED.feature_vector,
            most_likely_scores =
                EXCLUDED.most_likely_scores,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        RETURNING *
    """

    parameters = (
        prediction.fixture_id,
        prediction.competition_id,
        prediction.season_id,
        prediction.home_team_id,
        prediction.away_team_id,
        prediction.home_snapshot_id,
        prediction.away_snapshot_id,
        prediction.kickoff_at,

        prediction.home_expected_goals,
        prediction.away_expected_goals,
        prediction.total_expected_goals,

        prediction.home_win_probability,
        prediction.draw_probability,
        prediction.away_win_probability,

        prediction.btts_yes_probability,
        prediction.btts_no_probability,
        prediction.over_2_5_probability,
        prediction.under_2_5_probability,

        prediction.predicted_outcome,

        prediction.most_likely_home_goals,
        prediction.most_likely_away_goals,
        prediction.most_likely_score_probability,

        prediction.confidence,
        prediction.expected_goals_model_version,
        prediction.probability_model_version,

        Jsonb(prediction.feature_vector),
        Jsonb(prediction.most_likely_scores),
        Jsonb(prediction.metadata),
    )

    result = await connection.execute(
        query,
        parameters,
    )

    row = await result.fetchone()

    if row is None:
        raise RuntimeError(
            "Prediction insert did not return a row."
        )

    return _row_to_prediction_record(row)


async def get_prediction_by_id(
    connection: Any,
    *,
    prediction_id: UUID,
) -> PredictionRecord | None:
    result = await connection.execute(
        """
        SELECT *
        FROM core.match_predictions
        WHERE id = %s
        LIMIT 1
        """,
        (prediction_id,),
    )

    row = await result.fetchone()

    if row is None:
        return None

    return _row_to_prediction_record(row)


async def get_prediction_for_fixture(
    connection: Any,
    *,
    fixture_id: UUID,
    expected_goals_model_version: str,
    probability_model_version: str,
) -> PredictionRecord | None:
    result = await connection.execute(
        """
        SELECT *
        FROM core.match_predictions
        WHERE fixture_id = %s
          AND expected_goals_model_version = %s
          AND probability_model_version = %s
        LIMIT 1
        """,
        (
            fixture_id,
            expected_goals_model_version,
            probability_model_version,
        ),
    )

    row = await result.fetchone()

    if row is None:
        return None

    return _row_to_prediction_record(row)


async def save_evaluation(
    connection: Any,
    *,
    prediction: PredictionRecord,
) -> PredictionRecord:
    if prediction.id is None:
        raise ValueError(
            "Prediction id is required for evaluation."
        )

    result = await connection.execute(
        """
        UPDATE core.match_predictions
        SET
            actual_home_goals = %s,
            actual_away_goals = %s,
            actual_outcome = %s,
            result_confirmed = %s,
            evaluated_at = %s,

            outcome_correct = %s,
            exact_score_correct = %s,

            brier_score = %s,
            log_loss = %s,

            home_probability_error = %s,
            draw_probability_error = %s,
            away_probability_error = %s,

            updated_at = NOW()
        WHERE id = %s
        RETURNING *
        """,
        (
            prediction.actual_home_goals,
            prediction.actual_away_goals,
            prediction.actual_outcome,
            prediction.result_confirmed,
            prediction.evaluated_at,

            prediction.outcome_correct,
            prediction.exact_score_correct,

            prediction.brier_score,
            prediction.log_loss,

            prediction.home_probability_error,
            prediction.draw_probability_error,
            prediction.away_probability_error,

            prediction.id,
        ),
    )

    row = await result.fetchone()

    if row is None:
        raise RuntimeError(
            "Prediction evaluation update "
            "did not return a row."
        )

    return _row_to_prediction_record(row)



async def get_pending_prediction_evaluations(
    connection: Any,
    *,
    limit: int = 500,
) -> list[tuple[PredictionRecord, int, int]]:
    """
    Return predictions whose fixtures have confirmed final scores
    but whose prediction evaluations have not yet been saved.
    """

    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    query = """
        SELECT
            prediction.*,
            fixture.home_score AS evaluation_home_score,
            fixture.away_score AS evaluation_away_score
        FROM core.match_predictions AS prediction
        INNER JOIN core.fixtures AS fixture
            ON fixture.id = prediction.fixture_id
        WHERE prediction.fixture_id IS NOT NULL
          AND prediction.result_confirmed = FALSE
          AND prediction.evaluated_at IS NULL
          AND fixture.result_confirmed = TRUE
          AND fixture.home_score IS NOT NULL
          AND fixture.away_score IS NOT NULL
        ORDER BY
            fixture.kickoff_at ASC,
            prediction.predicted_at ASC,
            prediction.id ASC
        LIMIT %s
    """

    result = await connection.execute(
        query,
        (limit,),
    )

    rows = await result.fetchall()

    return [
        (
            _row_to_prediction_record(row),
            int(row["evaluation_home_score"]),
            int(row["evaluation_away_score"]),
        )
        for row in rows
    ]
