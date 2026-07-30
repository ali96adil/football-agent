import hashlib
import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db.connection import pool
from app.normalizers.fixtures import normalize_fixture
from app.providers import provider_manager
from app.services import collection_service


router = APIRouter(
    prefix="",
    tags=["Football-Data Fixtures"],
)

logger = logging.getLogger("football-collector.fixtures")


def validate_iso_date(value: str, field_name: str) -> str:
    try:
        date.fromisoformat(value)
        return value
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} must use YYYY-MM-DD format",
        ) from exc


@router.post("/collect/football-data/fixtures")
async def collect_football_data_fixtures(
    date_from: str | None = Query(
        default=None,
        description="Start date using YYYY-MM-DD",
        examples=["2026-07-29"],
    ),
    date_to: str | None = Query(
        default=None,
        description="End date using YYYY-MM-DD",
        examples=["2026-08-05"],
    ),
    competitions: str | None = Query(
        default=None,
        description="Competition codes separated by commas, for example PL,PD,SA",
        examples=["PL"],
    ),
) -> dict[str, Any]:
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="FOOTBALL_DATA_API_KEY is not configured",
        )

    params: dict[str, str] = {}

    if date_from:
        params["dateFrom"] = validate_iso_date(date_from, "date_from")

    if date_to:
        params["dateTo"] = validate_iso_date(date_to, "date_to")

    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=422,
            detail="date_from cannot be later than date_to",
        )

    if competitions:
        params["competitions"] = competitions.strip().upper()

    endpoint = "https://api.football-data.org/v4/matches"

    collection_result = await collection_service.collect(
        provider="football_data",
        endpoint=endpoint,
        params=params,
        api_key=api_key,
        collector="fixtures",
        ttl=timedelta(hours=6),
        metadata={
            "provider": "football-data.org",
            "request_params": params,
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

    matches = payload.get("matches", [])

    return {
        "status": "success",
        "provider": "football-data.org",
        "operation": "fixtures",
        "matches_received": len(matches),
        "filters": params,
        "raw_payload": stored_payload,
    }


@router.post(
    "/normalize/football-data/fixtures/{payload_id}"
)
async def normalize_football_data_fixtures(
    payload_id: int,
) -> dict[str, Any]:
    try:
        async with pool.connection() as connection:
            payload_result = await connection.execute(
                """
                SELECT
                    p.id,
                    p.source_id,
                    p.response_status,
                    p.payload,
                    s.code AS source_code
                FROM raw.api_payloads p
                JOIN core.data_sources s
                  ON s.id = p.source_id
                WHERE p.id = %s
                LIMIT 1
                """,
                (payload_id,),
            )

            raw_payload = await payload_result.fetchone()

            if not raw_payload:
                raise HTTPException(
                    status_code=404,
                    detail="Raw payload not found",
                )

            if raw_payload["source_code"] != "football_data":
                raise HTTPException(
                    status_code=409,
                    detail="Payload does not belong to football_data",
                )

            if raw_payload["response_status"] != 200:
                raise HTTPException(
                    status_code=409,
                    detail="Only successful payloads can be normalized",
                )

            payload = raw_payload["payload"] or {}
            matches = payload.get("matches", [])

            if not isinstance(matches, list):
                raise HTTPException(
                    status_code=422,
                    detail="Payload matches field is not a list",
                )

            normalized_fixture_ids: list[str] = []
            failed_matches: list[dict[str, Any]] = []

            for match in matches:
                try:
                    fixture_id = await normalize_fixture(
                        connection,
                        raw_payload["source_id"],
                        payload_id,
                        match,
                    )

                    normalized_fixture_ids.append(fixture_id)

                except Exception as exc:
                    logger.exception(
                        "Unable to normalize match %s",
                        match.get("id"),
                    )

                    failed_matches.append(
                        {
                            "external_fixture_id": match.get("id"),
                            "error": str(exc),
                        }
                    )

            if failed_matches:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "message": "Some fixtures failed to normalize",
                        "normalized_count": len(
                            normalized_fixture_ids
                        ),
                        "failed_count": len(failed_matches),
                        "failures": failed_matches,
                    },
                )

        return {
            "status": "success",
            "provider": "football-data.org",
            "raw_payload_id": payload_id,
            "matches_received": len(matches),
            "fixtures_normalized": len(
                normalized_fixture_ids
            ),
            "fixture_ids": normalized_fixture_ids,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Unable to normalize football-data fixtures"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to normalize football-data fixtures",
        ) from exc


@router.post("/sync/football-data/fixtures")
async def sync_football_data_fixtures(
    date_from: str | None = Query(
        default=None,
        description="Start date using YYYY-MM-DD",
        examples=["2026-07-29"],
    ),
    date_to: str | None = Query(
        default=None,
        description="End date using YYYY-MM-DD",
        examples=["2026-08-05"],
    ),
    competitions: str | None = Query(
        default=None,
        description="Competition codes separated by commas",
        examples=["PL"],
    ),
) -> dict[str, Any]:
    collection_result = await collect_football_data_fixtures(
        date_from=date_from,
        date_to=date_to,
        competitions=competitions,
    )

    raw_payload = collection_result.get("raw_payload") or {}
    payload_id = raw_payload.get("id")

    if payload_id is None:
        raise HTTPException(
            status_code=500,
            detail="Collection succeeded but raw payload ID is missing",
        )

    normalization_result = (
        await normalize_football_data_fixtures(
            payload_id=int(payload_id),
        )
    )

    return {
        "status": "success",
        "provider": "football-data.org",
        "operation": "sync_fixtures",
        "filters": collection_result.get("filters", {}),
        "collection": {
            "matches_received": collection_result.get(
                "matches_received",
                0,
            ),
            "raw_payload": raw_payload,
        },
        "normalization": {
            "raw_payload_id": normalization_result.get(
                "raw_payload_id"
            ),
            "matches_received": normalization_result.get(
                "matches_received",
                0,
            ),
            "fixtures_normalized": normalization_result.get(
                "fixtures_normalized",
                0,
            ),
            "fixture_ids": normalization_result.get(
                "fixture_ids",
                [],
            ),
        },
    }


@router.post("/collect/api-football/fixtures")
async def collect_api_football_fixtures(
    league: int = Query(
        ...,
        ge=1,
        description="API-Football league ID",
        examples=[39],
    ),
    season: int = Query(
        ...,
        ge=2000,
        le=2100,
        description="Season start year",
        examples=[2026],
    ),
    date_from: str | None = Query(
        default=None,
        description="Start date using YYYY-MM-DD",
        examples=["2026-08-21"],
    ),
    date_to: str | None = Query(
        default=None,
        description="End date using YYYY-MM-DD",
        examples=["2026-08-30"],
    ),
) -> dict[str, Any]:
    params: dict[str, str | int] = {
        "league": league,
        "season": season,
    }

    if date_from:
        params["from"] = validate_iso_date(
            date_from,
            "date_from",
        )

    if date_to:
        params["to"] = validate_iso_date(
            date_to,
            "date_to",
        )

    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=422,
            detail="date_from cannot be later than date_to",
        )

    collection_result = await collection_service.collect(
        provider="api_football",
        endpoint="/fixtures",
        params=params,
        collector="fixtures",
        ttl=timedelta(hours=6),
        metadata={
            "provider": "api-football",
            "league": league,
            "season": season,
            "request_params": params,
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

    provider_errors = payload.get("errors")

    if provider_errors:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "API-Football rejected the request",
                "raw_payload_id": stored_payload["id"],
                "provider_errors": provider_errors,
                "parameters": payload.get("parameters"),
            },
        )

    fixtures = payload.get("response", [])

    if not isinstance(fixtures, list):
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Invalid fixtures payload from API-Football"
                ),
                "raw_payload_id": stored_payload["id"],
            },
        )

    return {
        "status": "success",
        "provider": "api-football",
        "operation": "collect_fixtures",
        "league": league,
        "season": season,
        "fixtures_received": len(fixtures),
        "filters": params,
        "paging": payload.get("paging"),
        "results": payload.get("results"),
        "raw_payload": stored_payload,
    }
