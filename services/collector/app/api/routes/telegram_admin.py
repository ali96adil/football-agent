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


class DestinationUpdate(BaseModel):
    chat_id: int
    title: str = Field(min_length=1, max_length=255)
    chat_type: str = Field(pattern=r"^(private|group|supergroup|channel)$")
    enabled: bool = False
    publish_prediction_new: bool = False
    publish_prediction_changed: bool = False
    publish_update_success: bool = False
    publish_update_failure: bool = False


@router.get("")
async def identities(_: Annotated[CurrentUser, Depends(require("admin"))]) -> list[dict]:
    async with pool.connection() as connection:
        result = await connection.execute(
            """SELECT t.chat_id,t.telegram_user_id,t.enabled,t.alerts,t.updated_at,
                      u.id AS user_id,u.username,u.role
                 FROM core.telegram_identities t JOIN core.users u ON u.id=t.user_id
                ORDER BY t.chat_id,t.telegram_user_id"""
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
               ON CONFLICT (chat_id,telegram_user_id) DO UPDATE SET
                 user_id=EXCLUDED.user_id,enabled=EXCLUDED.enabled,alerts=EXCLUDED.alerts,updated_at=NOW()
               RETURNING chat_id,telegram_user_id,user_id,enabled,alerts""",
            (payload.chat_id,payload.telegram_user_id,payload.user_id,payload.enabled,Jsonb(payload.alerts)),
        )
        row=await result.fetchone()
        await audit(connection,action="telegram.allowlist.update",outcome="success",request=request,actor=actor,target_type="telegram_chat",target_id=str(payload.chat_id),details={"user_id":payload.user_id,"enabled":payload.enabled})
        return row


@router.get("/destinations")
async def destinations(_: Annotated[CurrentUser, Depends(require("admin"))]) -> list[dict]:
    async with pool.connection() as connection:
        result = await connection.execute(
            """SELECT chat_id,title,chat_type,enabled,activated_at,
                      publish_prediction_new,publish_prediction_changed,
                      publish_update_success,publish_update_failure,updated_at
                 FROM core.telegram_destinations ORDER BY chat_id"""
        )
        return await result.fetchall()


@router.put("/destinations")
async def upsert_destination(
    payload: DestinationUpdate, request: Request,
    actor: Annotated[CurrentUser, Depends(require("admin", csrf=True))],
) -> dict:
    async with pool.connection() as connection:
        result = await connection.execute(
            """INSERT INTO core.telegram_destinations
               (chat_id,title,chat_type,enabled,activated_at,
                publish_prediction_new,publish_prediction_changed,
                publish_update_success,publish_update_failure,updated_by)
               VALUES (%s,%s,%s,%s,NOW(),%s,%s,%s,%s,%s)
               ON CONFLICT (chat_id) DO UPDATE SET
                 title=EXCLUDED.title,chat_type=EXCLUDED.chat_type,
                 enabled=EXCLUDED.enabled,
                 activated_at=CASE
                   WHEN EXCLUDED.enabled AND (
                     NOT core.telegram_destinations.enabled
                     OR (EXCLUDED.publish_prediction_new AND NOT core.telegram_destinations.publish_prediction_new)
                     OR (EXCLUDED.publish_prediction_changed AND NOT core.telegram_destinations.publish_prediction_changed)
                     OR (EXCLUDED.publish_update_success AND NOT core.telegram_destinations.publish_update_success)
                     OR (EXCLUDED.publish_update_failure AND NOT core.telegram_destinations.publish_update_failure)
                   ) THEN NOW()
                   ELSE core.telegram_destinations.activated_at END,
                 publish_prediction_new=EXCLUDED.publish_prediction_new,
                 publish_prediction_changed=EXCLUDED.publish_prediction_changed,
                 publish_update_success=EXCLUDED.publish_update_success,
                 publish_update_failure=EXCLUDED.publish_update_failure,
                 updated_at=NOW(),updated_by=EXCLUDED.updated_by
               RETURNING chat_id,title,chat_type,enabled,activated_at,
                         publish_prediction_new,publish_prediction_changed,
                         publish_update_success,publish_update_failure""",
            (
                payload.chat_id,payload.title,payload.chat_type,payload.enabled,
                payload.publish_prediction_new,payload.publish_prediction_changed,
                payload.publish_update_success,payload.publish_update_failure,actor.id,
            ),
        )
        row=await result.fetchone()
        await audit(
            connection,action="telegram.destination.update",outcome="success",
            request=request,actor=actor,target_type="telegram_destination",
            target_id=str(payload.chat_id),
            details={"enabled":payload.enabled,"subscriptions":{
                "prediction_new":payload.publish_prediction_new,
                "prediction_changed":payload.publish_prediction_changed,
                "update_success":payload.publish_update_success,
                "update_failure":payload.publish_update_failure,
            }},
        )
        return row
