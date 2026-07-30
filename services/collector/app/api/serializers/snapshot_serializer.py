from app.api.schemas.snapshot_full import SnapshotFullResponse
from app.api.schemas.snapshot_summary import SnapshotSummaryResponse
from app.domain.team_snapshot import TeamSnapshot


class SnapshotSerializer:
    @staticmethod
    def summary(
        snapshot: TeamSnapshot,
    ) -> SnapshotSummaryResponse:
        return SnapshotSummaryResponse.model_validate(snapshot)

    @staticmethod
    def full(
        snapshot: TeamSnapshot,
    ) -> SnapshotFullResponse:
        return SnapshotFullResponse.model_validate(snapshot)