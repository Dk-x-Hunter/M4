from pyrogram import Client, filters
from pyrogram.types import Message

HELP_TEXT = """
**🎵 Music Bot Commands**

**Playback:**
/play <song/link> — play or queue
/pause — pause
/resume — resume
/skip — skip
/queue — show queue
/stop — stop and leave VC

**Sudo/Admin:**
/authorize — authorize this group
/unauthorize — revoke this group
/addsudo <user_id> — add sudo
/rmsudo <user_id> — remove sudo
/sudolist — list sudo users

**Owner:**
/promote <message> — broadcast to authorized groups
/promote_gc <chat_id> <message> — send to one chat
/promote_media — broadcast replied media
/schedulepromo <HH:MM> <message> — schedule promotion
/stats — bot statistics

/leaderboard — listener points
"""


@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(_, message: Message):
    await message.reply_text("👋 Hi! I'm a voice-chat music bot.\n\nSend /help for commands.")


@Client.on_message(filters.command("help"))
async def help_cmd(_, message: Message):
    await message.reply_text(HELP_TEXT)
