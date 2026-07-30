import logging

import json
import os
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db.connection import pool
from app.normalizers.standings import normalize_standings
from app.repositories.entities import (
    upsert_competition,
    upsert_season,
    upsert_team,
)
from app.repositories.standings import (
    insert_standing_row,
    insert_standing_snapshot,
)
from app.services import collection_service


router = APIRouter(
    prefix="",
    tags=["Football-Data Standings"],
)

logger = logging.getLogger(
    "football-collector.standings"
)

@router.post("/collect/football-data/standings")
async def collect_football_data_standings(
    competition: str = Query(
        ...,
        description="Competition code, for example PL, PD, BL1",
        min_length=2,
        max_length=20,
    ),
) -> dict[str, Any]:
    competition_code = competition.strip().upper()

    endpoint = (
        "https://api.football-data.org/v4/"
        f"competitions/{competition_code}/standings"
    )



    api_key = os.getenv(
        "FOOTBALL_DATA_API_KEY",
        "",
    ).strip()

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="FOOTBALL_DATA_API_KEY is not configured",
        )
 

    collection_result = await collection_service.collect(
        provider="football_data",
        endpoint=endpoint,
        params={},
        api_key=api_key,
        collector="standings",
        ttl=timedelta(hours=6),
        metadata={
            "provider": "football-data.org",
            "competition": competition_code,
        },
    )

    response_status = collection_result["response_status"]
    payload = collection_result["payload"]
    raw_payload = collection_result["raw_payload"]
    error_message = collection_result["error_message"]
    


    if response_status >= 400:
        raise HTTPException(
            status_code=response_status,
            detail={
                "message": error_message,
                "raw_payload_id": raw_payload["id"],
                "provider_response": payload,
            },
        )

    standings_count = 0

    if isinstance(payload, dict):
        standings = payload.get("standings", [])

        if isinstance(standings, list):
            standings_count = len(standings)

    return {
        "status": "success",
        "provider": "football-data.org",
        "operation": "collect_standings",
        "competition": competition_code,
        "standings_received": standings_count,
        "raw_payload": raw_payload,
    }

@router.post(
    "/normalize/football-data/standings/{payload_id}"
)
async def normalize_football_data_standings(
    payload_id: int,
) -> dict[str, Any]:

    async with pool.connection() as connection:
        async with connection.transaction():

            payload_result = await connection.execute(
                """
                SELECT
                    id,
                    source_id,
                    response_status,
                    payload
                FROM raw.api_payloads
                WHERE id = %s
                LIMIT 1
                """,
                (payload_id,),
            )

            stored_payload = await payload_result.fetchone()

            if stored_payload is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Payload {payload_id} not found",
                )

            if stored_payload["response_status"] >= 400:
                raise HTTPException(
                    status_code=409,
                    detail="Cannot normalize failed payload",
                )

            payload = stored_payload["payload"]

            if isinstance(payload, str):
                payload = json.loads(payload)

            normalized = normalize_standings(payload)

            snapshot = normalized["snapshot"]
            rows = normalized["rows"]
            competition_data = snapshot["competition"]
            season_data = snapshot["season"]

            competition_code = (
                competition_data.get("code") or ""
            ).strip().upper()

            if not competition_code:
                raise HTTPException(
                    status_code=422,
                    detail="Competition code is missing",
                )

            standing_type = (
                snapshot.get("standing_type") or "TOTAL"
            ).strip().upper()

            existing_result = await connection.execute(
                """
                SELECT id
                FROM core.standing_snapshots
                WHERE raw_payload_id = %s
                  AND standing_type = %s
                LIMIT 1
                """,
                (
                    payload_id,
                    standing_type,
                ),
            )

            existing_snapshot = await existing_result.fetchone()

            if existing_snapshot is not None:
                count_result = await connection.execute(
                    """
                    SELECT COUNT(*) AS row_count
                    FROM core.standing_rows
                    WHERE snapshot_id = %s
                    """,
                    (existing_snapshot["id"],),
                )

                count_row = await count_result.fetchone()

                return {
                    "status": "already_normalized",
                    "provider": "football-data.org",
                    "raw_payload_id": payload_id,
                    "snapshot_id": str(
                        existing_snapshot["id"]
                    ),
                    "rows": count_row["row_count"],
                }

            area_data = (
                payload.get("area")
                or competition_data.get("area")
                or {}
            )

            competition_id = await upsert_competition(
                connection,
                competition_data,
                area_data,
            )

            season_id = await upsert_season(
                connection,
                competition_id,
                season_data,
            )

            snapshot_id = await insert_standing_snapshot(
                connection=connection,
                competition_id=competition_id,
                season_id=season_id,
                source_id=stored_payload["source_id"],
                raw_payload_id=payload_id,
                competition_code=competition_code,
                standing_type=standing_type,
                metadata={
                    "provider": "football-data.org",
                    "stage": snapshot.get("stage"),
                    "group": snapshot.get("group"),
                },
            )
            country_code = (
                area_data.get("code")
                if isinstance(area_data, dict)
                else None
            )

            inserted_rows = 0

            for standing_row in rows:
                team_data = standing_row["team"]

                team_id = await upsert_team(
                    connection=connection,
                    source_id=stored_payload["source_id"],
                    team_data=team_data,
                    country_code=country_code,
                )

                await insert_standing_row(
                    connection=connection,
                    snapshot_id=snapshot_id,
                    team_id=team_id,
                    row=standing_row,
                )

                inserted_rows += 1

    return {
        "status": "success",
        "provider": "football-data.org",
        "operation": "normalize_standings",
        "raw_payload_id": payload_id,
        "competition": competition_code,
        "competition_id": competition_id,
        "season_id": season_id,
        "snapshot_id": snapshot_id,
        "standing_type": standing_type,
        "rows_inserted": inserted_rows,
    }

@router.post("/sync/football-data/standings")
async def sync_football_data_standings(
    competition: str = Query(
        ...,
        description="Competition code, for example PL, PD, BL1",
        min_length=2,
        max_length=20,
    ),
) -> dict[str, Any]:
    competition_code = competition.strip().upper()

    collection_result = await collect_football_data_standings(
        competition=competition_code,
    )

    raw_payload = collection_result.get("raw_payload")

    if isinstance(raw_payload, int):
        payload_id = raw_payload
    elif isinstance(raw_payload, dict):
        payload_id = (
            raw_payload.get("id")
            or raw_payload.get("payload_id")
            or raw_payload.get("raw_payload_id")
        )
    else:
        payload_id = None

    if payload_id is None:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Collection succeeded but payload ID was not returned",
                "collection_result": collection_result,
            },
        )

    normalization_result = await normalize_football_data_standings(
        payload_id=int(payload_id),
    )

    return {
        "status": "success",
        "provider": "football-data.org",
        "operation": "sync_standings",
        "competition": competition_code,
        "raw_payload_id": int(payload_id),
        "collection": collection_result,
        "normalization": normalization_result,
    }