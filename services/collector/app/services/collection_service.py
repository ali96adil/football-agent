from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from app.db.connection import pool
from app.providers import provider_manager


class CollectionService:
    async def collect(
        self,
        *,
        provider: str,
        endpoint: str,
        params: dict[str, Any],
        api_key: str,
        collector: str,
        ttl: timedelta,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
                provider=provider,
                endpoint=endpoint,
                params=params,
                api_key=api_key,
            )
        except RuntimeError as exc:
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
            if isinstance(payload, dict):
                error_message = (
                    payload.get("message")
                    or payload.get("error")
                )

            if not error_message:
                error_message = (
                    f"{provider} returned HTTP {response_status}"
                )

        async with pool.connection() as connection:

            source_result = await connection.execute(
                """
                SELECT id, enabled
                FROM core.data_sources
                WHERE code=%s
                LIMIT 1
                """,
                (provider,),
            )

            source = await source_result.fetchone()

            if not source:
                raise HTTPException(
                    status_code=500,
                    detail=f"{provider} source is missing",
                )

            if not source["enabled"]:
                raise HTTPException(
                    status_code=409,
                    detail=f"{provider} source is disabled",
                )

            expires_at = datetime.now(
                timezone.utc
            ) + ttl

            insert_result = await connection.execute(
                """
                INSERT INTO raw.api_payloads(
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
                VALUES(
                    %s,
                    %s,
                    %s,
                    NOW(),
                    %s,
                    %s::jsonb,
                    %s,
                    %s,
                    %s,
                    %s::jsonb
                )
                RETURNING *
                """,
                (
                    source["id"],
                    endpoint,
                    request_key,
                    response_status,
                    payload_json,
                    payload_hash,
                    expires_at,
                    error_message,
                    json.dumps(
                        {
                            "provider": provider,
                            "collector": collector,
                            "collected_at": datetime.now(
                                timezone.utc
                            ).isoformat(),
                            **(metadata or {}),
                        },
                        ensure_ascii=False,
                    ),
                ),
            )

            stored_payload = await insert_result.fetchone()

            if response_status < 400:
                await connection.execute(
                    """
                    UPDATE core.data_sources
                    SET
                        requests_used_today =
                            COALESCE(requests_used_today,0)+1,
                        last_success_at = NOW(),
                        updated_at = NOW()
                    WHERE id=%s
                    """,
                    (source["id"],),
                )
            else:
                await connection.execute(
                    """
                    UPDATE core.data_sources
                    SET
                        requests_used_today =
                            COALESCE(requests_used_today,0)+1,
                        last_failure_at = NOW(),
                        updated_at = NOW()
                    WHERE id=%s
                    """,
                    (source["id"],),
                )

        return {
            "response_status": response_status,
            "payload": payload,
            "raw_payload": stored_payload,
            "error_message": error_message,
        }


collection_service = CollectionService()