from __future__ import annotations

import unittest
from typing import Any

from app.auth import CurrentUser
from app.telegram import TelegramBot, TelegramIdentity, command_permission


class _Context:
    async def __aenter__(self): return _Connection()
    async def __aexit__(self, *_args): return None


class _Connection:
    async def execute(self, *_args, **_kwargs): return None


class _Pool:
    def connection(self): return _Context()


class _Transport:
    def __init__(self): self.messages: list[tuple[int,str]]=[]
    async def send(self, chat_id:int, text:str): self.messages.append((chat_id,text))
    async def updates(self, _offset): return []


class _Bot(TelegramBot):
    def __init__(self, identity: TelegramIdentity):
        self.test_identity=identity; self.executed: list[str]=[]
        super().__init__(_Pool(), _Transport())
    async def identity(self, _chat_id:int, _telegram_user_id:int|None): return self.test_identity
    async def execute(self, _identity, command:str, _argument:str): self.executed.append(command); return "ok"


class TelegramBotTests(unittest.IsolatedAsyncioTestCase):
    def identity(self, role:str) -> TelegramIdentity:
        return TelegramIdentity(10,20,CurrentUser("id",role,role,role),{})

    def test_command_permission_matrix(self):
        for command in ("status","fixtures","predictions","sources","jobs"):
            self.assertEqual(command_permission(command),"read")
        for command in ("sync","snapshots","run_predictions","retry"):
            self.assertEqual(command_permission(command),"operate")
        self.assertIsNone(command_permission("unknown"))

    async def test_viewer_can_read_but_cannot_control(self):
        bot=_Bot(self.identity("viewer"))
        await bot.handle({"text":"/status","chat":{"id":10},"from":{"id":20}})
        await bot.handle({"text":"/sync","chat":{"id":10},"from":{"id":20}})
        self.assertEqual(bot.executed,["status"])
        self.assertIn("الصلاحية",bot.transport.messages[-1][1])

    async def test_operator_control_command_is_dispatched_without_network(self):
        bot=_Bot(self.identity("operator"))
        await bot.handle({"text":"/run_predictions","chat":{"id":10},"from":{"id":20}})
        self.assertEqual(bot.executed,["run_predictions"])
        self.assertEqual(bot.transport.messages,[(10,"ok")])


if __name__ == "__main__": unittest.main()
