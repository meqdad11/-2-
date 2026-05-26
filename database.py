import aiosqlite
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "bans.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id    INTEGER NOT NULL,
                chat_id    INTEGER NOT NULL,
                reason     TEXT,
                banned_by  INTEGER,
                expires_at TIMESTAMP,
                banned_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                user_id     INTEGER NOT NULL,
                chat_id     INTEGER NOT NULL,
                count       INTEGER NOT NULL DEFAULT 1,
                last_warned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS event_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                user_id    INTEGER,
                target_id  INTEGER,
                detail     TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER NOT NULL,
                key     TEXT NOT NULL,
                value   TEXT,
                PRIMARY KEY (chat_id, key)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id       INTEGER NOT NULL,
                chat_id       INTEGER NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                first_seen    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS banned_words (
                chat_id INTEGER NOT NULL,
                word    TEXT NOT NULL,
                PRIMARY KEY (chat_id, word)
            )
        """)
        await db.commit()

    await _migrate_banned_users()


async def _migrate_banned_users():
    """Add expires_at column if it doesn't exist (migration for existing DBs)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("PRAGMA table_info(banned_users)")
        cols = {row[1] for row in await cursor.fetchall()}
        if "expires_at" not in cols:
            await db.execute("ALTER TABLE banned_users ADD COLUMN expires_at TIMESTAMP")
            await db.commit()


# ── Ban management ─────────────────────────────────────────────────────────────

async def add_ban(
    user_id: int,
    chat_id: int,
    reason: str | None,
    banned_by: int,
    expires_at: datetime | None = None,
) -> bool:
    exp = expires_at.isoformat() if expires_at else None
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO banned_users (user_id, chat_id, reason, banned_by, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, chat_id, reason, banned_by, exp),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            await db.execute(
                "UPDATE banned_users SET reason=?, banned_by=?, expires_at=?, banned_at=CURRENT_TIMESTAMP "
                "WHERE user_id=? AND chat_id=?",
                (reason, banned_by, exp, user_id, chat_id),
            )
            await db.commit()
            return False


async def remove_ban(user_id: int, chat_id: int, performed_by: int | None = None) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM banned_users WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def is_banned(user_id: int, chat_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM banned_users WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        return await cursor.fetchone() is not None


async def get_ban_info(user_id: int, chat_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM banned_users WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_bans(chat_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM banned_users WHERE chat_id=? ORDER BY banned_at DESC",
            (chat_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]


async def increment_message_count(user_id: int, chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_stats (user_id, chat_id, message_count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, chat_id)
            DO UPDATE SET
                message_count = message_count + 1,
                last_seen = CURRENT_TIMESTAMP
        """, (user_id, chat_id))
        await db.commit()


async def get_message_count(user_id: int, chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT message_count FROM user_stats WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_user_first_seen(user_id: int, chat_id: int) -> str | None:
    """Return the first_seen timestamp string for a user in a chat, or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT first_seen FROM user_stats WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def get_expired_bans() -> list[dict]:
    """Return all bans whose expires_at is in the past."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM banned_users WHERE expires_at IS NOT NULL AND expires_at <= ?",
            (now,),
        )
        return [dict(r) for r in await cursor.fetchall()]


# ── Warning system ─────────────────────────────────────────────────────────────

async def add_warning(user_id: int, chat_id: int) -> int:
    """Increment warning count and return new total."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT count FROM warnings WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        row = await cursor.fetchone()
        if row:
            new_count = row[0] + 1
            await db.execute(
                "UPDATE warnings SET count=?, last_warned=CURRENT_TIMESTAMP "
                "WHERE user_id=? AND chat_id=?",
                (new_count, user_id, chat_id),
            )
        else:
            new_count = 1
            await db.execute(
                "INSERT INTO warnings (user_id, chat_id, count) VALUES (?, ?, 1)",
                (user_id, chat_id),
            )
        await db.commit()
        return new_count


async def get_warning_count(user_id: int, chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT count FROM warnings WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def clear_warnings(user_id: int, chat_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM warnings WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        await db.commit()
        return cursor.rowcount > 0


# ── Event log ──────────────────────────────────────────────────────────────────

async def log_event(
    chat_id: int,
    event_type: str,
    user_id: int | None = None,
    target_id: int | None = None,
    detail: str | None = None,
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO event_log (chat_id, event_type, user_id, target_id, detail) "
            "VALUES (?, ?, ?, ?, ?)",
            (chat_id, event_type, user_id, target_id, detail),
        )
        await db.commit()


async def get_event_log(chat_id: int, limit: int = 30, event_type: str | None = None) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if event_type:
            cursor = await db.execute(
                "SELECT * FROM event_log WHERE chat_id=? AND event_type=? "
                "ORDER BY created_at DESC LIMIT ?",
                (chat_id, event_type, limit),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM event_log WHERE chat_id=? ORDER BY created_at DESC LIMIT ?",
                (chat_id, limit),
            )
        return [dict(r) for r in await cursor.fetchall()]


# ── Chat settings ──────────────────────────────────────────────────────────────

async def add_banned_word(chat_id: int, word: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO banned_words (chat_id, word) VALUES (?, ?)",
                (chat_id, word.lower()),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_banned_word(chat_id: int, word: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM banned_words WHERE chat_id=? AND word=?",
            (chat_id, word.lower()),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_banned_words(chat_id: int) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT word FROM banned_words WHERE chat_id=? ORDER BY word",
            (chat_id,),
        )
        return [row[0] for row in await cursor.fetchall()]


async def get_setting(chat_id: int, key: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM chat_settings WHERE chat_id=? AND key=?",
            (chat_id, key),
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def set_setting(chat_id: int, key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO chat_settings (chat_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id, key) DO UPDATE SET value=excluded.value",
            (chat_id, key, value),
        )
        await db.commit()
        
