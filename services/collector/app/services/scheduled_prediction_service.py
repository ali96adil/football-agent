from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.prediction.persistence_service import (
    PredictionPersistenceService,
)
from app.repositories.fixtures_repository import (
    get_scheduled_fixtures,
)
from app.services.snapshot_service import SnapshotService


logger = logging.getLogger(__name__)


class ScheduledPredictionService:
    """
    Generate predictions for scheduled fixtures.

    Pipeline for every fixture:

        scheduled fixture
            -> build home snapshot at kickoff cutoff
            -> build away snapshot at kickoff cutoff
            -> create prediction
            -> persist prediction

    Failures are isolated per fixture so the rest of the batch continues.
    """

    DEFAULT_DAYS_AHEAD = 3
    DEFAULT_WINDOW_SIZE = 10
    DEFAULT_LIMIT = 200

    @classmethod
    async def run(
        cls,
        connection: Any,
        *,
        kickoff_from: datetime | None = None,
        kickoff_to: datetime | None = None,
        days_ahead: int = DEFAULT_DAYS_AHEAD,
        window_size: int = DEFAULT_WINDOW_SIZE,
        limit: int = DEFAULT_LIMIT,
        competition_id: UUID | None = None,
        season_id: UUID | None = None,
        calculation_version: str | None = None,
    ) -> dict[str, Any]:
        cls._validate_arguments(
            kickoff_from=kickoff_from,
            kickoff_to=kickoff_to,
            days_ahead=days_ahead,
            window_size=window_size,
            limit=limit,
            calculation_version=calculation_version,
        )

        now = datetime.now(timezone.utc)

        effective_from = kickoff_from or now
        effective_to = kickoff_to or (
            effective_from + timedelta(days=days_ahead)
        )

        fixtures = await get_scheduled_fixtures(
            connection,
            kickoff_from=effective_from,
            kickoff_to=effective_to,
            competition_id=competition_id,
            season_id=season_id,
            limit=limit,
        )

        saved = 0
        skipped = 0
        failed = 0

        items: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for fixture in fixtures:
            try:
                item = await cls._predict_fixture(
                    connection,
                    fixture=fixture,
                    window_size=window_size,
                    calculation_version=calculation_version,
                )

                items.append(item)

                if item["status"] == "saved":
                    saved += 1
                else:
                    skipped += 1

            except Exception as error:
                failed += 1

                error_item = {
                    "fixture_id": str(fixture.fixture_id),
                    "competition_id": str(
                        fixture.competition_id
                    ),
                    "season_id": str(fixture.season_id),
                    "home_team_id": str(
                        fixture.home_team_id
                    ),
                    "away_team_id": str(
                        fixture.away_team_id
                    ),
                    "kickoff_at": (
                        fixture.kickoff_at.isoformat()
                    ),
                    "error_type": type(error).__name__,
                    "message": str(error),
                }

                errors.append(error_item)

                items.append(
                    {
                        "fixture_id": str(
                            fixture.fixture_id
                        ),
                        "status": "failed",
                        "reason": (
                            f"{type(error).__name__}: "
                            f"{error}"
                        ),
                    }
                )

                logger.exception(
                    "Scheduled prediction failed: "
                    "fixture_id=%s",
                    fixture.fixture_id,
                )

        status = cls._determine_status(
            total=len(fixtures),
            saved=saved,
            failed=failed,
        )

        return {
            "status": status,
            "kickoff_from": effective_from.isoformat(),
            "kickoff_to": effective_to.isoformat(),
            "fixtures_found": len(fixtures),
            "saved": saved,
            "skipped": skipped,
            "failed": failed,
            "items": items,
            "errors": errors,
        }

    @classmethod
    async def generate(
        cls,
        connection: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Compatibility alias for callers using generate().
        """

        return await cls.run(
            connection,
            **kwargs,
        )

    @classmethod
    async def _predict_fixture(
        cls,
        connection: Any,
        *,
        fixture: Any,
        window_size: int,
        calculation_version: str | None,
    ) -> dict[str, Any]:
        """
        Build fixture-safe snapshots and persist one prediction.

        The snapshot cutoff is the fixture kickoff time. This prevents
        future matches from leaking into historical feature data.
        """

        home_snapshot = await SnapshotService.build_and_save(
            connection=connection,
            team_id=fixture.home_team_id,
            competition_id=fixture.competition_id,
            season_id=fixture.season_id,
            window_size=window_size,
            cutoff_at=fixture.kickoff_at,
        )

        away_snapshot = await SnapshotService.build_and_save(
            connection=connection,
            team_id=fixture.away_team_id,
            competition_id=fixture.competition_id,
            season_id=fixture.season_id,
            window_size=window_size,
            cutoff_at=fixture.kickoff_at,
        )

        if home_snapshot.id is None:
            raise RuntimeError(
                "Saved home snapshot has no id."
            )

        if away_snapshot.id is None:
            raise RuntimeError(
                "Saved away snapshot has no id."
            )

        metadata: dict[str, Any] = {
            "source": "scheduled_prediction_service",
            "fixture_status": fixture.fixture_status,
            "window_size": window_size,
            "snapshot_cutoff_at": (
                fixture.kickoff_at.isoformat()
            ),
            "home_snapshot_hash": (
                home_snapshot.snapshot_hash
            ),
            "away_snapshot_hash": (
                away_snapshot.snapshot_hash
            ),
        }

        if calculation_version is not None:
            metadata["calculation_version"] = (
                calculation_version
            )

        prediction = await (
            PredictionPersistenceService.predict_and_save(
                connection,
                home_snapshot=home_snapshot,
                away_snapshot=away_snapshot,
                fixture_id=fixture.fixture_id,
                kickoff_at=fixture.kickoff_at,
                metadata=metadata,
            )
        )

        if prediction.id is None:
            raise RuntimeError(
                "Saved prediction has no id."
            )

        return {
            "fixture_id": str(fixture.fixture_id),
            "prediction_id": str(prediction.id),
            "home_snapshot_id": str(
                home_snapshot.id
            ),
            "away_snapshot_id": str(
                away_snapshot.id
            ),
            "status": "saved",
        }

    @staticmethod
    def _validate_arguments(
        *,
        kickoff_from: datetime | None,
        kickoff_to: datetime | None,
        days_ahead: int,
        window_size: int,
        limit: int,
        calculation_version: str | None,
    ) -> None:
        if days_ahead <= 0:
            raise ValueError(
                "days_ahead must be greater than zero."
            )

        if window_size <= 0:
            raise ValueError(
                "window_size must be greater than zero."
            )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        for field_name, value in (
            ("kickoff_from", kickoff_from),
            ("kickoff_to", kickoff_to),
        ):
            if value is not None and value.tzinfo is None:
                raise ValueError(
                    f"{field_name} must be timezone-aware."
                )

        if (
            kickoff_from is not None
            and kickoff_to is not None
            and kickoff_to < kickoff_from
        ):
            raise ValueError(
                "kickoff_to cannot be earlier than "
                "kickoff_from."
            )

        if (
            calculation_version is not None
            and not calculation_version.strip()
        ):
            raise ValueError(
                "calculation_version must not be empty."
            )

    @staticmethod
    def _determine_status(
        *,
        total: int,
        saved: int,
        failed: int,
    ) -> str:
        if total == 0:
            return "success"

        if failed == 0:
            return "success"

        if saved > 0:
            return "partial_success"

        return "failed"
