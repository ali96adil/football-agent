from __future__ import annotations

from typing import Any

from app.prediction.domain.prediction_fixture import (
    PredictionFixture,
)
from app.prediction.domain.prediction_run_report import (
    PREDICTION_RUN_FAILED,
    PREDICTION_RUN_SAVED,
    PREDICTION_RUN_SKIPPED,
    PredictionRunItem,
    PredictionRunReport,
)
from app.prediction.persistence_service import (
    PredictionPersistenceService,
)
from app.repositories.team_snapshots_repository import (
    get_latest_snapshot,
)


class PredictionRunner:
    """
    Coordinate batch prediction generation.

    One failed fixture does not stop the remaining fixtures.
    """

    @classmethod
    async def run(
        cls,
        connection: Any,
        *,
        fixtures: list[PredictionFixture],
        window_size: int = 10,
        calculation_version: str | None = None,
    ) -> PredictionRunReport:
        if window_size <= 0:
            raise ValueError(
                "window_size must be greater than zero."
            )

        items: list[PredictionRunItem] = []

        for fixture in fixtures:
            item = await cls._run_fixture(
                connection,
                fixture=fixture,
                window_size=window_size,
                calculation_version=calculation_version,
            )
            items.append(item)

        saved = sum(
            item.status == PREDICTION_RUN_SAVED
            for item in items
        )
        skipped = sum(
            item.status == PREDICTION_RUN_SKIPPED
            for item in items
        )
        failed = sum(
            item.status == PREDICTION_RUN_FAILED
            for item in items
        )

        return PredictionRunReport(
            total_fixtures=len(fixtures),
            saved=saved,
            skipped=skipped,
            failed=failed,
            items=tuple(items),
        )

    @classmethod
    async def _run_fixture(
        cls,
        connection: Any,
        *,
        fixture: PredictionFixture,
        window_size: int,
        calculation_version: str | None,
    ) -> PredictionRunItem:
        try:
            home_snapshot = await get_latest_snapshot(
                connection,
                team_id=fixture.home_team_id,
                competition_id=fixture.competition_id,
                season_id=fixture.season_id,
                window_size=window_size,
                calculation_version=calculation_version,
            )

            if home_snapshot is None:
                return PredictionRunItem(
                    fixture_id=fixture.fixture_id,
                    status=PREDICTION_RUN_SKIPPED,
                    reason="home_snapshot_not_found",
                )

            away_snapshot = await get_latest_snapshot(
                connection,
                team_id=fixture.away_team_id,
                competition_id=fixture.competition_id,
                season_id=fixture.season_id,
                window_size=window_size,
                calculation_version=calculation_version,
            )

            if away_snapshot is None:
                return PredictionRunItem(
                    fixture_id=fixture.fixture_id,
                    status=PREDICTION_RUN_SKIPPED,
                    reason="away_snapshot_not_found",
                )

            prediction = await (
                PredictionPersistenceService
                .predict_and_save(
                    connection,
                    home_snapshot=home_snapshot,
                    away_snapshot=away_snapshot,
                    fixture_id=fixture.fixture_id,
                    kickoff_at=fixture.kickoff_at,
                    metadata={
                        "source": "prediction_runner",
                        "fixture_status": (
                            fixture.fixture_status
                        ),
                        "window_size": window_size,
                    },
                )
            )

            if prediction.id is None:
                return PredictionRunItem(
                    fixture_id=fixture.fixture_id,
                    status=PREDICTION_RUN_FAILED,
                    reason=(
                        "saved_prediction_has_no_id"
                    ),
                )

            return PredictionRunItem(
                fixture_id=fixture.fixture_id,
                status=PREDICTION_RUN_SAVED,
                prediction_id=prediction.id,
            )

        except Exception as error:
            return PredictionRunItem(
                fixture_id=fixture.fixture_id,
                status=PREDICTION_RUN_FAILED,
                reason=(
                    f"{type(error).__name__}: {error}"
                ),
            )
