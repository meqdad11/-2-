import httpx
import os
from datetime import datetime, timezone
from typing import Optional

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}


def url(table: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table}"


async def init_db():
    pass


async def add_ban(user_id: int, chat_id: int, reason: str = None,
                  banned_by: int = 0, expires_at=None):
    async with httpx.AsyncClient() as client:
        await client.post(url("bans"), headers={**HEADERS, "Prefer": "resolution=merge-duplicates"}, json={
            "user_id": user_id, "chat_id": chat_id,
            "reason": reason, "banned_by": banned_by or 0,
            "expires_at": expires_at.isoformat() if expires_at else None
        })


async def remove_ban(user_id: int, chat_id: int, performed_by: int = 0) -> bool:
    async with httpx.AsyncClient() as client:
        r = await client.delete(
            url("bans"),
            headers=HEADERS,
            params={"user_id": f"eq.{user_id}", "chat_id": f"eq.{chat_id}"}
        )
        return r.status_code == 204


async def get_ban(user_id: int, chat_id: int) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("bans"),
            headers=HEADERS,
            params={"user_id": f"eq.{user_id}", "chat_id": f"eq.{chat_id}"}
        )
        data = r.json()
        return data[0] if data else None


async def get_ban_list(chat_id: int) -> list:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("bans"),
            headers=HEADERS,
            params={"chat_id": f"eq.{chat_id}", "order": "created_at.desc"}
        )
        return r.json() if r.status_code == 200 else []


async def get_expired_bans() -> list:
    now = datetime.now(timezone.utc).isoformat()
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("bans"),
            headers=HEADERS,
            params={"expires_at": f"lte.{now}", "expires_at": "not.is.null"}
        )
        return r.json() if r.status_code == 200 else []
async def add_warning(user_id: int, chat_id: int) -> int:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("warnings"),
            headers=HEADERS,
            params={"user_id": f"eq.{user_id}", "chat_id": f"eq.{chat_id}"}
        )
        data = r.json()
        if data:
            count = data[0]["count"] + 1
            await client.patch(
                url("warnings"),
                headers=HEADERS,
                params={"user_id": f"eq.{user_id}", "chat_id": f"eq.{chat_id}"},
                json={"count": count}
            )
        else:
            count = 1
            await client.post(url("warnings"), headers=HEADERS,
                              json={"user_id": user_id, "chat_id": chat_id, "count": 1})
        return count


async def get_warnings(user_id: int, chat_id: int) -> int:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("warnings"),
            headers=HEADERS,
            params={"user_id": f"eq.{user_id}", "chat_id": f"eq.{chat_id}"}
        )
        data = r.json()
        return data[0]["count"] if data else 0


async def clear_warnings(user_id: int, chat_id: int):
    async with httpx.AsyncClient() as client:
        await client.delete(
            url("warnings"),
            headers=HEADERS,
            params={"user_id": f"eq.{user_id}", "chat_id": f"eq.{chat_id}"}
        )


async def log_event(chat_id: int, event_type: str,
                    user_id: int = 0, target_id: int = 0, detail: str = None):
    async with httpx.AsyncClient() as client:
        await client.post(url("ban_log"), headers=HEADERS, json={
            "chat_id": chat_id, "action": event_type,
            "user_id": user_id or 0, "target_id": target_id or 0,
            "detail": detail
        })


async def log_bot_action(chat_id: int, action: str,
                         user_id: int = 0, detail: str = None):
    async with httpx.AsyncClient() as client:
        await client.post(url("bot_actions"), headers=HEADERS, json={
            "chat_id": chat_id, "action": action,
            "user_id": user_id or 0, "detail": detail
        })


async def get_event_log(chat_id: int, limit: int = 10) -> list:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("ban_log"),
            headers=HEADERS,
            params={"chat_id": f"eq.{chat_id}", "order": "created_at.desc", "limit": limit}
        )
        return r.json() if r.status_code == 200 else []


async def get_bot_actions_since(chat_id: int, since: str) -> list:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("bot_actions"),
            headers=HEADERS,
            params={"chat_id": f"eq.{chat_id}", "created_at": f"gte.{since}",
                    "order": "created_at.desc"}
        )
        return r.json() if r.status_code == 200 else []
async def get_new_members_since(chat_id: int, since: str) -> int:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("user_stats"),
            headers={**HEADERS, "Prefer": "count=exact"},
            params={"chat_id": f"eq.{chat_id}", "first_seen": f"gte.{since}"}
        )
        return int(r.headers.get("content-range", "0/0").split("/")[-1])


async def get_total_members(chat_id: int) -> int:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("user_stats"),
            headers={**HEADERS, "Prefer": "count=exact"},
            params={"chat_id": f"eq.{chat_id}"}
        )
        return int(r.headers.get("content-range", "0/0").split("/")[-1])


async def get_top_members(chat_id: int, limit: int = 5) -> list:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("user_stats"),
            headers=HEADERS,
            params={"chat_id": f"eq.{chat_id}", "order": "message_count.desc", "limit": limit}
        )
        return r.json() if r.status_code == 200 else []


async def increment_message_count(user_id: int, chat_id: int, full_name: str = ""):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("user_stats"),
            headers=HEADERS,
            params={"user_id": f"eq.{user_id}", "chat_id": f"eq.{chat_id}"}
        )
        data = r.json()
        if data:
            await client.patch(
                url("user_stats"),
                headers=HEADERS,
                params={"user_id": f"eq.{user_id}", "chat_id": f"eq.{chat_id}"},
                json={"message_count": data[0]["message_count"] + 1,
                      "last_seen": datetime.now(timezone.utc).isoformat()}
            )
        else:
            await client.post(url("user_stats"), headers=HEADERS, json={
                "user_id": user_id, "chat_id": chat_id, "message_count": 1
            })
        await client.post(
            url("settings"),
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
            json={"chat_id": chat_id, "key": f"username_{user_id}", "value": full_name}
        )


async def get_user_name(chat_id: int, user_id: int) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("settings"),
            headers=HEADERS,
            params={"chat_id": f"eq.{chat_id}", "key": f"eq.username_{user_id}"}
        )
        data = r.json()
        return data[0]["value"] if data else str(user_id)


async def get_message_count(user_id: int, chat_id: int) -> int:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("user_stats"),
            headers=HEADERS,
            params={"user_id": f"eq.{user_id}", "chat_id": f"eq.{chat_id}"}
        )
        data = r.json()
        return data[0]["message_count"] if data else 0


async def get_user_first_seen(user_id: int, chat_id: int) -> Optional[str]:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("user_stats"),
            headers=HEADERS,
            params={"user_id": f"eq.{user_id}", "chat_id": f"eq.{chat_id}"}
        )
        data = r.json()
        return str(data[0]["first_seen"]) if data else None
async def add_banned_word(chat_id: int, word: str) -> bool:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            url("banned_words"),
            headers={**HEADERS, "Prefer": "resolution=ignore-duplicates"},
            json={"chat_id": chat_id, "word": word.lower()}
        )
        return r.status_code in (200, 201)


async def remove_banned_word(chat_id: int, word: str) -> bool:
    async with httpx.AsyncClient() as client:
        r = await client.delete(
            url("banned_words"),
            headers=HEADERS,
            params={"chat_id": f"eq.{chat_id}", "word": f"eq.{word.lower()}"}
        )
        return r.status_code == 204


async def get_banned_words(chat_id: int) -> list:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("banned_words"),
            headers=HEADERS,
            params={"chat_id": f"eq.{chat_id}", "order": "word"}
        )
        return [row["word"] for row in r.json()] if r.status_code == 200 else []


async def get_setting(chat_id: int, key: str) -> Optional[str]:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("settings"),
            headers=HEADERS,
            params={"chat_id": f"eq.{chat_id}", "key": f"eq.{key}"}
        )
        data = r.json()
        return data[0]["value"] if data else None


async def set_setting(chat_id: int, key: str, value: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            url("settings"),
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
            json={"chat_id": chat_id, "key": key, "value": value}
        )


async def get_all_active_chats() -> list:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("user_stats"),
            headers=HEADERS,
            params={"select": "chat_id"}
        )
        data = r.json() if r.status_code == 200 else []
        return list(set(row["chat_id"] for row in data))


async def save_chat_name(chat_id: int, chat_name: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            url("settings"),
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
            json={"chat_id": chat_id, "key": "chat_name", "value": chat_name}
        )


async def get_chat_name(chat_id: int) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url("settings"),
            headers=HEADERS,
            params={"chat_id": f"eq.{chat_id}", "key": "eq.chat_name"}
        )
        data = r.json()
        return data[0]["value"] if data else str(chat_id)