from functools import wraps

from pyrogram import Client, filters
from pyrogram.types import Message

import config
import db


def owner_only(func):
    @wraps(func)
    async def wrapper(client, message: Message):
        if not message.from_user or message.from_user.id != config.OWNER_ID:
            return await message.reply_text("🚫 Owner only.")
        return await func(client, message)
    return wrapper


def sudo_only(func):
    @wraps(func)
    async def wrapper(client, message: Message):
        if not message.from_user or not db.is_sudo(message.from_user.id):
            return await message.reply_text("🚫 Sudo/admin only.")
        return await func(client, message)
    return wrapper


@Client.on_message(filters.command("authorize"))
@sudo_only
async def authorize_cmd(_, message: Message):
    if message.chat.type.value == "private":
        return await message.reply_text("Run this inside the group you want to authorize.")
    db.authorize_chat(message.chat.id)
    await message.reply_text("✅ This group is now authorized.")


@Client.on_message(filters.command("unauthorize"))
@sudo_only
async def unauthorize_cmd(_, message: Message):
    db.unauthorize_chat(message.chat.id)
    await message.reply_text("🚫 This group's access has been revoked.")


@Client.on_message(filters.command("addsudo"))
@owner_only
async def addsudo_cmd(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /addsudo <user_id>")
    try:
        uid = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ User ID must be numeric.")
    if uid <= 0:
        return await message.reply_text("❌ Invalid user ID.")
    db.add_sudo(uid)
    await message.reply_text(f"✅ `{uid}` added as sudo/admin.")


@Client.on_message(filters.command("rmsudo"))
@owner_only
async def rmsudo_cmd(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /rmsudo <user_id>")
    try:
        uid = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ User ID must be numeric.")
    if uid == config.OWNER_ID:
        return await message.reply_text("❌ The owner cannot be removed.")
    db.remove_sudo(uid)
    await message.reply_text(f"✅ `{uid}` removed from sudo/admin.")


@Client.on_message(filters.command("sudolist"))
@sudo_only
async def sudolist_cmd(_, message: Message):
    users = db.get_db()["sudo_users"]
    text = "\n".join(f"• `{u}`" for u in users) or "None"
    await message.reply_text(f"**Sudo users:**\n{text}")
