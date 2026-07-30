from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


PREDICTION_RUN_SAVED = "saved"
PREDICTION_RUN_SKIPPED = "skipped"
PREDICTION_RUN_FAILED = "failed"

VALID_PREDICTION_RUN_STATUSES = {
    PREDICTION_RUN_SAVED,
    PREDICTION_RUN_SKIPPED,
    PREDICTION_RUN_FAILED,
}


@dataclass(frozen=True, slots=True)
class PredictionRunItem:
    fixture_id: UUID
    status: str
    prediction_id: UUID | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in VALID_PREDICTION_RUN_STATUSES:
            raise ValueError(
                f"Unsupported prediction run status: "
                f"{self.status}"
            )

        if (
            self.status == PREDICTION_RUN_SAVED
            and self.prediction_id is None
        ):
            raise ValueError(
                "prediction_id is required when status "
                "is saved."
            )


@dataclass(frozen=True, slots=True)
class PredictionRunReport:
    total_fixtures: int
    saved: int
    skipped: int
    failed: int
    items: tuple[PredictionRunItem, ...]

    def __post_init__(self) -> None:
        if min(
            self.total_fixtures,
            self.saved,
            self.skipped,
            self.failed,
        ) < 0:
            raise ValueError(
                "Prediction run counters cannot be negative."
            )

        if len(self.items) != self.total_fixtures:
            raise ValueError(
                "items count must equal total_fixtures."
            )

        if (
            self.saved
            + self.skipped
            + self.failed
            != self.total_fixtures
        ):
            raise ValueError(
                "saved + skipped + failed must equal "
                "total_fixtures."
            )
