from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from app.config import get_provider_settings
from app.db.connection import pool
from app.providers import provider_manager


class CollectionService:
    async def collect(
        self,
        *,
        provider: str,
        endpoint: str,
        params: dict[str, Any],
        api_key: str | None = None,
        collector: str,
        ttl: timedelta,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with pool.connection() as connection:
            source_result = await connection.execute(
                """SELECT id, enabled, base_url, secret_ciphertext
                     FROM core.data_sources
                    WHERE provider=%s OR (provider IS NULL AND code=%s)
                    ORDER BY enabled DESC, priority DESC, id
                    LIMIT 1""",
                (provider, provider),
            )
            source = await source_result.fetchone()
            if not source:
                raise HTTPException(status_code=500, detail=f"{provider} source is missing")
            if not source["enabled"]:
                raise HTTPException(status_code=409, detail=f"{provider} source is disabled")
            stored_api_key = None
            if source["secret_ciphertext"] is not None:
                encryption_key = os.getenv("SOURCE_SECRET_ENCRYPTION_KEY", "")
                if len(encryption_key) < 32:
                    raise HTTPException(status_code=503, detail="source secret storage is not configured")
                decrypted = await connection.execute(
                    "SELECT pgp_sym_decrypt(%s,%s) AS value",
                    (source["secret_ciphertext"], encryption_key),
                )
                stored_api_key = (await decrypted.fetchone())["value"]

        provider_settings = None
        if not source["base_url"] or not (stored_api_key or api_key):
            provider_settings = get_provider_settings(provider)
        fallback_base_url = provider_settings.base_url if provider_settings else ""
        fallback_api_key = provider_settings.api_key if provider_settings else ""
        base_url = (source["base_url"] or fallback_base_url).rstrip("/")
        resolved_endpoint = endpoint if endpoint.startswith(("http://", "https://")) else f"{base_url}/{endpoint.lstrip('/')}"
        resolved_api_key = stored_api_key or api_key or fallback_api_key

        request_key_source = json.dumps(
            {
                "endpoint": resolved_endpoint,
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
                endpoint=resolved_endpoint,
                params=params,
                api_key=resolved_api_key,
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
                    resolved_endpoint,
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
