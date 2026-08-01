from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb

from app.auth import CurrentUser, audit, require
from app.db.connection import pool


router = APIRouter(prefix="/api/v1/admin/telegram", tags=["telegram"])


class IdentityUpdate(BaseModel):
    chat_id: int
    telegram_user_id: int | None = None
    user_id: str
    enabled: bool = True
    alerts: dict[str, bool] = Field(default_factory=lambda: {"failures": True, "worker": True, "stale_data": True, "success": False})


@router.get("")
async def identities(_: Annotated[CurrentUser, Depends(require("admin"))]) -> list[dict]:
    async with pool.connection() as connection:
        result = await connection.execute(
            """SELECT t.chat_id,t.telegram_user_id,t.enabled,t.alerts,t.updated_at,
                      u.id AS user_id,u.username,u.role
                 FROM core.telegram_identities t JOIN core.users u ON u.id=t.user_id
                ORDER BY t.chat_id"""
        )
        return await result.fetchall()


@router.put("")
async def upsert_identity(payload: IdentityUpdate, request: Request, actor: Annotated[CurrentUser, Depends(require("admin", csrf=True))]) -> dict:
    async with pool.connection() as connection:
        user = await connection.execute("SELECT 1 FROM core.users WHERE id=%s AND is_active=TRUE", (payload.user_id,))
        if not await user.fetchone():
            raise HTTPException(status_code=422, detail="active user not found")
        result = await connection.execute(
            """INSERT INTO core.telegram_identities (chat_id,telegram_user_id,user_id,enabled,alerts)
               VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT (chat_id) DO UPDATE SET telegram_user_id=EXCLUDED.telegram_user_id,
                 user_id=EXCLUDED.user_id,enabled=EXCLUDED.enabled,alerts=EXCLUDED.alerts,updated_at=NOW()
               RETURNING chat_id,telegram_user_id,user_id,enabled,alerts""",
            (payload.chat_id,payload.telegram_user_id,payload.user_id,payload.enabled,Jsonb(payload.alerts)),
        )
        row=await result.fetchone()
        await audit(connection,action="telegram.allowlist.update",outcome="success",request=request,actor=actor,target_type="telegram_chat",target_id=str(payload.chat_id),details={"user_id":payload.user_id,"enabled":payload.enabled})
        return row
