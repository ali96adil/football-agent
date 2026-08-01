from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.api.routes.competitions import (
    sync_football_data_competitions,
)
from app.api.routes.fixtures import (
    sync_football_data_fixtures,
)
from app.api.routes.standings import (
    sync_football_data_standings,
)
from app.db.connection import pool
from app.job_errors import safe_failure
from app.services.prediction_evaluation_service import (
    PredictionEvaluationService,
)
from app.services.scheduled_prediction_service import (
    ScheduledPredictionService,
)


router = APIRouter(
    prefix="",
    tags=["General Sync"],
)

logger = logging.getLogger("football-collector.sync")

FOOTBALL_DATA_MAX_WINDOW_DAYS = 10


def build_fixture_windows(
    start: date,
    end: date,
    max_window_days: int = FOOTBALL_DATA_MAX_WINDOW_DAYS,
) -> list[tuple[date, date]]:
    """
    Split an inclusive date range into non-overlapping windows.

    football-data.org accepts a maximum period of 10 calendar days.
    Because dateFrom and dateTo are inclusive, each window contains at
    most max_window_days dates.

    Example:
        2026-07-30 -> 2026-08-18

        Window 1: 2026-07-30 -> 2026-08-08
        Window 2: 2026-08-09 -> 2026-08-18
    """

    if max_window_days < 1:
        raise ValueError("max_window_days must be at least 1")

    if start > end:
        raise ValueError("start cannot be later than end")

    windows: list[tuple[date, date]] = []
    current_start = start

    while current_start <= end:
        current_end = min(
            current_start + timedelta(days=max_window_days - 1),
            end,
        )

        windows.append(
            (
                current_start,
                current_end,
            )
        )

        current_start = current_end + timedelta(days=1)

    return windows


def serialize_http_exception(
    exc: HTTPException,
) -> dict[str, Any]:
    """
    Convert FastAPI HTTPException data into a JSON-safe dictionary.
    """

    return {
        "status_code": exc.status_code,
        "detail": exc.detail,
    }


@router.post("/sync")
async def sync_all(
    fixture_days: int = Query(
        default=14,
        ge=1,
        le=60,
        description="Number of fixture days to sync from today",
    ),
    prediction_limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum scheduled fixtures to predict",
    ),
    evaluation_limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum finished predictions to evaluate",
    ),
    window_size: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Number of historical matches used for snapshots",
    ),
    calculation_version: str = Query(
        default="v1",
        min_length=1,
        max_length=100,
        description="Snapshot calculation version",
    ),
) -> dict[str, Any]:
    started_at = time.perf_counter()

    started_on = date.today()
    date_to = started_on + timedelta(days=fixture_days)

    calculation_version = calculation_version.strip()

    if not calculation_version:
        raise HTTPException(
            status_code=422,
            detail="calculation_version must not be empty.",
        )

    result: dict[str, Any] = {
        "status": "success",
        "operation": "sync_all",
        "date_from": started_on.isoformat(),
        "date_to": date_to.isoformat(),
        "settings": {
            "fixture_days": fixture_days,
            "fixture_window_days": FOOTBALL_DATA_MAX_WINDOW_DAYS,
            "prediction_limit": prediction_limit,
            "evaluation_limit": evaluation_limit,
            "window_size": window_size,
            "calculation_version": calculation_version,
        },
        "competitions": None,
        "fixtures": None,
        "standings": {
            "attempted": 0,
            "succeeded": 0,
            "failed": 0,
            "results": [],
            "errors": [],
        },
        "evaluation": None,
        "predictions": None,
        "errors": [],
        "duration_seconds": None,
    }

    def register_error(
        *,
        stage: str,
        exc: Exception,
        context: dict[str, Any] | None = None,
    ) -> None:
        result["status"] = "partial_success"

        error_item: dict[str, Any] = {
            "stage": stage,
            "error_type": type(exc).__name__,
            **safe_failure(exc),
        }

        if isinstance(exc, HTTPException):
            error_item.update(
                serialize_http_exception(exc)
            )

        if context:
            error_item.update(context)

        result["errors"].append(error_item)

    # ------------------------------------------------------------------
    # Stage 1: Sync competitions
    # ------------------------------------------------------------------

    try:
        result["competitions"] = (
            await sync_football_data_competitions()
        )

    except Exception as exc:
        logger.exception("Competition sync failed")

        register_error(
            stage="competitions",
            exc=exc,
        )

        result["competitions"] = {
            "status": "failed",
            "error_type": type(exc).__name__,
            **safe_failure(exc),
        }

    # ------------------------------------------------------------------
    # Stage 2: Load competitions from database
    # ------------------------------------------------------------------

    competitions: list[dict[str, Any]] = []

    try:
        async with pool.connection() as connection:
            competitions_result = await connection.execute(
                """
                SELECT
                    c.metadata->>'football_data_code' AS code,
                    c.canonical_name,
                    c.competition_type,
                    EXISTS (
                        SELECT 1
                        FROM core.seasons s
                        WHERE s.competition_id = c.id
                          AND s.is_current = TRUE
                    ) AS has_current_season
                FROM core.competitions c
                WHERE
                    c.metadata->>'football_data_code' IS NOT NULL
                    AND c.metadata->>'football_data_code' <> ''
                ORDER BY c.canonical_name
                """
            )

            competition_rows = (
                await competitions_result.fetchall()
            )

            competitions = [
                dict(row)
                for row in competition_rows
            ]

    except Exception as exc:
        logger.exception(
            "Unable to load competitions from database"
        )

        register_error(
            stage="load_competitions",
            exc=exc,
        )

    all_codes = sorted(
        {
            str(row["code"]).strip().upper()
            for row in competitions
            if row.get("code")
        }
    )

    current_leagues = [
        row
        for row in competitions
        if row.get("has_current_season")
        and row.get("competition_type") == "LEAGUE"
        and row.get("code")
    ]

    # ------------------------------------------------------------------
    # Stage 3: Sync fixtures using provider-safe date windows
    # ------------------------------------------------------------------

    if all_codes:
        fixture_windows = build_fixture_windows(
            started_on,
            date_to,
        )

        fixture_summary: dict[str, Any] = {
            "status": "success",
            "provider": "football-data.org",
            "operation": "fixtures_chunked_sync",
            "date_from": started_on.isoformat(),
            "date_to": date_to.isoformat(),
            "competition_count": len(all_codes),
            "competitions": all_codes,
            "window_size_days": FOOTBALL_DATA_MAX_WINDOW_DAYS,
            "windows_total": len(fixture_windows),
            "windows_succeeded": 0,
            "windows_failed": 0,
            "matches_received": 0,
            "results": [],
            "errors": [],
        }

        competition_codes = ",".join(all_codes)

        for window_number, (
            window_start,
            window_end,
        ) in enumerate(
            fixture_windows,
            start=1,
        ):
            window_started_at = time.perf_counter()

            logger.info(
                (
                    "Starting fixture window %s/%s: "
                    "%s -> %s"
                ),
                window_number,
                len(fixture_windows),
                window_start.isoformat(),
                window_end.isoformat(),
            )

            try:
                window_result = (
                    await sync_football_data_fixtures(
                        date_from=window_start.isoformat(),
                        date_to=window_end.isoformat(),
                        competitions=competition_codes,
                    )
                )

                collection_result = (
                    window_result.get("collection") or {}
                )

                normalization_result = (
                    window_result.get("normalization") or {}
                )

                matches_received = int(
                    collection_result.get("matches_received")
                    or normalization_result.get("matches_received")
                    or window_result.get("matches_received")
                    or 0
                )

                window_duration = round(
                    time.perf_counter()
                    - window_started_at,
                    3,
                )

                fixture_summary["windows_succeeded"] += 1
                fixture_summary["matches_received"] += (
                    matches_received
                )

                fixture_summary["results"].append(
                    {
                        "window": window_number,
                        "status": "success",
                        "date_from": window_start.isoformat(),
                        "date_to": window_end.isoformat(),
                        "matches_received": matches_received,
                        "duration_seconds": window_duration,
                        "result": window_result,
                    }
                )

                logger.info(
                    (
                        "Fixture window %s/%s completed: "
                        "%s -> %s, matches=%s, "
                        "duration_seconds=%s"
                    ),
                    window_number,
                    len(fixture_windows),
                    window_start.isoformat(),
                    window_end.isoformat(),
                    matches_received,
                    window_duration,
                )

            except HTTPException as exc:
                window_duration = round(
                    time.perf_counter()
                    - window_started_at,
                    3,
                )

                logger.exception(
                    (
                        "Fixture window %s/%s failed: "
                        "%s -> %s, status_code=%s"
                    ),
                    window_number,
                    len(fixture_windows),
                    window_start.isoformat(),
                    window_end.isoformat(),
                    exc.status_code,
                )

                fixture_summary["status"] = (
                    "partial_success"
                )
                fixture_summary["windows_failed"] += 1

                window_error = {
                    "window": window_number,
                    "status": "failed",
                    "date_from": window_start.isoformat(),
                    "date_to": window_end.isoformat(),
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                    "duration_seconds": window_duration,
                }

                fixture_summary["errors"].append(
                    window_error
                )

                register_error(
                    stage="fixtures",
                    exc=exc,
                    context={
                        "window": window_number,
                        "date_from": (
                            window_start.isoformat()
                        ),
                        "date_to": window_end.isoformat(),
                    },
                )

            except Exception as exc:
                window_duration = round(
                    time.perf_counter()
                    - window_started_at,
                    3,
                )

                logger.exception(
                    (
                        "Unexpected fixture window "
                        "failure %s/%s: %s -> %s"
                    ),
                    window_number,
                    len(fixture_windows),
                    window_start.isoformat(),
                    window_end.isoformat(),
                )

                fixture_summary["status"] = (
                    "partial_success"
                )
                fixture_summary["windows_failed"] += 1

                window_error = {
                    "window": window_number,
                    "status": "failed",
                    "date_from": window_start.isoformat(),
                    "date_to": window_end.isoformat(),
                    "error_type": type(exc).__name__,
                    **safe_failure(exc),
                    "duration_seconds": window_duration,
                }

                fixture_summary["errors"].append(
                    window_error
                )

                register_error(
                    stage="fixtures",
                    exc=exc,
                    context={
                        "window": window_number,
                        "date_from": (
                            window_start.isoformat()
                        ),
                        "date_to": window_end.isoformat(),
                    },
                )

        if (
            fixture_summary["windows_failed"]
            == fixture_summary["windows_total"]
        ):
            fixture_summary["status"] = "failed"

        elif fixture_summary["windows_failed"] > 0:
            fixture_summary["status"] = (
                "partial_success"
            )

        result["fixtures"] = fixture_summary

    else:
        result["fixtures"] = {
            "status": "skipped",
            "reason": (
                "No Football-Data competition "
                "codes found."
            ),
        }

    # ------------------------------------------------------------------
    # Stage 4: Sync standings
    # ------------------------------------------------------------------

    for competition in current_leagues:
        code = str(
            competition["code"]
        ).strip().upper()

        result["standings"]["attempted"] += 1

        try:
            standing_result = (
                await sync_football_data_standings(
                    competition=code,
                )
            )

            result["standings"]["succeeded"] += 1

            result["standings"]["results"].append(
                {
                    "competition": code,
                    "name": competition[
                        "canonical_name"
                    ],
                    "result": standing_result,
                }
            )

        except HTTPException as exc:
            logger.exception(
                (
                    "Standing sync failed for "
                    "competition=%s"
                ),
                code,
            )

            result["status"] = "partial_success"
            result["standings"]["failed"] += 1

            error_item = {
                "competition": code,
                "name": competition[
                    "canonical_name"
                ],
                "status_code": exc.status_code,
                "detail": exc.detail,
            }

            result["standings"]["errors"].append(
                error_item
            )

            result["errors"].append(
                {
                    "stage": "standings",
                    **error_item,
                }
            )

        except Exception as exc:
            logger.exception(
                (
                    "Standing sync failed for "
                    "competition=%s"
                ),
                code,
            )

            result["status"] = "partial_success"
            result["standings"]["failed"] += 1

            error_item = {
                "competition": code,
                "name": competition[
                    "canonical_name"
                ],
                "error_type": type(exc).__name__,
                **safe_failure(exc),
            }

            result["standings"]["errors"].append(
                error_item
            )

            result["errors"].append(
                {
                    "stage": "standings",
                    **error_item,
                }
            )

    # ------------------------------------------------------------------
    # Stage 5: Evaluate finished predictions
    # ------------------------------------------------------------------

    try:
        async with pool.connection() as connection:
            result["evaluation"] = (
                await PredictionEvaluationService.run(
                    connection,
                    limit=evaluation_limit,
                )
            )

    except Exception as exc:
        logger.exception(
            "Prediction evaluation failed"
        )

        register_error(
            stage="evaluation",
            exc=exc,
        )

        result["evaluation"] = {
            "status": "failed",
            "error_type": type(exc).__name__,
            **safe_failure(exc),
        }

    # ------------------------------------------------------------------
    # Stage 6: Build snapshots and predict scheduled fixtures
    # ------------------------------------------------------------------

    try:
        async with pool.connection() as connection:
            result["predictions"] = (
                await ScheduledPredictionService.run(
                    connection,
                    kickoff_from=None,
                    kickoff_to=None,
                    days_ahead=fixture_days,
                    competition_id=None,
                    season_id=None,
                    limit=prediction_limit,
                    window_size=window_size,
                    calculation_version=(
                        calculation_version
                    ),
                )
            )

    except Exception as exc:
        logger.exception(
            "Scheduled prediction stage failed"
        )

        register_error(
            stage="predictions",
            exc=exc,
        )

        result["predictions"] = {
            "status": "failed",
            "error_type": type(exc).__name__,
            **safe_failure(exc),
        }

    # ------------------------------------------------------------------
    # Final status
    # ------------------------------------------------------------------

    result["duration_seconds"] = round(
        time.perf_counter() - started_at,
        3,
    )

    logger.info(
        (
            "Sync pipeline completed with status=%s "
            "duration_seconds=%s"
        ),
        result["status"],
        result["duration_seconds"],
    )

    return result
