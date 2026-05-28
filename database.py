import asyncpg
import os
from datetime import datetime, timezone
from typing import Optional

DATABASE_URL = os.environ.get("DATABASE_URL")


async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bans (
                user_id    BIGINT NOT NULL,
                chat_id    BIGINT NOT NULL,
                reason     TEXT,
                banned_by  BIGINT DEFAULT 0,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ban_log (
                id           SERIAL PRIMARY KEY,
                user_id      BIGINT DEFAULT 0,
                chat_id      BIGINT,
                action       TEXT,
                performed_by BIGINT DEFAULT 0,
                target_id    BIGINT DEFAULT 0,
                detail       TEXT,
                created_at   TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                user_id BIGINT NOT NULL,
                chat_id BIGINT NOT NULL,
                count   INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id       BIGINT NOT NULL,
                chat_id       BIGINT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                first_seen    TIMESTAMP DEFAULT NOW(),
                last_seen     TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS banned_words (
                chat_id BIGINT NOT NULL,
                word    TEXT NOT NULL,
                PRIMARY KEY (chat_id, word)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                chat_id BIGINT NOT NULL,
                key     TEXT NOT NULL,
                value   TEXT,
                PRIMARY KEY (chat_id, key)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_actions (
                id         SERIAL PRIMARY KEY,
                chat_id    BIGINT,
                action     TEXT,
                user_id    BIGINT DEFAULT 0,
                detail     TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
    finally:
        await conn.close()
async def add_ban(user_id: int, chat_id: int, reason: str = None,
                  banned_by: int = 0, expires_at=None):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""
            INSERT INTO bans (user_id, chat_id, reason, banned_by, expires_at)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, chat_id) DO UPDATE SET
                reason=EXCLUDED.reason, banned_by=EXCLUDED.banned_by,
                expires_at=EXCLUDED.expires_at
        """, user_id, chat_id, reason, banned_by or 0, expires_at)
    finally:
        await conn.close()


async def remove_ban(user_id: int, chat_id: int, performed_by: int = 0) -> bool:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        result = await conn.execute(
            "DELETE FROM bans WHERE user_id=$1 AND chat_id=$2",
            user_id, chat_id
        )
        return result != "DELETE 0"
    finally:
        await conn.close()


async def get_ban(user_id: int, chat_id: int) -> dict:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "SELECT * FROM bans WHERE user_id=$1 AND chat_id=$2",
            user_id, chat_id
        )
        return dict(row) if row else None
    finally:
        await conn.close()


async def get_ban_list(chat_id: int) -> list:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(
            "SELECT * FROM bans WHERE chat_id=$1 ORDER BY created_at DESC",
            chat_id
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_expired_bans() -> list:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        now = datetime.now(timezone.utc)
        rows = await conn.fetch(
            "SELECT * FROM bans WHERE expires_at IS NOT NULL AND expires_at <= $1",
            now
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def add_warning(user_id: int, chat_id: int) -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""
            INSERT INTO warnings (user_id, chat_id, count) VALUES ($1, $2, 1)
            ON CONFLICT (user_id, chat_id) DO UPDATE SET count = warnings.count + 1
        """, user_id, chat_id)
        row = await conn.fetchrow(
            "SELECT count FROM warnings WHERE user_id=$1 AND chat_id=$2",
            user_id, chat_id
        )
        return row["count"] if row else 1
    finally:
        await conn.close()


async def get_warnings(user_id: int, chat_id: int) -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "SELECT count FROM warnings WHERE user_id=$1 AND chat_id=$2",
            user_id, chat_id
        )
        return row["count"] if row else 0
    finally:
        await conn.close()


async def clear_warnings(user_id: int, chat_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(
            "DELETE FROM warnings WHERE user_id=$1 AND chat_id=$2",
            user_id, chat_id
        )
    finally:
        await conn.close()
async def log_event(chat_id: int, event_type: str,
                    user_id: int = 0, target_id: int = 0, detail: str = None):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""
            INSERT INTO ban_log (chat_id, action, user_id, target_id, detail)
            VALUES ($1, $2, $3, $4, $5)
        """, chat_id, event_type, user_id or 0, target_id or 0, detail)
    finally:
        await conn.close()


async def log_bot_action(chat_id: int, action: str,
                         user_id: int = 0, detail: str = None):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""
            INSERT INTO bot_actions (chat_id, action, user_id, detail)
            VALUES ($1, $2, $3, $4)
        """, chat_id, action, user_id or 0, detail)
    finally:
        await conn.close()


async def get_event_log(chat_id: int, limit: int = 10) -> list:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch("""
            SELECT * FROM ban_log WHERE chat_id=$1
            ORDER BY created_at DESC LIMIT $2
        """, chat_id, limit)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_bot_actions_since(chat_id: int, since: str) -> list:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch("""
            SELECT * FROM bot_actions
            WHERE chat_id=$1 AND created_at >= $2
            ORDER BY created_at DESC
        """, chat_id, since)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_new_members_since(chat_id: int, since: str) -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow("""
            SELECT COUNT(*) as cnt FROM user_stats
            WHERE chat_id=$1 AND first_seen >= $2
        """, chat_id, since)
        return row["cnt"] if row else 0
    finally:
        await conn.close()


async def get_total_members(chat_id: int) -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "SELECT COUNT(*) as cnt FROM user_stats WHERE chat_id=$1",
            chat_id
        )
        return row["cnt"] if row else 0
    finally:
        await conn.close()


async def get_top_members(chat_id: int, limit: int = 5) -> list:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch("""
            SELECT user_id, message_count FROM user_stats
            WHERE chat_id=$1
            ORDER BY message_count DESC LIMIT $2
        """, chat_id, limit)
        return [dict(r) for r in rows]
    finally:
        await conn.close()
async def increment_message_count(user_id: int, chat_id: int, full_name: str = ""):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""
            INSERT INTO user_stats (user_id, chat_id, message_count, last_seen)
            VALUES ($1, $2, 1, NOW())
            ON CONFLICT (user_id, chat_id) DO UPDATE SET
                message_count = user_stats.message_count + 1,
                last_seen = NOW()
        """, user_id, chat_id)
        await conn.execute("""
            INSERT INTO settings (chat_id, key, value) VALUES ($1, $2, $3)
            ON CONFLICT (chat_id, key) DO UPDATE SET value=EXCLUDED.value
        """, chat_id, f"username_{user_id}", full_name)
    finally:
        await conn.close()


async def get_user_name(chat_id: int, user_id: int) -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "SELECT value FROM settings WHERE chat_id=$1 AND key=$2",
            chat_id, f"username_{user_id}"
        )
        return row["value"] if row else str(user_id)
    finally:
        await conn.close()


async def get_message_count(user_id: int, chat_id: int) -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "SELECT message_count FROM user_stats WHERE user_id=$1 AND chat_id=$2",
            user_id, chat_id
        )
        return row["message_count"] if row else 0
    finally:
        await conn.close()


async def get_user_first_seen(user_id: int, chat_id: int) -> Optional[str]:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "SELECT first_seen FROM user_stats WHERE user_id=$1 AND chat_id=$2",
            user_id, chat_id
        )
        return str(row["first_seen"]) if row else None
    finally:
        await conn.close()


async def add_banned_word(chat_id: int, word: str) -> bool:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(
            "INSERT INTO banned_words (chat_id, word) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            chat_id, word.lower()
        )
        return True
    except Exception:
        return False
    finally:
        await conn.close()


async def remove_banned_word(chat_id: int, word: str) -> bool:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        result = await conn.execute(
            "DELETE FROM banned_words WHERE chat_id=$1 AND word=$2",
            chat_id, word.lower()
        )
        return result != "DELETE 0"
    finally:
        await conn.close()


async def get_banned_words(chat_id: int) -> list:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(
            "SELECT word FROM banned_words WHERE chat_id=$1 ORDER BY word",
            chat_id
        )
        return [r["word"] for r in rows]
    finally:
        await conn.close()


async def get_setting(chat_id: int, key: str) -> Optional[str]:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "SELECT value FROM settings WHERE chat_id=$1 AND key=$2",
            chat_id, key
        )
        return row["value"] if row else None
    finally:
        await conn.close()


async def set_setting(chat_id: int, key: str, value: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""
            INSERT INTO settings (chat_id, key, value) VALUES ($1, $2, $3)
            ON CONFLICT (chat_id, key) DO UPDATE SET value=EXCLUDED.value
        """, chat_id, key, value)
    finally:
        await conn.close()


async def get_all_active_chats() -> list:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch("SELECT DISTINCT chat_id FROM user_stats")
        return [r["chat_id"] for r in rows]
    finally:
        await conn.close()


async def save_chat_name(chat_id: int, chat_name: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""
            INSERT INTO settings (chat_id, key, value) VALUES ($1, 'chat_name', $2)
            ON CONFLICT (chat_id, key) DO UPDATE SET value=EXCLUDED.value
        """, chat_id, chat_name)
    finally:
        await conn.close()


async def get_chat_name(chat_id: int) -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "SELECT value FROM settings WHERE chat_id=$1 AND key='chat_name'",
            chat_id
        )
        return row["value"] if row else str(chat_id)
    finally:
        await conn.close()