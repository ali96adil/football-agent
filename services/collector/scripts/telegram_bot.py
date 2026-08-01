from __future__ import annotations

import asyncio
import logging
import os

from app.db.connection import close_connection_pool, open_connection_pool, pool
from app.telegram import TelegramBot, TelegramTransport


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


async def run() -> None:
    transport = TelegramTransport(os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    bot = TelegramBot(pool, transport)
    await open_connection_pool()
    try:
        while True:
            await bot.poll_once()
            await bot.send_alerts()
    finally:
        await close_connection_pool()


if __name__ == "__main__":
    asyncio.run(run())
