import os
import logging

from pyrogram import Client
from pytgcalls import PyTgCalls

import config

logger = logging.getLogger(__name__)

# Validate configuration
required_config = {
    "API_ID": config.API_ID,
    "API_HASH": config.API_HASH,
    "BOT_TOKEN": config.BOT_TOKEN,
    "SESSION_STRING": config.SESSION_STRING,
    "OWNER_ID": config.OWNER_ID,
}

missing = [
    name for name, value in required_config.items()
    if not value or value == 0
]

if missing:
    raise RuntimeError(
        f"Missing configuration: {', '.join(missing)}"
    )

# Bot client
app = Client(
    "M4Bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    plugins=dict(root="plugins"),
)

# User client
user = Client(
    "M4User",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING,
)

# Voice chat client
call = PyTgCalls(user)

logger.info("Telegram clients initialized successfully")