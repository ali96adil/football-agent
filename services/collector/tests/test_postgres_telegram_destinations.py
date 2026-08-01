from __future__ import annotations

import os
import unittest

from psycopg.types.json import Jsonb
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import build_database_url
from app.telegram import TelegramBot


class _Transport:
    def __init__(self): self.messages: list[tuple[int,str]]=[]
    async def send(self, chat_id: int, text: str) -> None: self.messages.append((chat_id,text))
    async def updates(self, _offset): return []


@unittest.skipUnless(
    os.getenv("RUN_POSTGRES_INTEGRATION") == "1",
    "set RUN_POSTGRES_INTEGRATION=1 against an ephemeral migrated PostgreSQL database",
)
class PostgreSQLTelegramDestinationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.pool=AsyncConnectionPool(
            conninfo=build_database_url(),min_size=1,max_size=2,open=False,
            kwargs={"row_factory":dict_row},
        )
        await self.pool.open()
        await self.pool.wait()
        async with self.pool.connection() as connection:
            await connection.execute("DELETE FROM core.users WHERE username='telegram_schema_admin'")
            result=await connection.execute(
                """INSERT INTO core.users (username,display_name,password_hash,role)
                   VALUES ('telegram_schema_admin','Telegram Admin','not-used','admin')
                   RETURNING id"""
            )
            self.user_id=(await result.fetchone())["id"]

    async def asyncTearDown(self) -> None:
        async with self.pool.connection() as connection:
            await connection.execute("DELETE FROM core.jobs WHERE idempotency_key='old-backlog'")
            await connection.execute("DELETE FROM core.telegram_deliveries WHERE destination_chat_id IN (-7001,-7002)")
            await connection.execute("DELETE FROM core.telegram_destinations WHERE chat_id IN (-7001,-7002)")
            await connection.execute("DELETE FROM core.telegram_identities WHERE user_id=%s",(self.user_id,))
            await connection.execute("DELETE FROM core.users WHERE id=%s",(self.user_id,))
        await self.pool.close()

    async def test_private_and_group_share_sender_but_rbac_requires_exact_pair(self) -> None:
        async with self.pool.connection() as connection:
            for chat_id in (7001,-7001):
                await connection.execute(
                    """INSERT INTO core.telegram_identities
                       (chat_id,telegram_user_id,user_id,enabled,alerts)
                       VALUES (%s,356659919,%s,TRUE,%s)""",
                    (chat_id,self.user_id,Jsonb({})),
                )
        bot=TelegramBot(self.pool,_Transport())
        private=await bot.identity(7001,356659919)
        group=await bot.identity(-7001,356659919)
        rejected=await bot.identity(-7001,467148068)
        self.assertEqual(private.user.role,"admin")
        self.assertEqual(group.user.role,"admin")
        self.assertIsNone(rejected)

    async def test_destination_is_independent_and_delivery_claim_is_durable(self) -> None:
        async with self.pool.connection() as connection:
            await connection.execute(
                """INSERT INTO core.telegram_destinations
                   (chat_id,title,chat_type,enabled,publish_prediction_new)
                   VALUES (-7002,'destination only','group',TRUE,TRUE)"""
            )
        bot=TelegramBot(self.pool,_Transport())
        self.assertIsNone(await bot.identity(-7002,356659919))
        first=await bot._claim(-7002,"prediction:test","prediction_new","a"*64,"2026-08-01T00:00:00Z")
        duplicate=await bot._claim(-7002,"prediction:test","prediction_new","a"*64,"2026-08-01T00:00:00Z")
        changed=await bot._claim(-7002,"prediction:test","prediction_changed","b"*64,"2026-08-01T00:01:00Z")
        self.assertTrue(first)
        self.assertFalse(duplicate)
        self.assertTrue(changed)

    async def test_activation_cursor_cuts_backlog_and_failure_text_is_not_published(self) -> None:
        async with self.pool.connection() as connection:
            await connection.execute(
                """INSERT INTO core.telegram_destinations
                   (chat_id,title,chat_type,enabled,activated_at,
                    publish_update_success,publish_update_failure)
                   VALUES (-7002,'cursor test','group',TRUE,NOW(),TRUE,TRUE)"""
            )
            await connection.execute(
                """INSERT INTO core.jobs
                   (job_type,idempotency_key,status,finished_at,last_error)
                   VALUES ('sync_pipeline','old-backlog','dead_letter',NOW()-INTERVAL '1 minute','secret internal traceback')"""
            )
            destination_result=await connection.execute(
                "SELECT * FROM core.telegram_destinations WHERE chat_id=-7002"
            )
            destination=await destination_result.fetchone()
        transport=_Transport()
        bot=TelegramBot(self.pool,transport)
        await bot._publish_job_events(destination)
        self.assertEqual(transport.messages,[])


if __name__ == "__main__": unittest.main()
