# DK Music Bot 
 Telegram Voice-Chat Music Bot

A single-instance Telegram music bot using Pyrogram + PyTgCalls. The clone system was removed to keep the project simpler and safer.

## Features

- `/play <song or URL>`
- Queue management
- Automatic next-track playback when PyTgCalls emits a stream-end event
- `/pause`, `/resume`, `/skip`, `/stop`, `/queue`
- Owner/sudo access control
- Group authorization
- Promotions to authorized groups
- Media promotions
- Persistent scheduled promotions using SQLite
- Listener leaderboard and statistics

## Setup

1. Install Python and FFmpeg where required by your playback environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and set your values, or export the variables in your shell.
4. Generate a user session if needed:

```bash
python generate_session.py
```

5. Start:

```bash
python bot.py
```

The bot account should be added to the group with the permissions needed by your setup. The `SESSION_STRING` belongs to a normal Telegram user account used by PyTgCalls for voice-chat playback.

## Important

Never commit `.env`, `SESSION_STRING`, bot tokens, or `.session` files. The project uses `data.db` for persistent state; SQLite is safer than sharing a JSON file between processes.

## Commands

### Playback
`/play`, `/pause`, `/resume`, `/skip`, `/queue`, `/stop`

### Sudo
`/authorize`, `/unauthorize`, `/addsudo`, `/rmsudo`, `/sudolist`

### Owner
`/promote`, `/promote_gc`, `/promote_media`, `/schedulepromo`, `/stats`

### Public
`/start`, `/help`, `/leaderboard`
