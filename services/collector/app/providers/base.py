from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    code: str

    @abstractmethod
    def fetch(
        self,
        endpoint: str,
        params: dict[str, str],
        api_key: str,
    ) -> tuple[int, dict[str, Any]]:
        raise NotImplementedError
