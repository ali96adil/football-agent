from fastapi import APIRouter, HTTPException

from app.api.schemas.prediction_response import (
    PredictionResponse,
)
from app.services.prediction_service import prediction_service


router = APIRouter(
    prefix="/api/v1/predictions",
    tags=["Predictions"],
)


@router.get(
    "",
    response_model=list[PredictionResponse],
)
async def get_predictions(
    limit: int = 50,
    offset: int = 0,
    view: str = "upcoming",
):
    return await prediction_service.get_predictions(
        limit=limit,
        offset=offset,
        view=view,
    )


@router.get(
    "/{fixture_id}",
    response_model=PredictionResponse,
)
async def get_prediction(
    fixture_id: str,
):
    prediction = await prediction_service.get_prediction(
        fixture_id,
    )

    if prediction is None:
        raise HTTPException(
            status_code=404,
            detail="Prediction not found",
        )

    return prediction