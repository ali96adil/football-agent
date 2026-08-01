from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class JobExecutionError(RuntimeError):
    def __init__(self, reason: str, *, stage: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.stage = stage


def safe_failure(exc: Exception) -> dict[str, Any]:
    """Return a stable, secret-free failure classification for jobs and UI."""
    if isinstance(exc, JobExecutionError):
        result: dict[str, Any] = {"reason": exc.reason}
        if exc.stage:
            result["stage"] = exc.stage
        return result
    status = exc.status_code if isinstance(exc, HTTPException) else None
    text = str(exc).lower()
    if status == 401 or status == 403:
        reason = "authentication_failure"
    elif status == 409 and "disabled" in text:
        reason = "source_disabled"
    elif status == 429:
        reason = "rate_limit"
    elif status is not None:
        reason = "http_status"
    elif "timeout" in text or "timed out" in text:
        reason = "timeout"
    elif "connect" in text or "network" in text:
        reason = "connection_failure"
    elif "json" in text or "payload" in text or "response" in text:
        reason = "invalid_response"
    elif "database" in text or "postgres" in text:
        reason = "database_failure"
    else:
        reason = "dependency_failure"
    result: dict[str, Any] = {"reason": reason}
    if status is not None:
        result["http_status"] = status
    return result
