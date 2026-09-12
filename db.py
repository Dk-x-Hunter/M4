import sqlite3
import threading
import json
from datetime import datetime, timezone
from typing import Iterable, List, Dict, Optional

import config

_LOCK = threading.RLock()


def _connect():
    conn = sqlite3.connect(config.DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with _LOCK, _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sudo_users (
                user_id INTEGER PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS authorized_chats (
                chat_id INTEGER PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS promotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                message TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scheduled_promotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS music_queues (
                chat_id INTEGER PRIMARY KEY,
                queue TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.executemany(
            "INSERT OR IGNORE INTO sudo_users(user_id) VALUES (?)",
            [(uid,) for uid in set(config.SUDO_USERS + [config.OWNER_ID]) if uid],
        )


def _now():
    return datetime.now(timezone.utc).isoformat()


def get_db():
    with _LOCK, _connect() as conn:
        sudo = [r[0] for r in conn.execute("SELECT user_id FROM sudo_users ORDER BY user_id")]
        chats = [r[0] for r in conn.execute("SELECT chat_id FROM authorized_chats ORDER BY chat_id")]
        scheduled = [dict(r) for r in conn.execute("SELECT id, run_at, message FROM scheduled_promotions ORDER BY run_at")]
        return {"sudo_users": sudo, "authorized_chats": chats, "scheduled_promotions": scheduled}


def is_sudo(user_id: int) -> bool:
    with _LOCK, _connect() as conn:
        return conn.execute("SELECT 1 FROM sudo_users WHERE user_id=?", (user_id,)).fetchone() is not None


def add_sudo(user_id: int):
    with _LOCK, _connect() as conn:
        conn.execute("INSERT OR IGNORE INTO sudo_users(user_id) VALUES (?)", (user_id,))


def remove_sudo(user_id: int):
    if user_id == config.OWNER_ID:
        return
    with _LOCK, _connect() as conn:
        conn.execute("DELETE FROM sudo_users WHERE user_id=?", (user_id,))


def authorize_chat(chat_id: int):
    with _LOCK, _connect() as conn:
        conn.execute("INSERT OR IGNORE INTO authorized_chats(chat_id) VALUES (?)", (chat_id,))


def unauthorize_chat(chat_id: int):
    with _LOCK, _connect() as conn:
        conn.execute("DELETE FROM authorized_chats WHERE chat_id=?", (chat_id,))


def is_authorized_chat(chat_id: int) -> bool:
    with _LOCK, _connect() as conn:
        return conn.execute("SELECT 1 FROM authorized_chats WHERE chat_id=?", (chat_id,)).fetchone() is not None


def record_song(chat_id=None, user_id=None, title=None):
    if not title:
        return
    with _LOCK, _connect() as conn:
        conn.execute(
            "INSERT INTO songs(chat_id,user_id,title,created_at) VALUES (?,?,?,?)",
            (chat_id, user_id, title, _now()),
        )


def record_promotion(chat_ids: Iterable[int], message_text: str):
    with _LOCK, _connect() as conn:
        conn.executemany(
            "INSERT INTO promotions(chat_id,message,sent,created_at) VALUES (?,?,1,?)",
            [(chat_id, message_text, _now()) for chat_id in chat_ids],
        )


def record_targeted_promotion(chat_id: int, message_text: str, sent: bool):
    with _LOCK, _connect() as conn:
        conn.execute(
            "INSERT INTO promotions(chat_id,message,sent,created_at) VALUES (?,?,?,?)",
            (chat_id, message_text, int(sent), _now()),
        )


def add_scheduled_promotion(run_at: str, message: str) -> int:
    with _LOCK, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO scheduled_promotions(run_at,message,created_at) VALUES (?,?,?)",
            (run_at, message, _now()),
        )
        return int(cur.lastrowid)


def get_due_promotions(now_iso: str):
    with _LOCK, _connect() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, run_at, message FROM scheduled_promotions WHERE run_at<=? ORDER BY run_at",
            (now_iso,),
        )]
        if rows:
            conn.executemany("DELETE FROM scheduled_promotions WHERE id=?", [(r["id"],) for r in rows])
        return rows


def get_leaderboard(limit=10):
    with _LOCK, _connect() as conn:
        return [tuple(r) for r in conn.execute(
            "SELECT user_id, COUNT(*) AS points FROM songs WHERE user_id IS NOT NULL GROUP BY user_id ORDER BY points DESC LIMIT ?",
            (limit,),
        )]


def get_stats():
    with _LOCK, _connect() as conn:
        active = conn.execute("SELECT COUNT(*) FROM authorized_chats").fetchone()[0]
        songs = conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
        promotions = conn.execute("SELECT COUNT(*) FROM promotions").fetchone()[0]
        top = [tuple(r) for r in conn.execute(
            "SELECT title, COUNT(*) AS count FROM songs GROUP BY title ORDER BY count DESC LIMIT 5"
        )]
        active_chat = conn.execute(
            "SELECT chat_id, COUNT(*) AS count FROM songs WHERE chat_id IS NOT NULL GROUP BY chat_id ORDER BY count DESC LIMIT 1"
        ).fetchone()
        return {
            "active_chats": active,
            "songs": songs,
            "promotions": promotions,
            "top_songs": top,
            "most_active_chat": tuple(active_chat) if active_chat else None,
        }


# --------------------------------------------------
# Music Queue Methods
# --------------------------------------------------

async def get_queue(chat_id: int) -> Optional[List[Dict]]:
    """Get the music queue for a chat."""
    with _LOCK, _connect() as conn:
        row = conn.execute(
            "SELECT queue FROM music_queues WHERE chat_id=?",
            (chat_id,),
        ).fetchone()
        
        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return []
        return None


async def set_queue(chat_id: int, queue: List[Dict]) -> None:
    """Save or update the music queue for a chat."""
    queue_json = json.dumps(queue)
    with _LOCK, _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO music_queues(chat_id, queue, updated_at) VALUES (?, ?, ?)",
            (chat_id, queue_json, _now()),
        )


async def clear_queue(chat_id: int) -> None:
    """Clear the music queue for a chat."""
    with _LOCK, _connect() as conn:
        conn.execute(
            "DELETE FROM music_queues WHERE chat_id=?",
            (chat_id,),
        )
