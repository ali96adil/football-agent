from __future__ import annotations

from typing import Any

import httpx

from app.providers.base import BaseProvider


class APIFootballProvider(BaseProvider):
    code = "api_football"

    def fetch(
        self,
        endpoint: str,
        params: dict[str, Any] | None,
        api_key: str,
    ) -> tuple[int, Any]:
        headers = {
            "x-apisports-key": api_key,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                endpoint,
                params=params or {},
                headers=headers,
            )

        try:
            payload = response.json()
        except ValueError:
            payload = {
                "message": "Provider returned a non-JSON response",
                "body": response.text,
            }

        return response.status_code, payload
        
api_football_provider = APIFootballProvider()