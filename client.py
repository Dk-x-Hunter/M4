import logging
import os

import pyrogram.errors as pyrogram_errors
import pyrogram.utils as pyrogram_utils
from pyrogram import Client
from pyrogram.raw import types as pyrogram_types
from pytgcalls import PyTgCalls

import config

pyrogram_utils.MIN_CHANNEL_ID = -100000000000000

# Compatibility aliases used by some Pyrogram/PyTgCalls combinations.
if not hasattr(pyrogram_errors, "GroupcallForbidden") and hasattr(pyrogram_errors, "GroupCallInvalid"):
    pyrogram_errors.GroupcallForbidden = pyrogram_errors.GroupCallInvalid
if not hasattr(pyrogram_errors, "GroupcallInvalid") and hasattr(pyrogram_errors, "GroupCallInvalid"):
    pyrogram_errors.GroupcallInvalid = pyrogram_errors.GroupCallInvalid
if not hasattr(pyrogram_types, "InputGroupCallSlug") and hasattr(pyrogram_types, "InputGroupCall"):
    pyrogram_types.InputGroupCallSlug = pyrogram_types.InputGroupCall

logger = logging.getLogger("musicbot")

required = {
    "API_ID": config.API_ID,
    "API_HASH": config.API_HASH,
    "BOT_TOKEN": config.BOT_TOKEN,
    "SESSION_STRING": config.SESSION_STRING,
    "OWNER_ID": config.OWNER_ID,
}
missing = [name for name, value in required.items() if not value]
if missing:
    raise SystemExit("Missing configuration: " + ", ".join(missing))

sessions_dir = os.path.join(os.path.dirname(__file__), "sessions")
os.makedirs(sessions_dir, exist_ok=True)

app = Client(
    "musicbot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    in_memory=True,
    plugins={"root": "plugins"},
)

user = Client(
    "musicuser",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING,
    in_memory=True,
)

call = PyTgCalls(user)
QUEUES = {}
QUEUE_LOCKS = {}
