import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.schemas.snapshot_build import SnapshotBuildRequest
from app.api.schemas.snapshot_full import SnapshotFullResponse
from app.api.schemas.snapshot_summary import SnapshotSummaryResponse
from app.api.serializers.snapshot_serializer import SnapshotSerializer
from app.db.connection import pool
from app.repositories.team_snapshots_repository import (
    get_latest_snapshot,
    get_latest_snapshots_for_competition,
    get_snapshot_by_id,
)
from app.services.snapshot_service import SnapshotService


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/snapshots",
    tags=["Team Snapshots"],
)


@router.get(
    "/latest/{team_id}",
    response_model=SnapshotSummaryResponse,
)
async def get_latest_team_snapshot(
    team_id: UUID,
    competition_id: UUID = Query(...),
    season_id: UUID = Query(...),
    window_size: int = Query(default=10, ge=1, le=100),
) -> SnapshotSummaryResponse:
    async with pool.connection() as connection:
        snapshot = await get_latest_snapshot(
            connection,
            team_id=team_id,
            competition_id=competition_id,
            season_id=season_id,
            window_size=window_size,
        )

    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No snapshot found for the requested team, "
                "competition, season, and window size."
            ),
        )

    return SnapshotSerializer.summary(snapshot)


@router.get(
    "/competition/{competition_id}",
    response_model=list[SnapshotSummaryResponse],
)
async def get_competition_latest_snapshots(
    competition_id: UUID,
    season_id: UUID = Query(...),
    window_size: int = Query(default=10, ge=1, le=100),
    calculation_version: str | None = Query(default=None),
) -> list[SnapshotSummaryResponse]:
    """
    Return the latest snapshot for every team in a competition.

    Results are filtered by competition, season, window size,
    and optionally calculation version.
    """

    if calculation_version is not None:
        calculation_version = calculation_version.strip()

        if not calculation_version:
            raise HTTPException(
                status_code=422,
                detail="calculation_version must not be empty.",
            )

    async with pool.connection() as connection:
        snapshots = await get_latest_snapshots_for_competition(
            connection,
            competition_id=competition_id,
            season_id=season_id,
            window_size=window_size,
            calculation_version=calculation_version,
        )

    return [
        SnapshotSerializer.summary(snapshot)
        for snapshot in snapshots
    ]


@router.post(
    "/build",
    response_model=SnapshotFullResponse,
    status_code=201,
)
async def build_team_snapshot(
    request: SnapshotBuildRequest,
) -> SnapshotFullResponse:
    try:
        async with pool.connection() as connection:
            snapshot = await SnapshotService.build_and_save(
                connection=connection,
                team_id=request.team_id,
                competition_id=request.competition_id,
                season_id=request.season_id,
                window_size=request.window_size,
                cutoff_at=request.cutoff_at,
            )

        return SnapshotSerializer.full(snapshot)

    except Exception as exc:
        logger.exception(
            "Unable to build team snapshot",
            extra={
                "team_id": str(request.team_id),
                "competition_id": str(request.competition_id),
                "season_id": str(request.season_id),
                "window_size": request.window_size,
                "cutoff_at": (
                    request.cutoff_at.isoformat()
                    if request.cutoff_at is not None
                    else None
                ),
            },
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to build team snapshot.",
        ) from exc


@router.get(
    "/{snapshot_id}",
    response_model=SnapshotFullResponse,
)
async def get_team_snapshot(
    snapshot_id: UUID,
) -> SnapshotFullResponse:
    async with pool.connection() as connection:
        snapshot = await get_snapshot_by_id(
            connection,
            snapshot_id=snapshot_id,
        )

    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="Snapshot not found.",
        )

    return SnapshotSerializer.full(snapshot)