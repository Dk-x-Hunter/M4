import asyncio
from functools import wraps

import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import filters as call_filters
from pytgcalls.types import MediaStream, StreamEnded

import config
import db
from client import QUEUES, call

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch1",
    "socket_timeout": 15,
}


def gated(func):
    @wraps(func)
    async def wrapper(client, message: Message):
        if not message.from_user:
            return
        if message.chat.type.value == "private":
            return await message.reply_text("Use this inside a group voice chat.")
        if not (db.is_sudo(message.from_user.id) or db.is_authorized_chat(message.chat.id)):
            return await message.reply_text("🚫 This group isn't authorized. Ask the owner to run /authorize here.")
        return await func(client, message)
    return wrapper


def _extract(query: str):
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        info = ydl.extract_info(query, download=False)
        if info and info.get("entries"):
            info = next((x for x in info["entries"] if x), None)
        if not info or not info.get("url"):
            raise ValueError("No playable audio was found.")
        return {"title": info.get("title") or "Unknown", "url": info["url"]}


async def _play_next(chat_id: int):
    queue = QUEUES.get(chat_id, [])
    if not queue:
        try:
            await call.leave_call(chat_id)
        except Exception:
            pass
        return False
    track = queue[0]
    await call.play(chat_id, MediaStream(track["url"]))
    return True


@call.on_update(call_filters.stream_end())
async def stream_end_handler(_, update: StreamEnded):
    chat_id = update.chat_id
    queue = QUEUES.get(chat_id, [])
    if queue:
        queue.pop(0)
    if queue:
        try:
            await _play_next(chat_id)
        except Exception:
            QUEUES[chat_id] = []
            try:
                await call.leave_call(chat_id)
            except Exception:
                pass
    else:
        QUEUES.pop(chat_id, None)
        try:
            await call.leave_call(chat_id)
        except Exception:
            pass


@Client.on_message(filters.command("play"))
@gated
async def play_cmd(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /play <song name or link>")
    chat_id = message.chat.id
    queue = QUEUES.setdefault(chat_id, [])
    if len(queue) >= config.MAX_QUEUE_SIZE:
        return await message.reply_text(f"❌ Queue limit reached ({config.MAX_QUEUE_SIZE}).")

    query = message.text.split(None, 1)[1].strip()
    msg = await message.reply_text("🔎 Searching...")
    try:
        track = await asyncio.to_thread(_extract, query)
    except Exception as exc:
        return await msg.edit_text(f"❌ Couldn't find audio: `{type(exc).__name__}`")

    track["requested_by"] = message.from_user.mention
    queue.append(track)

    if len(queue) > 1:
        return await msg.edit_text(f"➕ Queued (#{len(queue)}): **{track['title']}**")

    try:
        await call.play(chat_id, MediaStream(track["url"]))
        db.record_song(chat_id, message.from_user.id, track["title"])
        await msg.edit_text(f"▶️ Playing: **{track['title']}**")
    except Exception as exc:
        queue.pop(0)
        if not queue:
            QUEUES.pop(chat_id, None)
        await msg.edit_text(f"❌ Failed to join/play in VC: `{type(exc).__name__}`")


@Client.on_message(filters.command("skip"))
@gated
async def skip_cmd(_, message: Message):
    queue = QUEUES.get(message.chat.id, [])
    if not queue:
        return await message.reply_text("Nothing is playing.")
    queue.pop(0)
    if queue:
        try:
            await _play_next(message.chat.id)
            return await message.reply_text("⏭ Skipped. Playing next track.")
        except Exception:
            QUEUES.pop(message.chat.id, None)
    else:
        QUEUES.pop(message.chat.id, None)
    try:
        await call.leave_call(message.chat.id)
    except Exception:
        pass
    await message.reply_text("⏭ Skipped. Queue is empty.")


@Client.on_message(filters.command("stop"))
@gated
async def stop_cmd(_, message: Message):
    QUEUES.pop(message.chat.id, None)
    try:
        await call.leave_call(message.chat.id)
    except Exception:
        pass
    await message.reply_text("⏹ Stopped and left the voice chat.")


@Client.on_message(filters.command("pause"))
@gated
async def pause_cmd(_, message: Message):
    try:
        await call.pause_stream(message.chat.id)
        await message.reply_text("⏸ Paused.")
    except Exception as exc:
        await message.reply_text(f"❌ Cannot pause: `{type(exc).__name__}`")


@Client.on_message(filters.command("resume"))
@gated
async def resume_cmd(_, message: Message):
    try:
        await call.resume_stream(message.chat.id)
        await message.reply_text("▶️ Resumed.")
    except Exception as exc:
        await message.reply_text(f"❌ Cannot resume: `{type(exc).__name__}`")


@Client.on_message(filters.command("queue"))
@gated
async def queue_cmd(_, message: Message):
    queue = QUEUES.get(message.chat.id, [])
    if not queue:
        return await message.reply_text("Queue is empty.")
    lines = [f"{i}. **{t['title']}** — {t['requested_by']}" for i, t in enumerate(queue, 1)]
    await message.reply_text("**Queue:**\n" + "\n".join(lines))
