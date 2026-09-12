import asyncio
import logging

import config
import db
from client import app, call, user
from plugins.promotion import scheduler

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("musicbot")


def main():
    db.init_db()
    logger.info("Starting music bot")
    user.start()
    call.start()
    app.start()
    task = asyncio.create_task(scheduler(app))
    try:
        from pyrogram import idle
        idle()
    finally:
        task.cancel()
        try:
            call.stop()
        except Exception:
            pass
        try:
            user.stop()
        except Exception:
            pass
        app.stop()
        logger.info("Bot stopped")


if __name__ == "__main__":
    main()
