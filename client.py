import os
import logging

import pyrogram.errors as pyrogram_errors
import pyrogram.utils as pyrogram_utils
from pyrogram import Client
from pyrogram.raw import types as pyrogram_types
from pytgcalls import PyTgCalls

import config

logger = logging.getLogger(__name__)

# Pyrogram/PyTgCalls compatibility fixes
pyrogram_utils.MIN_CHANNEL_ID = -100000000000000

# Fix old PyTgCalls error names
if not hasattr(pyrogram_errors, "GroupcallForbidden"):
    for name in (
        "GroupCallForbidden",
        "GroupCallInvalid",
        "GroupcallInvalid",
    ):
        if hasattr(pyrogram_errors, name):
            pyrogram_errors.GroupcallForbidden = getattr(
                pyrogram_errors, name
            )
            break

if not hasattr(pyrogram_errors, "GroupcallInvalid"):
    for name in (
        "GroupCallInvalid",
        "GroupCallForbidden",
        "GroupcallForbidden",
    ):
        if hasattr(pyrogram_errors, name):
            pyrogram_errors.GroupcallInvalid = getattr(
                pyrogram_errors, name
            )
            break

# Configuration validation
required = {
    "API_ID": config.API_ID,
    "API_HASH": config.API_HASH,
    "BOT_TOKEN": config.BOT_TOKEN,
    "SESSION_STRING": config.SESSION_STRING,
    "OWNER_ID": config.OWNER_ID,
}

missing = [
    key for key, value in required.items()
    if not value or value == 0
]

if missing:
    raise SystemExit(
        "Missing required configuration: " + ", ".join(missing)
    )

# Bot client
app = Client(
    "M4Bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    in_memory=True,
    plugins={"root": "plugins"},
)

# User account client
user = Client(
    "M4User",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING,
    in_memory=True,
)

# Voice chat client
call = PyTgCalls(user)

# Queue storage
QUEUES = {}
QUEUE_LOCKS = {}