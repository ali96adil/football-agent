from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.auth import (
    CSRF_COOKIE, SESSION_COOKIE, CurrentUser, UserDependency, audit, client_ip,
    require, session_cookie_secure,
)
from app.db.connection import pool
from app.security import hash_password, hash_secret, new_secret, verify_password


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
users_router = APIRouter(prefix="/api/v1/admin/users", tags=["users"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class UserCreate(BaseModel):
    username: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{2,63}$")
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=1024)
    role: Literal["admin", "operator", "viewer"]


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: Literal["admin", "operator", "viewer"] | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=1024)


def public_user(row: dict) -> dict:
    return {key: row[key] for key in ("id", "username", "display_name", "role", "is_active", "created_at", "last_login_at") if key in row}


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response) -> dict:
    username = payload.username.strip().lower()
    ip = client_ip(request)
    async with pool.connection() as connection:
        attempts = await connection.execute(
            """SELECT COUNT(*) AS attempts FROM core.login_attempts
                 WHERE username=%s AND client_ip IS NOT DISTINCT FROM %s
                   AND succeeded=FALSE AND attempted_at > NOW() - INTERVAL '15 minutes'""",
            (username, ip),
        )
        if int((await attempts.fetchone())["attempts"]) >= int(os.getenv("LOGIN_RATE_LIMIT", "5")):
            await audit(connection, action="auth.login", outcome="denied", request=request, details={"reason": "rate_limited", "username": username})
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="too many login attempts")
        result = await connection.execute(
            "SELECT id, username, display_name, role, is_active, password_hash FROM core.users WHERE username=%s",
            (username,),
        )
        row = await result.fetchone()
        valid = bool(row and row["is_active"] and verify_password(payload.password, row["password_hash"]))
        await connection.execute(
            "INSERT INTO core.login_attempts (username, client_ip, succeeded) VALUES (%s, %s, %s)",
            (username, ip, valid),
        )
        if not valid:
            await audit(connection, action="auth.login", outcome="failure", request=request, details={"username": username})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
        token, csrf = new_secret(), new_secret()
        expires = datetime.now(timezone.utc) + timedelta(hours=int(os.getenv("SESSION_TTL_HOURS", "12")))
        await connection.execute(
            """INSERT INTO core.user_sessions
               (user_id, token_hash, csrf_hash, expires_at, client_ip, user_agent)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (row["id"], hash_secret(token), hash_secret(csrf), expires, ip, request.headers.get("user-agent", "")[:500]),
        )
        await connection.execute("UPDATE core.users SET last_login_at=NOW() WHERE id=%s", (row["id"],))
        actor = CurrentUser(str(row["id"]), row["username"], row["display_name"], row["role"])
        await audit(connection, action="auth.login", outcome="success", request=request, actor=actor)
    response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=session_cookie_secure(), samesite="strict", max_age=int((expires-datetime.now(timezone.utc)).total_seconds()), path="/")
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, secure=session_cookie_secure(), samesite="strict", max_age=int((expires-datetime.now(timezone.utc)).total_seconds()), path="/")
    return {"user": {"id": actor.id, "username": actor.username, "display_name": actor.display_name, "role": actor.role}}


@router.get("/me")
async def me(user: UserDependency) -> dict:
    return {"id": user.id, "username": user.username, "display_name": user.display_name, "role": user.role}


@router.post("/logout")
async def logout(request: Request, response: Response, user: Annotated[CurrentUser, Depends(require("read", csrf=True))]) -> dict:
    token = request.cookies.get(SESSION_COOKIE, "")
    async with pool.connection() as connection:
        await connection.execute("UPDATE core.user_sessions SET revoked_at=NOW() WHERE token_hash=%s", (hash_secret(token),))
        await audit(connection, action="auth.logout", outcome="success", request=request, actor=user)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"status": "logged_out"}


@users_router.get("")
async def list_users(_: Annotated[CurrentUser, Depends(require("admin"))]) -> list[dict]:
    async with pool.connection() as connection:
        result = await connection.execute("SELECT id, username, display_name, role, is_active, created_at, last_login_at FROM core.users ORDER BY username")
        return [public_user(row) for row in await result.fetchall()]


@users_router.post("", status_code=201)
async def create_user(payload: UserCreate, request: Request, actor: Annotated[CurrentUser, Depends(require("admin", csrf=True))]) -> dict:
    async with pool.connection() as connection:
        try:
            result = await connection.execute(
                """INSERT INTO core.users (username, display_name, password_hash, role)
                   VALUES (%s, %s, %s, %s)
                   RETURNING id, username, display_name, role, is_active, created_at, last_login_at""",
                (payload.username, payload.display_name.strip(), hash_password(payload.password), payload.role),
            )
            row = await result.fetchone()
        except Exception as exc:
            if getattr(exc, "sqlstate", None) == "23505":
                raise HTTPException(status_code=409, detail="username already exists") from exc
            raise
        await audit(connection, action="users.create", outcome="success", request=request, actor=actor, target_type="user", target_id=str(row["id"]), details={"role": payload.role})
    return public_user(row)


@users_router.patch("/{user_id}")
async def update_user(user_id: str, payload: UserUpdate, request: Request, actor: Annotated[CurrentUser, Depends(require("admin", csrf=True))]) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    assignments, values = [], []
    for field in ("display_name", "role", "is_active"):
        if field in changes:
            assignments.append(f"{field}=%s")
            values.append(changes[field])
    if payload.password is not None:
        assignments.append("password_hash=%s")
        values.append(hash_password(payload.password))
    if not assignments:
        raise HTTPException(status_code=422, detail="no changes supplied")
    assignments.append("updated_at=NOW()")
    async with pool.connection() as connection:
        result = await connection.execute(
            f"UPDATE core.users SET {', '.join(assignments)} WHERE id=%s RETURNING id, username, display_name, role, is_active, created_at, last_login_at",
            (*values, user_id),
        )
        row = await result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="user not found")
        if payload.is_active is False:
            await connection.execute("UPDATE core.user_sessions SET revoked_at=NOW() WHERE user_id=%s", (user_id,))
        await audit(connection, action="users.update", outcome="success", request=request, actor=actor, target_type="user", target_id=user_id, details={"fields": sorted(changes)})
    return public_user(row)
