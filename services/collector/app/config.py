from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderSettings:
    code: str
    base_url: str
    api_key: str


def build_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return database_url

    host = os.getenv("APP_DB_HOST", "postgres")
    port = os.getenv("APP_DB_PORT", "5432")
    database = os.getenv("APP_DB_NAME")
    user = os.getenv("APP_DB_USER")
    password = os.getenv("APP_DB_PASSWORD")

    missing = [
        name
        for name, value in {
            "APP_DB_NAME": database,
            "APP_DB_USER": user,
            "APP_DB_PASSWORD": password,
        }.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Missing required database variables: "
            + ", ".join(missing)
        )

    return (
        f"postgresql://"
        f"{user}:{password}@{host}:{port}/{database}"
    )


def get_provider_settings(provider: str) -> ProviderSettings:
    normalized_provider = (
        provider.strip().lower().replace("-", "_")
    )

    providers = {
        "football_data": {
            "base_url": os.getenv(
                "FOOTBALL_DATA_BASE_URL",
                "https://api.football-data.org/v4",
            ),
            "api_key": os.getenv("FOOTBALL_DATA_API_KEY", ""),
        },
        "api_football": {
            "base_url": os.getenv(
                "API_FOOTBALL_BASE_URL",
                "https://v3.football.api-sports.io",
            ),
            "api_key": os.getenv("API_FOOTBALL_KEY", ""),
        },
    }

    try:
        values = providers[normalized_provider]
    except KeyError as exc:
        available = ", ".join(sorted(providers))

        raise RuntimeError(
            f"Unknown provider configuration '{provider}'. "
            f"Available providers: {available}"
        ) from exc

    api_key = values["api_key"].strip()

    if not api_key:
        raise RuntimeError(
            f"API key is missing for provider "
            f"'{normalized_provider}'"
        )

    return ProviderSettings(
        code=normalized_provider,
        base_url=values["base_url"].rstrip("/"),
        api_key=api_key,
    )


def build_provider_endpoint(
    provider: str,
    endpoint: str,
) -> str:
    settings = get_provider_settings(provider)

    if endpoint.startswith(("http://", "https://")):
        return endpoint

    return (
        f"{settings.base_url}/"
        f"{endpoint.lstrip('/')}"
    )
