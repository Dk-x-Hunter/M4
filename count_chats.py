from pyrogram import Client
from pyrogram.enums import ChatType

import config


with Client(
    "chat_counter",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING,
    in_memory=True,
) as app:
    counts = {"total": 0, "groups": 0, "supergroups": 0, "channels": 0, "private": 0}
    for dialog in app.get_dialogs():
        counts["total"] += 1
        t = dialog.chat.type
        if t == ChatType.GROUP:
            counts["groups"] += 1
        elif t == ChatType.SUPERGROUP:
            counts["supergroups"] += 1
        elif t == ChatType.CHANNEL:
            counts["channels"] += 1
        else:
            counts["private"] += 1

print("Total:", counts["total"])
print("Groups:", counts["groups"])
print("Supergroups:", counts["supergroups"])
print("Channels:", counts["channels"])
print("Private:", counts["private"])
