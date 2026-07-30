from __future__ import annotations

import asyncio
from typing import Any

from app.providers import get_provider


class ProviderManager:
    """Unified interface for calling external data providers."""

    async def fetch(
        self,
        *,
        provider: str,
        endpoint: str,
        params: dict[str, Any] | None,
        api_key: str,
    ) -> tuple[int, dict[str, Any]]:
        provider_instance = get_provider(provider)

        response_status, payload = await asyncio.to_thread(
            provider_instance.fetch,
            endpoint,
            params,
            api_key,
        )

        return response_status, payload


provider_manager = ProviderManager()