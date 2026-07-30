import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from app.db.connection import pool
from app.repositories.entities import upsert_competition, upsert_season
from app.providers import provider_manager


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

    request_key_source = json.dumps(
        {
            "endpoint": endpoint,
            "params": params,
        },
        sort_keys=True,
        separators=(",", ":"),
    )

    request_key = hashlib.sha256(
        request_key_source.encode("utf-8")
    ).hexdigest()

    try:
        response_status, payload = await provider_manager.fetch(
            provider="football_data",
            endpoint=endpoint,
            params=params,
            api_key=api_key,
        )
    except RuntimeError as exc:
        logger.exception("Football-data competitions request failed")

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    payload_json = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    payload_hash = hashlib.sha256(
        payload_json.encode("utf-8")
    ).hexdigest()

    error_message = None

    if response_status >= 400:
        error_message = (
            payload.get("message")
            or payload.get("error")
            or f"football-data.org returned HTTP {response_status}"
        )

    try:
        async with pool.connection() as connection:
            source_result = await connection.execute(
                """
                SELECT id, enabled
                FROM core.data_sources
                WHERE code = %s
                LIMIT 1
                """,
                ("football_data",),
            )

            source = await source_result.fetchone()

            if not source:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "football_data source is missing "
                        "from core.data_sources"
                    ),
                )

            if not source["enabled"]:
                raise HTTPException(
                    status_code=409,
                    detail="football_data source is disabled",
                )

            raw_result = await connection.execute(
                """
                INSERT INTO raw.api_payloads (
                    source_id,
                    endpoint,
                    request_key,
                    requested_at,
                    response_status,
                    payload,
                    payload_hash,
                    expires_at,
                    error_message,
                    metadata
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    NOW(),
                    %s,
                    %s::jsonb,
                    %s,
                    NOW() + INTERVAL '7 days',
                    %s,
                    %s::jsonb
                )
                RETURNING id
                """,
                (
                    source["id"],
                    endpoint,
                    request_key,
                    response_status,
                    payload_json,
                    payload_hash,
                    error_message,
                    json.dumps(
                        {
                            "provider": "football-data.org",
                            "collector": "competitions",
                            "collected_at": datetime.now(
                                timezone.utc
                            ).isoformat(),
                        },
                        ensure_ascii=False,
                    ),
                ),
            )

            stored_payload = await raw_result.fetchone()

            if response_status >= 400:
                await connection.execute(
                    """
                    UPDATE core.data_sources
                    SET
                        requests_used_today =
                            COALESCE(requests_used_today, 0) + 1,
                        last_failure_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (source["id"],),
                )

                raise HTTPException(
                    status_code=response_status,
                    detail={
                        "message": error_message,
                        "raw_payload_id": stored_payload["id"],
                        "provider_response": payload,
                    },
                )

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

            await connection.execute(
                """
                UPDATE core.data_sources
                SET
                    requests_used_today =
                        COALESCE(requests_used_today, 0) + 1,
                    last_success_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (source["id"],),
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