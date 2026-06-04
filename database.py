import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import asyncio
from supabase import create_client, Client

# ========== إعدادات Supabase ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://xlaruzxqtbsqjqdbwbyb.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_gbt0EnA6iBYIm1b4TuKHXg_vQYhmPXm")

# ========== إنشاء عميل Supabase ==========
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ تم الاتصال بـ Supabase بنجاح")
except Exception as e:
    print(f"❌ فشل الاتصال بـ Supabase: {e}")
    supabase = None

# ========== دوال مساعدة ==========
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ========== دوال الحظر ==========
async def add_ban(user_id: int, chat_id: int, reason: str = None, banned_by: int = 0, expires_at=None):
    if not supabase: return
    data = {
        "user_id": user_id,
        "chat_id": chat_id,
        "reason": reason,
        "banned_by": banned_by or 0,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": now_iso()
    }
    await asyncio.get_event_loop().run_in_executor(None, lambda: supabase.table("bans").upsert(data).execute())

async def remove_ban(user_id: int, chat_id: int, performed_by: int = 0) -> bool:
    if not supabase: return False
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("bans").delete().eq("user_id", user_id).eq("chat_id", chat_id).execute()
    )
    return len(result.data) > 0

async def get_ban(user_id: int, chat_id: int) -> dict:
    if not supabase: return None
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("bans").select("*").eq("user_id", user_id).eq("chat_id", chat_id).execute()
    )
    return result.data[0] if result.data else None

async def get_ban_list(chat_id: int) -> list:
    if not supabase: return []
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("bans").select("*").eq("chat_id", chat_id).execute()
    )
    return result.data

async def get_expired_bans() -> list:
    if not supabase: return []
    now = now_iso()
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("bans").select("*").lt("expires_at", now).execute()
    )
    return result.data

# ========== دوال التحذيرات ==========
async def add_warning(user_id: int, chat_id: int) -> int:
    if not supabase: return 0
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("warnings").select("count").eq("user_id", user_id).eq("chat_id", chat_id).execute()
    )
    count = result.data[0]["count"] if result.data else 0
    new_count = count + 1
    data = {"user_id": user_id, "chat_id": chat_id, "count": new_count}
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("warnings").upsert(data).execute()
    )
    return new_count

async def get_warnings(user_id: int, chat_id: int) -> int:
    if not supabase: return 0
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("warnings").select("count").eq("user_id", user_id).eq("chat_id", chat_id).execute()
    )
    return result.data[0]["count"] if result.data else 0

async def clear_warnings(user_id: int, chat_id: int):
    if not supabase: return
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("warnings").delete().eq("user_id", user_id).eq("chat_id", chat_id).execute()
    )

# ========== دوال الكلمات المحظورة ==========
async def add_banned_word(chat_id: int, word: str) -> bool:
    if not supabase: return False
    try:
        data = {"chat_id": chat_id, "word": word.lower()}
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("banned_words").insert(data).execute()
        )
        return True
    except:
        return False

async def remove_banned_word(chat_id: int, word: str) -> bool:
    if not supabase: return False
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("banned_words").delete().eq("chat_id", chat_id).eq("word", word.lower()).execute()
    )
    return len(result.data) > 0

async def get_banned_words(chat_id: int) -> list:
    if not supabase: return []
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("banned_words").select("word").eq("chat_id", chat_id).execute()
    )
    return [row["word"] for row in result.data]

# ========== دوال الإعدادات ==========
async def get_setting(chat_id: int, key: str) -> Optional[str]:
    if not supabase: return None
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("settings").select("value").eq("chat_id", chat_id).eq("key", key).execute()
    )
    return result.data[0]["value"] if result.data else None

async def set_setting(chat_id: int, key: str, value: str):
    if not supabase: return
    data = {"chat_id": chat_id, "key": key, "value": value}
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("settings").upsert(data).execute()
    )

# ========== دوال إحصائيات المستخدمين ==========
async def increment_message_count(user_id: int, chat_id: int, full_name: str = ""):
    if not supabase: return
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("user_stats").select("message_count").eq("user_id", user_id).eq("chat_id", chat_id).execute()
    )
    if result.data:
        new_count = result.data[0]["message_count"] + 1
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("user_stats").update({
                "message_count": new_count,
                "last_seen": now_iso(),
                "full_name": full_name
            }).eq("user_id", user_id).eq("chat_id", chat_id).execute()
        )
    else:
        data = {
            "user_id": user_id, "chat_id": chat_id, "message_count": 1,
            "first_seen": now_iso(), "last_seen": now_iso(), "full_name": full_name
        }
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("user_stats").insert(data).execute()
        )

async def get_message_count(user_id: int, chat_id: int) -> int:
    if not supabase: return 0
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("user_stats").select("message_count").eq("user_id", user_id).eq("chat_id", chat_id).execute()
    )
    return result.data[0]["message_count"] if result.data else 0

async def get_user_first_seen(user_id: int, chat_id: int) -> Optional[str]:
    if not supabase: return None
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("user_stats").select("first_seen").eq("user_id", user_id).eq("chat_id", chat_id).execute()
    )
    return result.data[0]["first_seen"] if result.data else None

async def get_user_last_seen(user_id: int, chat_id: int) -> Optional[str]:
    if not supabase: return None
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("user_stats").select("last_seen").eq("user_id", user_id).eq("chat_id", chat_id).execute()
    )
    return result.data[0]["last_seen"] if result.data else None

async def get_all_active_chats() -> list:
    if not supabase: return []
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("user_stats").select("chat_id").execute()
    )
    return list(set(row["chat_id"] for row in result.data))

async def get_total_members(chat_id: int) -> int:
    if not supabase: return 0
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("user_stats").select("user_id").eq("chat_id", chat_id).execute()
    )
    return len(result.data)

async def get_top_members(chat_id: int, limit: int = 5) -> list:
    if not supabase: return []
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("user_stats").select("user_id, full_name, message_count").eq("chat_id", chat_id).order("message_count", desc=True).limit(limit).execute()
    )
    return result.data

async def get_user_name(chat_id: int, user_id: int) -> str:
    if not supabase: return str(user_id)
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("user_stats").select("full_name").eq("chat_id", chat_id).eq("user_id", user_id).execute()
    )
    return result.data[0]["full_name"] if result.data else str(user_id)

async def save_chat_name(chat_id: int, chat_name: str):
    await set_setting(chat_id, "chat_name", chat_name)

async def get_chat_name(chat_id: int) -> str:
    return await get_setting(chat_id, "chat_name") or str(chat_id)

# ========== دوال سجل الأحداث ==========
async def log_event(chat_id: int, event_type: str, user_id: int = 0, target_id: int = 0, detail: str = None):
    if not supabase: return
    data = {
        "chat_id": chat_id, "action": event_type,
        "user_id": user_id or 0, "target_id": target_id or 0,
        "detail": detail, "created_at": now_iso()
    }
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("ban_log").insert(data).execute()
    )

async def get_event_log(chat_id: int, limit: int = 10) -> list:
    if not supabase: return []
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("ban_log").select("action, created_at, user_id, target_id, detail").eq("chat_id", chat_id).order("created_at", desc=True).limit(limit).execute()
    )
    return result.data

async def log_bot_action(chat_id: int, action: str, user_id: int = 0, detail: str = None):
    if not supabase: return
    data = {
        "chat_id": chat_id, "action": action,
        "user_id": user_id or 0, "detail": detail,
        "created_at": now_iso()
    }
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("bot_actions").insert(data).execute()
    )

async def get_bot_actions_since(chat_id: int, since: str) -> list:
    if not supabase: return []
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("bot_actions").select("*").eq("chat_id", chat_id).gte("created_at", since).order("created_at", desc=True).execute()
    )
    return result.data

# ========== دوال الأقفال ==========
async def set_lock(chat_id: int, lock_type: str, locked: bool):
    if not supabase: return
    data = {
        "chat_id": chat_id, "lock_type": lock_type,
        "is_locked": locked, "updated_at": now_iso()
    }
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("group_locks").upsert(data).execute()
    )

async def is_locked(chat_id: int, lock_type: str) -> bool:
    if not supabase: return False
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("group_locks").select("is_locked").eq("chat_id", chat_id).eq("lock_type", lock_type).execute()
    )
    return result.data[0]["is_locked"] if result.data else False

# ========== دوال نظام "صارحني" ==========

async def create_anonymous_link(user_id: int) -> str:
    if not supabase: return ""
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("anon_links").delete().eq("user_id", user_id).execute()
    )
    link_id = str(uuid.uuid4())[:8]
    data = {"link_id": link_id, "user_id": user_id, "created_at": now_iso()}
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("anon_links").insert(data).execute()
    )
    return link_id

async def get_user_by_link(link_id: str) -> Optional[int]:
    if not supabase: return None
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("anon_links").select("user_id").eq("link_id", link_id).execute()
    )
    return result.data[0]["user_id"] if result.data else None

async def save_anonymous_message(link_id: str, message: str, sender_id: int = 0):
    if not supabase: return
    data = {
        "link_id": link_id, "message": message,
        "sender_id": sender_id, "created_at": now_iso()
    }
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("anon_messages").insert(data).execute()
    )

async def get_anonymous_messages(user_id: int, mark_read: bool = True) -> list:
    if not supabase: return []
    result_links = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("anon_links").select("link_id").eq("user_id", user_id).execute()
    )
    link_ids = [row["link_id"] for row in result_links.data]
    if not link_ids:
        return []
    result_msgs = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table("anon_messages").select("*").in_("link_id", link_ids).order("created_at", desc=True).execute()
    )
    if mark_read:
        for msg in result_msgs.data:
            if not msg["is_read"]:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: supabase.table("anon_messages").update({"is_read": True}).eq("id", msg["id"]).execute()
                )
    return result_msgs.data

# ========== دوال المستخدمين النشطين ==========
async def update_user_activity(user_id: int, chat_id: int):
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if not supabase:
        return
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("user_activity").upsert({
                "user_id": user_id,
                "chat_id": chat_id,
                "last_active_month": current_month
            }).execute()
        )
    except Exception as e:
        print(f"خطأ في update_user_activity: {e}")

async def count_active_users() -> int:
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if not supabase:
        return 0
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("user_activity").select("user_id").eq("last_active_month", current_month).execute()
        )
        unique_users = set(row["user_id"] for row in result.data)
        return len(unique_users)
    except Exception as e:
        print(f"خطأ في count_active_users: {e}")
        return 0

# ==================== دوال نظام الأزمات ====================

async def add_crisis_word(chat_id: int, word: str) -> bool:
    if not supabase:
        return False
    try:
        existing = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("crisis_words").select("word").eq("chat_id", chat_id).eq("word", word).execute()
        )
        if existing.data:
            return False
        
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("crisis_words").insert({
                "chat_id": chat_id,
                "word": word,
                "created_at": now_iso()
            }).execute()
        )
        return True
    except Exception as e:
        print(f"Error adding crisis word: {e}")
        return False

async def remove_crisis_word(chat_id: int, word: str) -> bool:
    if not supabase:
        return False
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("crisis_words").delete().eq("chat_id", chat_id).eq("word", word).execute()
        )
        return len(result.data) > 0
    except Exception as e:
        print(f"Error removing crisis word: {e}")
        return False

async def get_crisis_words(chat_id: int) -> list:
    if not supabase:
        return []
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("crisis_words").select("word").eq("chat_id", chat_id).execute()
        )
        return result.data
    except Exception as e:
        print(f"Error getting crisis words: {e}")
        return []

async def get_crisis_words_count(chat_id: int) -> int:
    words = await get_crisis_words(chat_id)
    return len(words)

async def set_crisis_reply(chat_id: int, reply_text: str) -> bool:
    if not supabase:
        return False
    try:
        existing = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("crisis_settings").select("chat_id").eq("chat_id", chat_id).execute()
        )
        if existing.data:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: supabase.table("crisis_settings").update({"reply_text": reply_text, "updated_at": now_iso()}).eq("chat_id", chat_id).execute()
            )
        else:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: supabase.table("crisis_settings").insert({
                    "chat_id": chat_id,
                    "reply_text": reply_text,
                    "enabled": False,
                    "updated_at": now_iso()
                }).execute()
            )
        return True
    except Exception as e:
        print(f"Error setting crisis reply: {e}")
        return False

async def get_crisis_reply(chat_id: int) -> str:
    if not supabase:
        return ""
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("crisis_settings").select("reply_text").eq("chat_id", chat_id).execute()
        )
        if result.data:
            return result.data[0].get("reply_text", "")
        return ""
    except Exception as e:
        print(f"Error getting crisis reply: {e}")
        return ""

async def set_crisis_enabled(chat_id: int, enabled: bool) -> bool:
    if not supabase:
        return False
    try:
        existing = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("crisis_settings").select("chat_id").eq("chat_id", chat_id).execute()
        )
        if existing.data:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: supabase.table("crisis_settings").update({"enabled": enabled, "updated_at": now_iso()}).eq("chat_id", chat_id).execute()
            )
        else:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: supabase.table("crisis_settings").insert({
                    "chat_id": chat_id,
                    "enabled": enabled,
                    "reply_text": "",
                    "updated_at": now_iso()
                }).execute()
            )
        return True
    except Exception as e:
        print(f"Error setting crisis enabled: {e}")
        return False

async def get_crisis_enabled(chat_id: int) -> bool:
    if not supabase:
        return False
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("crisis_settings").select("enabled").eq("chat_id", chat_id).execute()
        )
        if result.data:
            return result.data[0].get("enabled", False)
        return False
    except Exception as e:
        print(f"Error getting crisis enabled: {e}")
        return False

async def log_crisis_alert(chat_id: int, word: str, user_id: int):
    if not supabase:
        return
    try:
        data = {
            "chat_id": chat_id,
            "action": "crisis_alert",
            "user_id": user_id,
            "detail": f"word:{word}",
            "created_at": now_iso()
        }
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("ban_log").insert(data).execute()
        )
    except Exception as e:
        print(f"Error logging crisis alert: {e}")

# ==================== دوال الردود التلقائية ====================

async def add_custom_reply(chat_id: int, keyword: str, reply: str) -> bool:
    if not supabase:
        return False
    try:
        existing = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("custom_replies").select("keyword").eq("chat_id", chat_id).eq("keyword", keyword).execute()
        )
        if existing.data:
            return False
        
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("custom_replies").insert({
                "chat_id": chat_id,
                "keyword": keyword,
                "reply": reply,
                "created_at": now_iso()
            }).execute()
        )
        return True
    except Exception as e:
        print(f"Error adding custom reply: {e}")
        return False

async def remove_custom_reply(chat_id: int, keyword: str) -> bool:
    if not supabase:
        return False
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("custom_replies").delete().eq("chat_id", chat_id).eq("keyword", keyword).execute()
        )
        return len(result.data) > 0
    except Exception as e:
        print(f"Error removing custom reply: {e}")
        return False

async def get_custom_replies(chat_id: int) -> dict:
    if not supabase:
        return {}
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("custom_replies").select("keyword, reply").eq("chat_id", chat_id).execute()
        )
        return {row["keyword"]: row["reply"] for row in result.data}
    except Exception as e:
        print(f"Error getting custom replies: {e}")
        return {}

# ==================== دوال الاختصارات ====================

async def add_custom_command(chat_id: int, shortcut: str, target_command: str) -> bool:
    if not supabase:
        return False
    try:
        existing = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("custom_commands").select("shortcut").eq("chat_id", chat_id).eq("shortcut", shortcut).execute()
        )
        if existing.data:
            return False
        
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("custom_commands").insert({
                "chat_id": chat_id,
                "shortcut": shortcut,
                "target_command": target_command,
                "created_at": now_iso()
            }).execute()
        )
        return True
    except Exception as e:
        print(f"Error adding custom command: {e}")
        return False

async def remove_custom_command(chat_id: int, shortcut: str) -> bool:
    if not supabase:
        return False
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("custom_commands").delete().eq("chat_id", chat_id).eq("shortcut", shortcut).execute()
        )
        return len(result.data) > 0
    except Exception as e:
        print(f"Error removing custom command: {e}")
        return False

async def get_custom_commands(chat_id: int) -> dict:
    if not supabase:
        return {}
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("custom_commands").select("shortcut, target_command").eq("chat_id", chat_id).execute()
        )
        return {row["shortcut"]: row["target_command"] for row in result.data}
    except Exception as e:
        print(f"Error getting custom commands: {e}")
        return {}

# ==================== دوال الهمسات ====================

async def save_whisper_link(whisper_id: str, sender_id: int, sender_name: str, target_id: int, target_name: str, chat_id: int, chat_title: str) -> bool:
    if not supabase:
        return False
    try:
        data = {
            "id": whisper_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "target_id": target_id,
            "target_name": target_name,
            "chat_id": chat_id,
            "chat_title": chat_title,
            "used": False,
            "created_at": now_iso()
        }
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("whisper_links").insert(data).execute()
        )
        return True
    except Exception as e:
        print(f"Error saving whisper link: {e}")
        return False

async def get_whisper_link(whisper_id: str) -> dict:
    if not supabase:
        return None
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("whisper_links").select("*").eq("id", whisper_id).eq("used", False).execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error getting whisper link: {e}")
        return None

async def delete_whisper_link(whisper_id: str) -> bool:
    if not supabase:
        return False
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("whisper_links").update({"used": True}).eq("id", whisper_id).execute()
        )
        return True
    except Exception as e:
        print(f"Error deleting whisper link: {e}")
        return False

# ==================== دوال سجل المستخدمين ====================

async def log_user_action(user_id: int, chat_id: int, action_type: str, action_by: int = 0, by_name: str = "", reason: str = None, duration: str = None):
    """تسجيل أي إجراء ضد عضو (تحذير، حظر، كتم، تقرير)"""
    if not supabase:
        return
    try:
        data = {
            "user_id": user_id,
            "chat_id": chat_id,
            "action_type": action_type,
            "action_by": action_by,
            "by_name": by_name,
            "reason": reason,
            "duration": duration,
            "created_at": now_iso()
        }
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("user_actions").insert(data).execute()
        )
    except Exception as e:
        print(f"Error logging user action: {e}")

async def get_user_actions(user_id: int, chat_id: int, limit: int = 50) -> list:
    if not supabase:
        return []
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("user_actions")
            .select("*")
            .eq("user_id", user_id)
            .eq("chat_id", chat_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
    except Exception as e:
        print(f"Error getting user actions: {e}")
        return []

async def clear_all_bans(chat_id: int):
    if not supabase:
        return
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("bans").delete().eq("chat_id", chat_id).execute()
        )
    except Exception as e:
        print(f"Error clearing bans: {e}")

async def clear_all_mutes(chat_id: int):
    if not supabase:
        return
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("user_actions").delete().eq("chat_id", chat_id).eq("action_type", "mute").execute()
        )
    except Exception as e:
        print(f"Error clearing mutes: {e}")

# ==================== دوال التذكيرات ====================

async def save_reminder(user_id: int, chat_id: int, reminder_time: str, reminder_text: str):
    """حفظ تذكير يومي في قاعدة البيانات"""
    if not supabase:
        return False
    try:
        # حذف التذكير القديم إذا موجود
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("reminders").delete().eq("user_id", user_id).eq("chat_id", chat_id).execute()
        )
        # إضافة التذكير الجديد
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("reminders").insert({
                "user_id": user_id,
                "chat_id": chat_id,
                "reminder_time": reminder_time,
                "reminder_text": reminder_text
            }).execute()
        )
        return True
    except Exception as e:
        print(f"خطأ في حفظ التذكير: {e}")
        return False

async def delete_reminder(user_id: int, chat_id: int):
    """حذف تذكير يومي من قاعدة البيانات"""
    if not supabase:
        return False
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("reminders").delete().eq("user_id", user_id).eq("chat_id", chat_id).execute()
        )
        return True
    except Exception as e:
        print(f"خطأ في حذف التذكير: {e}")
        return False

async def load_all_reminders():
    """تحميل جميع التذكيرات اليومية من قاعدة البيانات"""
    if not supabase:
        return []
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table("reminders").select("*").execute()
        )
        return result.data if result.data else []
    except Exception as e:
        print(f"خطأ في تحميل التذكيرات: {e}")
        return []

# ========== تهيئة قاعدة البيانات ==========
async def init_db():
    if supabase:
        print("✅ Supabase جاهز للعمل")
    else:
        print("❌ فشل الاتصال بـ Supabase")