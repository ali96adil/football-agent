import logging
import os
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from app.db.connection import pool
from app.repositories.entities import upsert_competition, upsert_season
from app.services import collection_service


router = APIRouter(
    prefix="",
    tags=["Football-Data Competitions"],
)

logger = logging.getLogger("football-collector.competitions")


@router.post("/sync/football-data/competitions")
async def sync_football_data_competitions() -> dict[str, Any]:
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="FOOTBALL_DATA_API_KEY is not configured",
        )

    endpoint = "https://api.football-data.org/v4/competitions"
    params: dict[str, str] = {}

    collection_result = await collection_service.collect(
        provider="football_data",
        endpoint=endpoint,
        params=params,
        api_key=api_key,
        collector="competitions",
        ttl=timedelta(days=7),
        metadata={
            "provider": "football-data.org",
        },
    )

    response_status = collection_result["response_status"]
    payload = collection_result["payload"]
    stored_payload = collection_result["raw_payload"]
    error_message = collection_result["error_message"]

    if response_status >= 400:
        raise HTTPException(
            status_code=response_status,
            detail={
                "message": error_message,
                "raw_payload_id": stored_payload["id"],
                "provider_response": payload,
            },
        )

    try:
        async with pool.connection() as connection:
            competitions = payload.get("competitions", [])

            if not isinstance(competitions, list):
                raise HTTPException(
                    status_code=502,
                    detail="Invalid competitions payload from provider",
                )

            competitions_synced = 0
            seasons_synced = 0
            skipped = 0
            errors: list[dict[str, Any]] = []

            for competition_data in competitions:
                try:
                    area_data = competition_data.get("area") or {}

                    competition_id = await upsert_competition(
                        connection,
                        competition_data,
                        area_data,
                    )

                    competitions_synced += 1

                    current_season = competition_data.get(
                        "currentSeason"
                    )

                    if current_season:
                        season_id = await upsert_season(
                            connection,
                            competition_id,
                            current_season,
                        )

                        if season_id:
                            seasons_synced += 1

                except Exception as exc:
                    skipped += 1

                    errors.append(
                        {
                            "football_data_id": competition_data.get("id"),
                            "code": competition_data.get("code"),
                            "name": competition_data.get("name"),
                            "error": str(exc),
                        }
                    )

                    logger.exception(
                        "Unable to sync competition: %s",
                        competition_data.get("name"),
                    )

        return {
            "status": "success",
            "provider": "football-data.org",
            "operation": "sync_competitions",
            "raw_payload_id": stored_payload["id"],
            "provider_count": payload.get("count"),
            "competitions_received": len(competitions),
            "competitions_synced": competitions_synced,
            "seasons_synced": seasons_synced,
            "skipped": skipped,
            "errors": errors,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Unable to synchronize competitions")

        raise HTTPException(
            status_code=500,
            detail="Unable to synchronize competitions",
        ) from exc