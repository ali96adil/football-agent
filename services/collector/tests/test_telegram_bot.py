from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from typing import Any

from app.auth import CurrentUser
from app.telegram import (
    TelegramBot, TelegramIdentity, command_permission, content_hash,
    prediction_payload,
    prediction_is_current,
)


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
    def __init__(self, identity: TelegramIdentity | None):
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

    async def test_rejected_command_logs_only_safe_identity_metadata(self):
        bot=_Bot(None)
        message={
            "text":"/status secret-command-content",
            "chat":{"id":-5106995856,"type":"group","title":"football-agent"},
            "from":{"id":467148068,"username":"candidate_user","first_name":"Secret Name"},
        }
        with self.assertLogs("football-telegram",level="WARNING") as captured:
            await bot.handle(message)
        log="\n".join(captured.output)
        self.assertIn('"chat_id":-5106995856',log)
        self.assertIn('"chat_type":"group"',log)
        self.assertIn('"chat_title":"football-agent"',log)
        self.assertIn('"telegram_user_id":467148068',log)
        self.assertIn('"username":"candidate_user"',log)
        self.assertIn('"reason":"not_allowlisted"',log)
        self.assertNotIn("secret-command-content",log)
        self.assertNotIn("Secret Name",log)
        self.assertEqual(bot.transport.messages,[])

    def test_prediction_hash_changes_only_for_public_meaningful_fields(self):
        now=datetime.now(timezone.utc)
        row={
            "id":"prediction","fixture_id":"fixture","home_snapshot_hash":"home-hash",
            "away_snapshot_hash":"away-hash","kickoff_at":now+timedelta(hours=1),
            "home_team":"Home","away_team":"Away","predicted_outcome":"home_win",
            "confidence":0.7,"home_win_probability":0.6,"draw_probability":0.2,
            "away_win_probability":0.2,"most_likely_home_goals":2,
            "most_likely_away_goals":1,"metadata":{"internal":"secret"},
        }
        original=content_hash(prediction_payload(row))
        row["metadata"]={"internal":"changed secret"}
        self.assertEqual(content_hash(prediction_payload(row)),original)
        row["confidence"]=0.8
        self.assertNotEqual(content_hash(prediction_payload(row)),original)

    def test_prediction_window_blocks_backlog_and_started_fixture(self):
        now=datetime.now(timezone.utc)
        row={"updated_at":now+timedelta(seconds=1),"kickoff_at":now+timedelta(hours=1),"result_confirmed":False}
        self.assertTrue(prediction_is_current(row,now,now=now))
        row["updated_at"]=now-timedelta(seconds=1)
        self.assertFalse(prediction_is_current(row,now,now=now))
        row["updated_at"]=now+timedelta(seconds=1)
        row["kickoff_at"]=now
        self.assertFalse(prediction_is_current(row,now,now=now))
        row["kickoff_at"]=now+timedelta(hours=1)
        row["result_confirmed"]=True
        self.assertFalse(prediction_is_current(row,now,now=now))


if __name__ == "__main__": unittest.main()
