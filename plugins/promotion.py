import asyncio
from datetime import datetime, timedelta, timezone
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


async def _broadcast(client: Client, text: str):
    chat_ids = db.get_db()["authorized_chats"]
    sent, failed = [], []
    for chat_id in chat_ids:
        try:
            await client.send_message(chat_id, text)
            sent.append(chat_id)
        except Exception:
            failed.append(chat_id)
    db.record_promotion(sent, text)
    return sent, failed


@Client.on_message(filters.command("promote"))
@owner_only
async def promote_cmd(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /promote <message>")
    sent, failed = await _broadcast(client, message.text.split(None, 1)[1])
    await message.reply_text(f"✅ Sent: {len(sent)} | Failed: {len(failed)}")


@Client.on_message(filters.command("promote_gc"))
@owner_only
async def promote_gc_cmd(client, message: Message):
    if len(message.command) < 3:
        return await message.reply_text("Usage: /promote_gc <chat_id> <message>")
    try:
        chat_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ Chat ID must be numeric.")
    text = message.text.split(None, 2)[2]
    try:
        await client.send_message(chat_id, text)
    except Exception as exc:
        db.record_targeted_promotion(chat_id, text, False)
        return await message.reply_text(f"❌ Failed: `{type(exc).__name__}`")
    db.record_targeted_promotion(chat_id, text, True)
    await message.reply_text("✅ Promotion sent.")


@Client.on_message(filters.command("promote_media"))
@owner_only
async def promote_media_cmd(client, message: Message):
    source = message.reply_to_message
    if not source:
        return await message.reply_text("Reply to media with /promote_media [caption].")
    caption = message.text.split(None, 1)[1] if len(message.command) > 1 else source.caption
    sent, failed = [], []
    for chat_id in db.get_db()["authorized_chats"]:
        try:
            await source.copy(chat_id, caption=caption)
            sent.append(chat_id)
        except Exception:
            failed.append(chat_id)
    db.record_promotion(sent, caption or "media promotion")
    await message.reply_text(f"✅ Sent: {len(sent)} | Failed: {len(failed)}")


@Client.on_message(filters.command("schedulepromo"))
@owner_only
async def schedulepromo_cmd(_, message: Message):
    if len(message.command) < 3:
        return await message.reply_text("Usage: /schedulepromo <HH:MM> <message>")
    try:
        t = datetime.strptime(message.command[1], "%H:%M").time()
    except ValueError:
        return await message.reply_text("❌ Time must be HH:MM (24-hour).")
    now = datetime.now().astimezone()
    run_at = datetime.combine(now.date(), t, tzinfo=now.tzinfo)
    if run_at <= now:
        run_at += timedelta(days=1)
    db.add_scheduled_promotion(run_at.astimezone(timezone.utc).isoformat(), message.text.split(None, 2)[2])
    await message.reply_text(f"🗓 Scheduled for {run_at:%Y-%m-%d %H:%M %Z}.")


async def scheduler(client: Client):
    while True:
        try:
            now = datetime.now(timezone.utc).isoformat()
            due = db.get_due_promotions(now)
            for item in due:
                sent, failed = await _broadcast(client, item["message"])
                try:
                    await client.send_message(config.OWNER_ID, f"🗓 Scheduled promotion: sent {len(sent)}, failed {len(failed)}")
                except Exception:
                    pass
            await asyncio.sleep(config.PROMOTION_INTERVAL)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(config.PROMOTION_INTERVAL)


@Client.on_message(filters.command("stats"))
@owner_only
async def stats_cmd(_, message: Message):
    stats = db.get_stats()
    top = "\n".join(f"{i}. {title} ({count})" for i, (title, count) in enumerate(stats["top_songs"], 1)) or "No songs yet."
    active = stats["most_active_chat"]
    await message.reply_text(
        "**Bot statistics**\n"
        f"Authorized chats: `{stats['active_chats']}`\n"
        f"Songs played: `{stats['songs']}`\n"
        f"Promotions logged: `{stats['promotions']}`\n"
        f"Most active chat: `{active[0] if active else 'N/A'}`\n\n"
        f"**Top songs**\n{top}"
    )


@Client.on_message(filters.command("leaderboard"))
async def leaderboard_cmd(_, message: Message):
    rows = db.get_leaderboard()
    if not rows:
        return await message.reply_text("No listener points yet.")
    text = "\n".join(f"{i}. `{uid}` — **{points}**" for i, (uid, points) in enumerate(rows, 1))
    await message.reply_text("**Listener leaderboard**\n" + text)
