import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.providers.base import BaseProvider


class FootballDataProvider(BaseProvider):
    code = "football_data"

    def fetch(
        self,
        endpoint: str,
        params: dict[str, str],
        api_key: str,
    ) -> tuple[int, dict[str, Any]]:
        query_string = urlencode(params)
        url = endpoint

        if query_string:
            url = f"{endpoint}?{query_string}"

        request = Request(
            url=url,
            method="GET",
            headers={
                "X-Auth-Token": api_key,
                "Accept": "application/json",
                "User-Agent": "football-intelligence-collector/0.2.0",
            },
        )

        try:
            with urlopen(request, timeout=30) as response:
                response_body = response.read().decode("utf-8")
                response_status = response.status

            return response_status, json.loads(response_body)

        except HTTPError as exc:
            response_body = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            try:
                payload = json.loads(response_body)
            except json.JSONDecodeError:
                payload = {
                    "error": "Invalid JSON response",
                    "response_body": response_body,
                }

            return exc.code, payload

        except URLError as exc:
            raise RuntimeError(
                f"Unable to connect to football-data.org: {exc.reason}"
            ) from exc


football_data_provider = FootballDataProvider()


def fetch_football_data(
    endpoint: str,
    params: dict[str, str],
    api_key: str,
) -> tuple[int, dict[str, Any]]:
    return football_data_provider.fetch(
        endpoint=endpoint,
        params=params,
        api_key=api_key,
    )
