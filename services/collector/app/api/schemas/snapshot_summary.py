from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class SnapshotSummaryResponse(BaseModel):
    team_id: UUID
    competition_id: UUID
    season_id: UUID

    matches_played: int

    overall_rating: Decimal | None
    attack_rating: Decimal | None
    defence_rating: Decimal | None
    form_rating: Decimal | None

    form_sequence: str
    data_completeness: Decimal

    model_config = {
        "from_attributes": True,
    }