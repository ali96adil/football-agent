from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SnapshotBuildRequest(BaseModel):
    team_id: UUID
    competition_id: UUID
    season_id: UUID

    window_size: int = Field(default=10, ge=1, le=100)
    cutoff_at: datetime | None = None