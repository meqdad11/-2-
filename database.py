import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import asyncio
from contextlib import contextmanager

# ========== مسار قاعدة البيانات ==========
DB_PATH = os.environ.get("DATABASE_PATH", "bot_data.db")

# ========== دبورات مساعدة للتعامل مع SQLite ==========
def get_connection():
    """إنشاء اتصال بقاعدة البيانات مع Row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_tables():
    """إنشاء الجداول إذا لم تكن موجودة"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # جدول الحظر
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bans (
                user_id INTEGER,
                chat_id INTEGER,
                reason TEXT,
                banned_by INTEGER,
                expires_at TEXT,
                created_at TEXT,
                PRIMARY KEY (user_id, chat_id)
            )
        ''')
        
        # جدول التحذيرات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warnings (
                user_id INTEGER,
                chat_id INTEGER,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, chat_id)
            )
        ''')
        
        # جدول الكلمات المحظورة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS banned_words (
                chat_id INTEGER,
                word TEXT,
                PRIMARY KEY (chat_id, word)
            )
        ''')
        
        # جدول الإعدادات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                chat_id INTEGER,
                key TEXT,
                value TEXT,
                PRIMARY KEY (chat_id, key)
            )
        ''')
        
        # جدول إحصائيات المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER,
                chat_id INTEGER,
                message_count INTEGER DEFAULT 0,
                first_seen TEXT,
                last_seen TEXT,
                full_name TEXT,
                PRIMARY KEY (user_id, chat_id)
            )
        ''')
        
        # جدول سجل الأحداث
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ban_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                action TEXT,
                user_id INTEGER,
                target_id INTEGER,
                detail TEXT,
                created_at TEXT
            )
        ''')
        
        # جدول سجل إجراءات البوت
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                action TEXT,
                user_id INTEGER,
                detail TEXT,
                created_at TEXT
            )
        ''')
        
        # جدول الأقفال
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_locks (
                chat_id INTEGER,
                lock_type TEXT,
                is_locked INTEGER DEFAULT 0,
                updated_at TEXT,
                PRIMARY KEY (chat_id, lock_type)
            )
        ''')
        
        # جدول روابط صارحني
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anon_links (
                link_id TEXT PRIMARY KEY,
                user_id INTEGER,
                created_at TEXT
            )
        ''')
        
        # جدول رسائل صارحني
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anon_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_id TEXT,
                message TEXT,
                sender_id INTEGER,
                created_at TEXT,
                is_read INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()

# ========== تهيئة قاعدة البيانات ==========
async def init_db():
    """تهيئة قاعدة البيانات (إنشاء الجداول في أول تشغيل)"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, init_tables)

# ========== دوال الحظر ==========
async def add_ban(user_id: int, chat_id: int, reason: str = None, banned_by: int = 0, expires_at=None):
    def _add():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO bans (user_id, chat_id, reason, banned_by, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, chat_id, reason, banned_by, expires_at.isoformat() if expires_at else None,
                  datetime.now(timezone.utc).isoformat()))
            conn.commit()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _add)

async def remove_ban(user_id: int, chat_id: int, performed_by: int = 0) -> bool:
    def _remove():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM bans WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
            return cursor.rowcount > 0
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _remove)

async def get_ban(user_id: int, chat_id: int) -> dict:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM bans WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
            row = cursor.fetchone()
            return dict(row) if row else None
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

async def get_ban_list(chat_id: int) -> list:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM bans WHERE chat_id = ?', (chat_id,))
            return [dict(row) for row in cursor.fetchall()]
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

async def get_expired_bans() -> list:
    now = datetime.now(timezone.utc).isoformat()
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM bans WHERE expires_at IS NOT NULL AND expires_at <= ?', (now,))
            return [dict(row) for row in cursor.fetchall()]
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

# ========== دوال التحذيرات ==========
async def add_warning(user_id: int, chat_id: int) -> int:
    def _add():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO warnings (user_id, chat_id, count) VALUES (?, ?, 1)
                ON CONFLICT(user_id, chat_id) DO UPDATE SET count = count + 1
                RETURNING count
            ''', (user_id, chat_id))
            row = cursor.fetchone()
            return row['count'] if row else 1
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _add)

async def get_warnings(user_id: int, chat_id: int) -> int:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT count FROM warnings WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
            row = cursor.fetchone()
            return row['count'] if row else 0
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

async def clear_warnings(user_id: int, chat_id: int):
    def _clear():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM warnings WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
            conn.commit()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _clear)

# ========== دوال الكلمات المحظورة ==========
async def add_banned_word(chat_id: int, word: str) -> bool:
    def _add():
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('INSERT INTO banned_words (chat_id, word) VALUES (?, ?)', (chat_id, word.lower()))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _add)

async def remove_banned_word(chat_id: int, word: str) -> bool:
    def _remove():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM banned_words WHERE chat_id = ? AND word = ?', (chat_id, word.lower()))
            return cursor.rowcount > 0
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _remove)

async def get_banned_words(chat_id: int) -> list:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT word FROM banned_words WHERE chat_id = ?', (chat_id,))
            return [row['word'] for row in cursor.fetchall()]
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

# ========== دوال الإعدادات ==========
async def get_setting(chat_id: int, key: str) -> Optional[str]:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE chat_id = ? AND key = ?', (chat_id, key))
            row = cursor.fetchone()
            return row['value'] if row else None
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

async def set_setting(chat_id: int, key: str, value: str):
    def _set():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, ?, ?)
            ''', (chat_id, key, value))
            conn.commit()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _set)

# ========== دوال إحصائيات المستخدمين ==========
async def increment_message_count(user_id: int, chat_id: int, full_name: str = ""):
    def _inc():
        with get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            # التحقق إذا كان المستخدم موجوداً
            cursor.execute('SELECT * FROM user_stats WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
            row = cursor.fetchone()
            if row:
                cursor.execute('''
                    UPDATE user_stats SET message_count = message_count + 1, last_seen = ?, full_name = ?
                    WHERE user_id = ? AND chat_id = ?
                ''', (now, full_name, user_id, chat_id))
            else:
                cursor.execute('''
                    INSERT INTO user_stats (user_id, chat_id, message_count, first_seen, last_seen, full_name)
                    VALUES (?, ?, 1, ?, ?, ?)
                ''', (user_id, chat_id, now, now, full_name))
            conn.commit()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _inc)

async def get_message_count(user_id: int, chat_id: int) -> int:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT message_count FROM user_stats WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
            row = cursor.fetchone()
            return row['message_count'] if row else 0
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

async def get_user_first_seen(user_id: int, chat_id: int) -> Optional[str]:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT first_seen FROM user_stats WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
            row = cursor.fetchone()
            return row['first_seen'] if row else None
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

async def get_all_active_chats() -> list:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT chat_id FROM user_stats')
            return [row['chat_id'] for row in cursor.fetchall()]
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

async def get_total_members(chat_id: int) -> int:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM user_stats WHERE chat_id = ?', (chat_id,))
            row = cursor.fetchone()
            return row['count'] if row else 0
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

async def get_top_members(chat_id: int, limit: int = 5) -> list:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, full_name, message_count FROM user_stats 
                WHERE chat_id = ? ORDER BY message_count DESC LIMIT ?
            ''', (chat_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

async def get_user_name(chat_id: int, user_id: int) -> str:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT full_name FROM user_stats WHERE chat_id = ? AND user_id = ?', (chat_id, user_id))
            row = cursor.fetchone()
            return row['full_name'] if row else str(user_id)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

async def save_chat_name(chat_id: int, chat_name: str):
    await set_setting(chat_id, "chat_name", chat_name)

async def get_chat_name(chat_id: int) -> str:
    return await get_setting(chat_id, "chat_name") or str(chat_id)

# ========== دوال سجل الأحداث ==========
async def log_event(chat_id: int, event_type: str, user_id: int = 0, target_id: int = 0, detail: str = None):
    def _log():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ban_log (chat_id, action, user_id, target_id, detail, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (chat_id, event_type, user_id or 0, target_id or 0, detail,
                  datetime.now(timezone.utc).isoformat()))
            # حذف السجلات القديمة (تبقي آخر 100)
            cursor.execute('''
                DELETE FROM ban_log WHERE id NOT IN (
                    SELECT id FROM ban_log WHERE chat_id = ? ORDER BY created_at DESC LIMIT 100
                )
            ''', (chat_id,))
            conn.commit()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _log)

async def get_event_log(chat_id: int, limit: int = 10) -> list:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT action, created_at FROM ban_log 
                WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?
            ''', (chat_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

async def log_bot_action(chat_id: int, action: str, user_id: int = 0, detail: str = None):
    def _log():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO bot_actions (chat_id, action, user_id, detail, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (chat_id, action, user_id or 0, detail, datetime.now(timezone.utc).isoformat()))
            conn.commit()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _log)

async def get_bot_actions_since(chat_id: int, since: str) -> list:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT action, detail, created_at FROM bot_actions 
                WHERE chat_id = ? AND created_at >= ? ORDER BY created_at DESC
            ''', (chat_id, since))
            return [dict(row) for row in cursor.fetchall()]
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

# ========== دوال الأقفال ==========
async def set_lock(chat_id: int, lock_type: str, locked: bool):
    def _set():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO group_locks (chat_id, lock_type, is_locked, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (chat_id, lock_type, 1 if locked else 0, datetime.now(timezone.utc).isoformat()))
            conn.commit()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _set)

async def is_locked(chat_id: int, lock_type: str) -> bool:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_locked FROM group_locks WHERE chat_id = ? AND lock_type = ?', (chat_id, lock_type))
            row = cursor.fetchone()
            return bool(row['is_locked']) if row else False
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

# ========== دوال نظام "صارحني" ==========
import uuid

async def create_anonymous_link(user_id: int) -> str:
    def _create():
        with get_connection() as conn:
            cursor = conn.cursor()
            # حذف الرابط القديم للمستخدم
            cursor.execute('DELETE FROM anon_links WHERE user_id = ?', (user_id,))
            link_id = str(uuid.uuid4())[:8]
            cursor.execute('''
                INSERT INTO anon_links (link_id, user_id, created_at)
                VALUES (?, ?, ?)
            ''', (link_id, user_id, datetime.now(timezone.utc).isoformat()))
            conn.commit()
            return link_id
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _create)

async def get_user_by_link(link_id: str) -> Optional[int]:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM anon_links WHERE link_id = ?', (link_id,))
            row = cursor.fetchone()
            return row['user_id'] if row else None
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

async def save_anonymous_message(link_id: str, message: str, sender_id: int = 0):
    def _save():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO anon_messages (link_id, message, sender_id, created_at)
                VALUES (?, ?, ?, ?)
            ''', (link_id, message, sender_id, datetime.now(timezone.utc).isoformat()))
            conn.commit()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _save)

async def get_anonymous_messages(user_id: int, mark_read: bool = True) -> list:
    def _get():
        with get_connection() as conn:
            cursor = conn.cursor()
            # الحصول على جميع link_ids للمستخدم
            cursor.execute('SELECT link_id FROM anon_links WHERE user_id = ?', (user_id,))
            links = [row['link_id'] for row in cursor.fetchall()]
            if not links:
                return []
            placeholders = ','.join('?' for _ in links)
            cursor.execute(f'''
                SELECT message, created_at, is_read FROM anon_messages 
                WHERE link_id IN ({placeholders}) ORDER BY created_at DESC
            ''', links)
            messages = [dict(row) for row in cursor.fetchall()]
            if mark_read:
                cursor.execute(f'''
                    UPDATE anon_messages SET is_read = 1 
                    WHERE link_id IN ({placeholders}) AND is_read = 0
                ''', links)
                conn.commit()
            return messages
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)