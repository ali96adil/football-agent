from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.domain.team_snapshot import TeamSnapshot
from app.repositories.fixtures_repository import (
    get_completed_fixtures_for_team,
)
from app.repositories.team_snapshots_repository import (
    save_snapshot,
)
from app.services.rating_engine import RatingEngine
from app.services.snapshot_builder import SnapshotBuilder
from app.services.statistics_engine import StatisticsEngine


class SnapshotService:
    """
    Complete Team Intelligence pipeline.

        Fixtures
            ↓
        StatisticsEngine
            ↓
        RatingEngine
            ↓
        SnapshotBuilder
            ↓
        TeamSnapshotsRepository
    """

    @classmethod
    async def build_and_save(
        cls,
        *,
        connection,
        team_id: UUID,
        competition_id: UUID,
        season_id: UUID,
        window_size: int = 10,
        cutoff_at: datetime | None = None,
    ) -> TeamSnapshot:

        fixtures = await get_completed_fixtures_for_team(
            connection,
            team_id=team_id,
            competition_id=competition_id,
            season_id=season_id,
            window_size=window_size,
            cutoff_at=cutoff_at,
        )

        statistics = StatisticsEngine.calculate(
            team_id=team_id,
            fixtures=fixtures,
            window_size=window_size,
        )

        ratings = RatingEngine.calculate(
            statistics,
        )

        snapshot = SnapshotBuilder.build(
            team_id=team_id,
            competition_id=competition_id,
            season_id=season_id,
            statistics=statistics,
            ratings=ratings,
            data_cutoff_at=cutoff_at,
        )

        return await save_snapshot(
            connection,
            snapshot=snapshot,
        )