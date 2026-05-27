import aiosqlite
from datetime import datetime, timezone
from typing import Optional

DB_PATH = "bans.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bans (
                user_id    INTEGER NOT NULL,
                chat_id    INTEGER NOT NULL,
                reason     TEXT,
                banned_by  INTEGER,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ban_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER DEFAULT 0,
                chat_id      INTEGER,
                action       TEXT,
                performed_by INTEGER,
                target_id    INTEGER DEFAULT 0,
                detail       TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                count   INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, chat_id)
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                chat_id INTEGER NOT NULL,
                key     TEXT NOT NULL,
                value   TEXT,
                PRIMARY KEY (chat_id, key)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_actions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER,
                action     TEXT,
                user_id    INTEGER DEFAULT 0,
                detail     TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for col, typ in [("target_id", "INTEGER"), ("detail", "TEXT"), ("user_id", "INTEGER")]:
            try:
                await db.execute(f"ALTER TABLE ban_log ADD COLUMN {col} {typ} DEFAULT 0")
            except Exception:
                pass
        await db.commit()


async def add_ban(user_id: int, chat_id: int, reason: str = None,
                  banned_by: int = 0, expires_at=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO bans (user_id, chat_id, reason, banned_by, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, chat_id, reason, banned_by, expires_at))
        await db.commit()


async def remove_ban(user_id: int, chat_id: int, performed_by: int = 0) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM bans WHERE user_id=? AND chat_id=?",
            (user_id, chat_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_ban(user_id: int, chat_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bans WHERE user_id=? AND chat_id=?",
            (user_id, chat_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_ban_list(chat_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bans WHERE chat_id=? ORDER BY created_at DESC",
            (chat_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_expired_bans() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        now = datetime.now(timezone.utc).isoformat()
        cursor = await db.execute(
            "SELECT * FROM bans WHERE expires_at IS NOT NULL AND expires_at <= ?",
            (now,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def add_warning(user_id: int, chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO warnings (user_id, chat_id, count) VALUES (?, ?, 1)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET count = count + 1
        """, (user_id, chat_id))
        await db.commit()
        cursor = await db.execute(
            "SELECT count FROM warnings WHERE user_id=? AND chat_id=?",
            (user_id, chat_id)
        )
        row = await cursor.fetchone()
        return row[0] if row else 1


async def get_warnings(user_id: int, chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT count FROM warnings WHERE user_id=? AND chat_id=?",
            (user_id, chat_id)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def clear_warnings(user_id: int, chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM warnings WHERE user_id=? AND chat_id=?",
            (user_id, chat_id)
        )
        await db.commit()


async def log_event(chat_id: int, event_type: str,
                    user_id: int = 0, target_id: int = 0, detail: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO ban_log (chat_id, action, user_id, target_id, detail)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, event_type, user_id or 0, target_id or 0, detail))
        await db.commit()


async def log_bot_action(chat_id: int, action: str,
                         user_id: int = 0, detail: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO bot_actions (chat_id, action, user_id, detail)
            VALUES (?, ?, ?, ?)
        """, (chat_id, action, user_id or 0, detail))
        await db.commit()


async def get_event_log(chat_id: int, limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM ban_log WHERE chat_id=?
            ORDER BY created_at DESC LIMIT ?
        """, (chat_id, limit))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_bot_actions_since(chat_id: int, since: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM bot_actions
            WHERE chat_id=? AND created_at >= ?
            ORDER BY created_at DESC
        """, (chat_id, since))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_new_members_since(chat_id: int, since: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT COUNT(*) FROM user_stats
            WHERE chat_id=? AND first_seen >= ?
        """, (chat_id, since))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_total_members(chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM user_stats WHERE chat_id=?",
            (chat_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_top_members(chat_id: int, limit: int = 5) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT user_id, message_count FROM user_stats
            WHERE chat_id=?
            ORDER BY message_count DESC LIMIT ?
        """, (chat_id, limit))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def increment_message_count(user_id: int, chat_id: int, full_name: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_stats (user_id, chat_id, message_count, last_seen)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                message_count = message_count + 1,
                last_seen = CURRENT_TIMESTAMP
        """, (user_id, chat_id))
        await db.execute("""
            INSERT OR REPLACE INTO settings (chat_id, key, value)
            VALUES (?, ?, ?)
        """, (chat_id, f"username_{user_id}", full_name))
        await db.commit()


async def get_user_name(chat_id: int, user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM settings WHERE chat_id=? AND key=?",
            (chat_id, f"username_{user_id}")
        )
        row = await cursor.fetchone()
        return row[0] if row else str(user_id)


async def get_message_count(user_id: int, chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT message_count FROM user_stats WHERE user_id=? AND chat_id=?",
            (user_id, chat_id)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_user_first_seen(user_id: int, chat_id: int) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT first_seen FROM user_stats WHERE user_id=? AND chat_id=?",
            (user_id, chat_id)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


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


async def get_banned_words(chat_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT word FROM banned_words WHERE chat_id=? ORDER BY word",
            (chat_id,)
        )
        return [row[0] for row in await cursor.fetchall()]


async def get_setting(chat_id: int, key: str) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM settings WHERE chat_id=? AND key=?",
            (chat_id, key)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def set_setting(chat_id: int, key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO settings (chat_id, key, value)
            VALUES (?, ?, ?)
        """, (chat_id, key, value))
        await db.commit()


async def get_all_active_chats() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT DISTINCT chat_id FROM user_stats"
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def save_chat_name(chat_id: int, chat_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO settings (chat_id, key, value)
            VALUES (?, 'chat_name', ?)
        """, (chat_id, chat_name))
        await db.commit()


async def get_chat_name(chat_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM settings WHERE chat_id=? AND key='chat_name'",
            (chat_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else str(chat_id)
