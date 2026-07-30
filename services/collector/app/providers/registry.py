from app.providers.api_football import api_football_provider
from app.providers.base import BaseProvider
from app.providers.football_data import football_data_provider


_PROVIDERS: dict[str, BaseProvider] = {
    football_data_provider.code: football_data_provider,
    api_football_provider.code: api_football_provider,
}


def get_provider(name: str) -> BaseProvider:
    normalized_name = name.strip().lower().replace("-", "_")

    try:
        return _PROVIDERS[normalized_name]
    except KeyError as exc:
        available = ", ".join(sorted(_PROVIDERS))

        raise ValueError(
            f"Unknown provider '{name}'. Available providers: {available}"
        ) from exc


def list_providers() -> tuple[str, ...]:
    return tuple(sorted(_PROVIDERS))