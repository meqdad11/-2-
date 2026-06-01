import httpx
import json
import os
from datetime import datetime, timezone
from typing import Optional

# ========== المتغيرات العامة (GITHUB_TOKEN, GIST_ID) ==========
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GIST_ID = os.environ.get("GIST_ID", "")

# ========== إعدادات رؤوس الطلبات (HEADERS) ==========
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# ========== هيكل التخزين المؤقت (_cache) ==========
_cache = {
    "bans": {},
    "warnings": {},
    "banned_words": {},
    "settings": {},
    "user_stats": {},
    "ban_log": [],
    "bot_actions": [],
}

# ========== دالة غير متزامنة: _load_from_gist ==========
async def _load_from_gist():
    if not GIST_ID:
        return
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"https://api.github.com/gists/{GIST_ID}",
                headers=HEADERS
            )
            if r.status_code == 200:
                files = r.json().get("files", {})
                for key in _cache:
                    if f"{key}.json" in files:
                        content = files[f"{key}.json"]["content"]
                        _cache[key] = json.loads(content)
    except Exception as e:
        pass


# ========== دالة غير متزامنة: _save_to_gist ==========
async def _save_to_gist():
    global GIST_ID
    try:
        files = {}
        for key in _cache:
            files[f"{key}.json"] = {
                "content": json.dumps(_cache[key], ensure_ascii=False, default=str)
            }
        async with httpx.AsyncClient() as client:
            if GIST_ID:
                await client.patch(
                    f"https://api.github.com/gists/{GIST_ID}",
                    headers=HEADERS,
                    json={"files": files}
                )
            else:
                r = await client.post(
                    "https://api.github.com/gists",
                    headers=HEADERS,
                    json={
                        "description": "Bot Database",
                        "public": False,
                        "files": files
                    }
                )
                if r.status_code == 201:
                    GIST_ID = r.json()["id"]
                    os.environ["GIST_ID"] = GIST_ID
    except Exception as e:
        pass


# ========== دالة غير متزامنة: init_db ==========
async def init_db():
    await _load_from_gist()
    if not GIST_ID:
        await _save_to_gist()


# ========== دالة غير متزامنة: add_ban ==========
async def add_ban(user_id: int, chat_id: int, reason: str = None,
                  banned_by: int = 0, expires_at=None):
    key = f"{user_id}_{chat_id}"
    _cache["bans"][key] = {
        "user_id": user_id, "chat_id": chat_id,
        "reason": reason, "banned_by": banned_by or 0,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await _save_to_gist()


# ========== دالة غير متزامنة: remove_ban ==========
async def remove_ban(user_id: int, chat_id: int, performed_by: int = 0) -> bool:
    key = f"{user_id}_{chat_id}"
    if key in _cache["bans"]:
        del _cache["bans"][key]
        await _save_to_gist()
        return True
    return False


# ========== دالة غير متزامنة: get_ban ==========
async def get_ban(user_id: int, chat_id: int) -> dict:
    return _cache["bans"].get(f"{user_id}_{chat_id}")


# ========== دالة غير متزامنة: get_ban_list ==========
async def get_ban_list(chat_id: int) -> list:
    return [b for b in _cache["bans"].values() if b["chat_id"] == chat_id]


# ========== دالة غير متزامنة: get_expired_bans ==========
async def get_expired_bans() -> list:
    now = datetime.now(timezone.utc)
    expired = []
    for b in _cache["bans"].values():
        if b.get("expires_at"):
            try:
                exp = datetime.fromisoformat(b["expires_at"])
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp <= now:
                    expired.append(b)
            except Exception:
                pass
    return expired


# ========== دالة غير متزامنة: add_warning ==========
async def add_warning(user_id: int, chat_id: int) -> int:
    key = f"{user_id}_{chat_id}"
    current = _cache["warnings"].get(key, {"count": 0})
    current["count"] = current.get("count", 0) + 1
    current["user_id"] = user_id
    current["chat_id"] = chat_id
    _cache["warnings"][key] = current
    await _save_to_gist()
    return current["count"]


# ========== دالة غير متزامنة: get_warnings ==========
async def get_warnings(user_id: int, chat_id: int) -> int:
    key = f"{user_id}_{chat_id}"
    return _cache["warnings"].get(key, {}).get("count", 0)


# ========== دالة غير متزامنة: clear_warnings ==========
async def clear_warnings(user_id: int, chat_id: int):
    key = f"{user_id}_{chat_id}"
    if key in _cache["warnings"]:
        del _cache["warnings"][key]
        await _save_to_gist()


# ========== دالة غير متزامنة: log_event ==========
async def log_event(chat_id: int, event_type: str,
                    user_id: int = 0, target_id: int = 0, detail: str = None):
    _cache["ban_log"].append({
        "chat_id": chat_id, "action": event_type,
        "user_id": user_id or 0, "target_id": target_id or 0,
        "detail": detail,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    if len(_cache["ban_log"]) > 100:
        _cache["ban_log"] = _cache["ban_log"][-100:]


# ========== دالة غير متزامنة: log_bot_action ==========
async def log_bot_action(chat_id: int, action: str,
                         user_id: int = 0, detail: str = None):
    _cache["bot_actions"].append({
        "chat_id": chat_id, "action": action,
        "user_id": user_id or 0, "detail": detail,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    if len(_cache["bot_actions"]) > 200:
        _cache["bot_actions"] = _cache["bot_actions"][-200:]
    await _save_to_gist()


# ========== دالة غير متزامنة: get_event_log ==========
async def get_event_log(chat_id: int, limit: int = 10) -> list:
    logs = [e for e in _cache["ban_log"] if e["chat_id"] == chat_id]
    return sorted(logs, key=lambda x: x["created_at"], reverse=True)[:limit]


# ========== دالة غير متزامنة: get_bot_actions_since ==========
async def get_bot_actions_since(chat_id: int, since: str) -> list:
    actions = [a for a in _cache["bot_actions"]
               if a["chat_id"] == chat_id and a["created_at"] >= since]
    return sorted(actions, key=lambda x: x["created_at"], reverse=True)


# ========== دالة غير متزامنة: get_new_members_since ==========
async def get_new_members_since(chat_id: int, since: str) -> int:
    return sum(1 for s in _cache["user_stats"].values()
               if s["chat_id"] == chat_id and s.get("first_seen", "") >= since)


# ========== دالة غير متزامنة: get_total_members ==========
async def get_total_members(chat_id: int) -> int:
    return sum(1 for s in _cache["user_stats"].values()
               if s["chat_id"] == chat_id)


# ========== دالة غير متزامنة: get_top_members ==========
async def get_top_members(chat_id: int, limit: int = 5) -> list:
    members = [s for s in _cache["user_stats"].values() if s["chat_id"] == chat_id]
    return sorted(members, key=lambda x: x.get("message_count", 0), reverse=True)[:limit]


# ========== دالة غير متزامنة: increment_message_count ==========
async def increment_message_count(user_id: int, chat_id: int, full_name: str = ""):
    key = f"{user_id}_{chat_id}"
    if key not in _cache["user_stats"]:
        _cache["user_stats"][key] = {
            "user_id": user_id, "chat_id": chat_id,
            "message_count": 0,
            "first_seen": datetime.now(timezone.utc).isoformat()
        }
    _cache["user_stats"][key]["message_count"] += 1
    _cache["user_stats"][key]["last_seen"] = datetime.now(timezone.utc).isoformat()
    skey = f"{chat_id}_username_{user_id}"
    _cache["settings"][skey] = {"chat_id": chat_id, "key": f"username_{user_id}", "value": full_name}


# ========== دالة غير متزامنة: get_user_name ==========
async def get_user_name(chat_id: int, user_id: int) -> str:
    skey = f"{chat_id}_username_{user_id}"
    return _cache["settings"].get(skey, {}).get("value", str(user_id))


# ========== دالة غير متزامنة: get_message_count ==========
async def get_message_count(user_id: int, chat_id: int) -> int:
    return _cache["user_stats"].get(f"{user_id}_{chat_id}", {}).get("message_count", 0)


# ========== دالة غير متزامنة: get_user_first_seen ==========
async def get_user_first_seen(user_id: int, chat_id: int) -> Optional[str]:
    return _cache["user_stats"].get(f"{user_id}_{chat_id}", {}).get("first_seen")


# ========== دالة غير متزامنة: add_banned_word ==========
async def add_banned_word(chat_id: int, word: str) -> bool:
    key = f"{chat_id}_{word.lower()}"
    if key in _cache["banned_words"]:
        return False
    _cache["banned_words"][key] = {"chat_id": chat_id, "word": word.lower()}
    await _save_to_gist()
    return True


# ========== دالة غير متزامنة: remove_banned_word ==========
async def remove_banned_word(chat_id: int, word: str) -> bool:
    key = f"{chat_id}_{word.lower()}"
    if key in _cache["banned_words"]:
        del _cache["banned_words"][key]
        await _save_to_gist()
        return True
    return False


# ========== دالة غير متزامنة: get_banned_words ==========
async def get_banned_words(chat_id: int) -> list:
    return [v["word"] for v in _cache["banned_words"].values() if v["chat_id"] == chat_id]


# ========== دالة غير متزامنة: get_setting ==========
async def get_setting(chat_id: int, key: str) -> Optional[str]:
    skey = f"{chat_id}_{key}"
    return _cache["settings"].get(skey, {}).get("value")


# ========== دالة غير متزامنة: set_setting ==========
async def set_setting(chat_id: int, key: str, value: str):
    skey = f"{chat_id}_{key}"
    _cache["settings"][skey] = {"chat_id": chat_id, "key": key, "value": value}
    await _save_to_gist()


# ========== دالة غير متزامنة: get_all_active_chats ==========
async def get_all_active_chats() -> list:
    return list(set(s["chat_id"] for s in _cache["user_stats"].values()))


# ========== دالة غير متزامنة: save_chat_name ==========
async def save_chat_name(chat_id: int, chat_name: str):
    await set_setting(chat_id, "chat_name", chat_name)


# ========== دالة غير متزامنة: get_chat_name ==========
async def get_chat_name(chat_id: int) -> str:
    return await get_setting(chat_id, "chat_name") or str(chat_id)