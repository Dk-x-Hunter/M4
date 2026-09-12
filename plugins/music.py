import asyncio
import logging
import os
from functools import wraps

import yt_dlp
from pyrogram import filters
from pyrogram.types import Message
from pytgcalls.types import MediaStream

import client
import db
import config

logger = logging.getLogger(__name__)

# --------------------------------------------------
# YouTube / yt-dlp configuration
# --------------------------------------------------

YDL_OPTS = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "noplaylist": True,
    "quiet": False,
    "no_warnings": False,
    "default_search": "ytsearch1",
    "socket_timeout": 30,
    "retries": 5,
    "fragment_retries": 5,
    "extractor_retries": 5,
    "skip_unavailable_fragments": True,
    # YouTube-specific options to bypass bot detection
    "extractor_args": {
        "youtube": {
            "player_client": ["web"],
            "player_skip": ["js", "configs"],
        }
    },
    # Additional headers to avoid being detected as a bot
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    # Disable DASH to simplify extraction
    "youtube_include_dash_manifest": False,
}


# --------------------------------------------------
# Global variables
# --------------------------------------------------

CALLS = client.call


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def admin_only(func):
    @wraps(func)
    async def wrapper(c, message: Message, *args, **kwargs):
        if not message.from_user:
            return

        user_id = message.from_user.id

        if user_id == config.OWNER_ID:
            return await func(c, message, *args, **kwargs)

        try:
            # Check if user is admin in the chat
            member = await c.get_chat_member(message.chat.id, user_id)
            if not member.privileges:
                return await message.reply_text(
                    "❌ You are not allowed to use this command."
                )

        except Exception:
            logger.exception("Failed to check admin permissions")
            return await message.reply_text(
                "⚠️ Could not verify your permissions."
            )

        return await func(c, message, *args, **kwargs)

    return wrapper


async def _extract(query: str):
    """
    Extract an audio stream from YouTube.

    Returns:
        {
            "title": "...",
            "url": "..."
        }
    """

    try:
        search_query = query

        if not query.startswith(("http://", "https://")):
            search_query = f"ytsearch1:{query}"

        logger.info("Extracting audio for query: %s", query)
        
        loop = asyncio.get_running_loop()

        def extract():
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                logger.info("Starting yt-dlp extraction...")
                info = ydl.extract_info(search_query, download=False)
                logger.info("yt-dlp extraction completed")
                return info

        info = await loop.run_in_executor(None, extract)

        if not info:
            raise RuntimeError("No information returned by yt-dlp.")

        if "entries" in info:
            entries = info.get("entries") or []

            if not entries:
                raise RuntimeError("No results found.")

            info = entries[0]

        if not info:
            raise RuntimeError("No video information found.")

        stream_url = info.get("url")
        title = info.get("title") or "Unknown title"

        if not stream_url:
            raise RuntimeError(
                "yt-dlp did not return a playable audio URL."
            )

        logger.info("Successfully extracted: %s", title)

        return {
            "title": title,
            "url": stream_url,
        }

    except Exception as error:
        logger.exception(
            "yt-dlp extraction failed for query: %s",
            query,
        )
        raise RuntimeError(
            f"Could not extract audio from YouTube: {error}"
        ) from error


async def _get_queue(chat_id: int):
    queue = await db.get_queue(chat_id)

    if queue is None:
        queue = []

    return queue


async def _save_queue(chat_id: int, queue):
    await db.set_queue(chat_id, queue)


async def _clear_queue(chat_id: int):
    await db.set_queue(chat_id, [])


async def _play_next(chat_id: int):
    queue = await _get_queue(chat_id)

    if not queue:
        try:
            await CALLS.leave_group_call(chat_id)
        except Exception:
            pass
        return

    current = queue[0]

    try:
        logger.info(
            "Playing in chat %s: %s",
            chat_id,
            current.get("title", "Unknown title"),
        )
        
        # Use MediaStream for PyTgCalls 2.2.8
        await CALLS.play(
            chat_id,
            MediaStream(current["url"]),
        )

        logger.info(
            "Now playing in %s: %s",
            chat_id,
            current.get("title", "Unknown title"),
        )

    except Exception:
        logger.exception(
            "Failed to play audio in chat %s",
            chat_id,
        )

        queue.pop(0)
        await _save_queue(chat_id, queue)

        await _play_next(chat_id)


# --------------------------------------------------
# Commands
# --------------------------------------------------

@client.app.on_message(filters.command("play"))
@admin_only
async def play_music(c, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "🎵 Usage:\n"
            "`/play song name or YouTube URL`"
        )

    query = " ".join(message.command[1:])

    status = await message.reply_text(
        "🔎 Searching for your song..."
    )

    try:
        result = await _extract(query)

        chat_id = message.chat.id
        queue = await _get_queue(chat_id)

        queue.append(
            {
                "title": result["title"],
                "url": result["url"],
                "requested_by": (
                    message.from_user.id
                    if message.from_user
                    else None
                ),
            }
        )

        await _save_queue(chat_id, queue)

        if len(queue) == 1:
            await _play_next(chat_id)

            await status.edit_text(
                f"▶️ **Now playing:**\n"
                f"{result['title']}"
            )
        else:
            await status.edit_text(
                f"➕ **Added to queue:**\n"
                f"{result['title']}\n\n"
                f"📌 Position: `{len(queue)}`"
            )

    except Exception as error:
        logger.exception("Play command failed")

        await status.edit_text(
            "❌ **Could not play this song.**\n\n"
            f"`{error}`"
        )


@client.app.on_message(filters.command("pause"))
@admin_only
async def pause_music(c, message: Message):
    try:
        await CALLS.pause(message.chat.id)
        await message.reply_text("⏸️ Music paused.")
    except Exception as error:
        logger.exception("Pause failed")
        await message.reply_text(
            f"❌ Could not pause music:\n`{error}`"
        )


@client.app.on_message(filters.command("resume"))
@admin_only
async def resume_music(c, message: Message):
    try:
        await CALLS.resume(message.chat.id)
        await message.reply_text("▶️ Music resumed.")
    except Exception as error:
        logger.exception("Resume failed")
        await message.reply_text(
            f"❌ Could not resume music:\n`{error}`"
        )


@client.app.on_message(filters.command("skip"))
@admin_only
async def skip_music(c, message: Message):
    chat_id = message.chat.id
    queue = await _get_queue(chat_id)

    if not queue:
        return await message.reply_text(
            "ℹ️ The music queue is empty."
        )

    queue.pop(0)
    await _save_queue(chat_id, queue)

    if queue:
        await _play_next(chat_id)

        await message.reply_text(
            f"⏭️ Skipped.\n"
            f"▶️ Now playing: **{queue[0]['title']}**"
        )
    else:
        try:
            await CALLS.leave_group_call(chat_id)
        except Exception:
            pass

        await message.reply_text(
            "⏹️ Queue finished."
        )


@client.app.on_message(filters.command("stop"))
@admin_only
async def stop_music(c, message: Message):
    chat_id = message.chat.id

    await _clear_queue(chat_id)

    try:
        await CALLS.leave_group_call(chat_id)
    except Exception:
        pass

    await message.reply_text(
        "⏹️ Stopped music and cleared the queue."
    )


@client.app.on_message(filters.command("queue"))
async def show_queue(c, message: Message):
    queue = await _get_queue(message.chat.id)

    if not queue:
        return await message.reply_text(
            "📭 The music queue is empty."
        )

    text = "🎶 **Music Queue:**\n\n"

    for index, item in enumerate(queue, start=1):
        title = item.get("title", "Unknown title")

        if index == 1:
            text += f"▶️ `{index}.` **{title}**\n"
        else:
            text += f"`{index}.` {title}\n"

    await message.reply_text(text)
