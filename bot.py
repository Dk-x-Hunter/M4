import asyncio
import logging

import db
from client import app, call, user

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def scheduler(client):
    """
    Background scheduler.

    Keep your existing scheduler implementation here if
    your repository already has one.
    """
    while True:
        await asyncio.sleep(60)


def main():
    logger.info("Starting M4 Music Bot")

    # Initialize database
    db.init_db()

    # Start user account
    user.start()
    logger.info("User client started")

    # Start voice chat client
    call.start()
    logger.info("Voice chat client started")

    # Start bot
    app.start()
    logger.info("Bot client started")

    # Start background scheduler
    task = app.loop.create_task(scheduler(app))

    try:
        from pyrogram import idle
        idle()
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
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

        try:
            app.stop()
        except Exception:
            pass

        logger.info("Bot stopped")


if __name__ == "__main__":
    main()