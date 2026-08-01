from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from typing import Annotated, Any, Callable

from fastapi import Depends, HTTPException, Request, status

from app.db.connection import pool
from app.security import hash_secret


SESSION_COOKIE = "football_session"
CSRF_COOKIE = "football_csrf"
ROLE_PERMISSIONS = {
    "viewer": frozenset({"read"}),
    "operator": frozenset({"read", "operate"}),
    "admin": frozenset({"read", "operate", "admin"}),
}


@dataclass(frozen=True)
class CurrentUser:
    id: str
    username: str
    display_name: str
    role: str

    def has(self, permission: str) -> bool:
        return permission in ROLE_PERMISSIONS.get(self.role, frozenset())


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    return forwarded or (request.client.host if request.client else None)


async def audit(
    connection: Any, *, action: str, outcome: str, request: Request | None = None,
    actor: CurrentUser | None = None, target_type: str | None = None,
    target_id: str | None = None, details: dict[str, Any] | None = None,
) -> None:
    from psycopg.types.json import Jsonb

    await connection.execute(
        """
        INSERT INTO core.audit_log (
            actor_user_id, actor_username, actor_role, action, target_type,
            target_id, outcome, client_ip, details
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            actor.id if actor else None, actor.username if actor else None,
            actor.role if actor else None, action, target_type, target_id, outcome,
            client_ip(request) if request else None, Jsonb(details or {}),
        ),
    )


async def current_user(request: Request) -> CurrentUser:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    async with pool.connection() as connection:
        result = await connection.execute(
            """
            SELECT u.id, u.username, u.display_name, u.role, s.csrf_hash
              FROM core.user_sessions s
              JOIN core.users u ON u.id = s.user_id
             WHERE s.token_hash = %s AND s.revoked_at IS NULL
               AND s.expires_at > NOW() AND u.is_active = TRUE
            """,
            (hash_secret(raw_token),),
        )
        row = await result.fetchone()
        if row:
            await connection.execute(
                "UPDATE core.user_sessions SET last_seen_at=NOW() WHERE token_hash=%s",
                (hash_secret(raw_token),),
            )
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session expired")
    request.state.csrf_hash = row["csrf_hash"]
    return CurrentUser(
        id=str(row["id"]), username=row["username"],
        display_name=row["display_name"], role=row["role"],
    )


UserDependency = Annotated[CurrentUser, Depends(current_user)]


def require(permission: str, *, csrf: bool = False) -> Callable[..., Any]:
    async def dependency(request: Request, user: UserDependency) -> CurrentUser:
        if not user.has(permission):
            async with pool.connection() as connection:
                await audit(connection, action=f"permission.{permission}", outcome="denied", request=request, actor=user)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        if csrf:
            cookie = request.cookies.get(CSRF_COOKIE, "")
            header = request.headers.get("x-csrf-token", "")
            expected_hash = getattr(request.state, "csrf_hash", "")
            if not cookie or not header or not hmac.compare_digest(cookie, header) or not hmac.compare_digest(hash_secret(header), expected_hash):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid CSRF token")
        return user
    return dependency


def session_cookie_secure() -> bool:
    return os.getenv("SESSION_COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
