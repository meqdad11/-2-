from fastapi import FastAPI, Request, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from utils import database as db
import uvicorn
import threading
import logging
import os
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Shafaq Bot Dashboard")
templates = Jinja2Templates(directory="templates")

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")
SESSION_TOKEN = "shafaq_session"

def is_authenticated(session: str = None) -> bool:
    return session == DASHBOARD_PASSWORD and DASHBOARD_PASSWORD != ""

# ==================== صفحة تسجيل الدخول ====================
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    return HTMLResponse(f"""
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <title>شفق — تسجيل الدخول</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: Arial, sans-serif; background: #12121f; color: #e0e0e0;
                display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
        .card {{ background: #1e1e30; border-radius: 16px; padding: 32px; width: 100%; max-width: 340px; }}
        h1 {{ font-size: 1.3em; color: #ffb347; margin-bottom: 24px; text-align: center; }}
        input {{ width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #333;
                 background: #12121f; color: #fff; font-size: 1em; margin-bottom: 16px; }}
        button {{ width: 100%; padding: 12px; border-radius: 8px; border: none;
                  background: #ffb347; color: #000; font-size: 1em; font-weight: bold; cursor: pointer; }}
        .error {{ color: #ff6666; font-size: 0.85em; margin-bottom: 12px; text-align: center; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>🌅 بوت شفق</h1>
        {"<div class='error'>❌ كلمة المرور خاطئة</div>" if error else ""}
        <form method="POST" action="/login">
            <input type="password" name="password" placeholder="كلمة المرور" autofocus>
            <button type="submit">دخول</button>
        </form>
    </div>
</body>
</html>
""")

@app.post("/login")
async def login(request: Request):
    form = await request.form()
    password = form.get("password", "")
    if password == DASHBOARD_PASSWORD:
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(SESSION_TOKEN, password, httponly=True, max_age=86400)
        return response
    return RedirectResponse(url="/login?error=1", status_code=302)

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(SESSION_TOKEN)
    return response

# ==================== الداشبورد الرئيسي ====================
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, shafaq_session: str = Cookie(default=None)):
    if not is_authenticated(shafaq_session):
        return RedirectResponse(url="/login", status_code=302)

    try:
        chats_list = await db.get_all_active_chats()
        chats = len(chats_list)

        users = 0
        for cid in chats_list:
            users += await db.get_total_members(int(cid))

        ban_list = []
        total_bans = 0
        for cid in chats_list:
            bans = await db.get_ban_list(int(cid))
            total_bans += len(bans)
            ban_list.extend(bans[:3])
        ban_list = ban_list[:15]

        total_warnings = 0

        active_locks = 0
        lock_types = ["links", "tags", "media", "files", "video", "voice", "gifs"]
        total_locks = len(chats_list[:5]) * len(lock_types)
        for cid in chats_list[:5]:
            for lock_type in lock_types:
                if await db.is_locked(int(cid), lock_type):
                    active_locks += 1
        lock_percent = int((active_locks / total_locks * 100)) if total_locks > 0 else 0

        reminders = await db.load_all_reminders()
        total_reminders = len(reminders)

        events = []
        for cid in chats_list[:5]:
            chat_events = await db.get_event_log(int(cid), limit=5)
            events.extend(chat_events)
        events = sorted(events, key=lambda x: x.get("created_at", ""), reverse=True)[:20]

        top_members = []
        for cid in chats_list[:3]:
            chat_name = await db.get_chat_name(int(cid))
            members = await db.get_top_members(int(cid), limit=3)
            for m in members:
                m["chat_name"] = chat_name
                top_members.append(m)
        top_members = sorted(top_members, key=lambda x: x.get("message_count", 0), reverse=True)[:10]

        crisis_data = []
        for cid in chats_list:
            chat_name = await db.get_chat_name(int(cid))
            enabled = await db.get_crisis_enabled(int(cid))
            words = await db.get_crisis_words(int(cid))
            crisis_data.append({
                "chat_id": cid,
                "chat_name": chat_name,
                "enabled": enabled,
                "word_count": len(words),
            })

        all_crisis_words = []
        for cid in chats_list:
            chat_name = await db.get_chat_name(int(cid))
            words_data = await db.get_crisis_words(int(cid))
            words = [w.get("word", "") for w in words_data if w.get("word")]
            if words:
                all_crisis_words.append({"chat_name": chat_name, "words": words})

        all_banned_words = []
        for cid in chats_list:
            chat_name = await db.get_chat_name(int(cid))
            words = await db.get_banned_words(int(cid))
            if words:
                all_banned_words.append({"chat_name": chat_name, "words": words})

        last_update = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        chats = users = active_locks = total_locks = total_bans = total_warnings = total_reminders = lock_percent = 0
        events = ban_list = top_members = crisis_data = all_crisis_words = all_banned_words = []
        last_update = "خطأ في جلب البيانات"

    context = {
        "request": request,
        "chats": chats,
        "users": users,
        "total_bans": total_bans,
        "total_warnings": total_warnings,
        "active_locks": active_locks,
        "total_locks": total_locks,
        "lock_percent": lock_percent,
        "total_reminders": total_reminders,
        "events": events,
        "ban_list": ban_list,
        "top_members": top_members,
        "crisis_data": crisis_data,
        "all_crisis_words": all_crisis_words,
        "all_banned_words": all_banned_words,
        "last_update": last_update,
    }
    return templates.TemplateResponse(request=request, name="dashboard.html", context=context)

# ==================== API أوامر التحكم ====================
@app.post("/api/crisis/toggle")
async def toggle_crisis(request: Request, shafaq_session: str = Cookie(default=None)):
    if not is_authenticated(shafaq_session):
        return {"error": "unauthorized"}
    data = await request.json()
    chat_id = data.get("chat_id")
    enabled = data.get("enabled")
    if not chat_id:
        return {"error": "missing chat_id"}
    await db.set_crisis_enabled(int(chat_id), bool(enabled))
    return {"success": True, "chat_id": chat_id, "enabled": enabled}

@app.post("/api/ban/remove")
async def remove_ban_api(request: Request, shafaq_session: str = Cookie(default=None)):
    if not is_authenticated(shafaq_session):
        return {"error": "unauthorized"}
    data = await request.json()
    user_id = data.get("user_id")
    chat_id = data.get("chat_id")
    if not user_id or not chat_id:
        return {"error": "missing data"}
    await db.remove_ban(int(user_id), int(chat_id))
    return {"success": True}

@app.post("/api/warnings/clear")
async def clear_warnings_api(request: Request, shafaq_session: str = Cookie(default=None)):
    if not is_authenticated(shafaq_session):
        return {"error": "unauthorized"}
    data = await request.json()
    user_id = data.get("user_id")
    chat_id = data.get("chat_id")
    if not user_id or not chat_id:
        return {"error": "missing data"}
    await db.clear_warnings(int(user_id), int(chat_id))
    return {"success": True}

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

def start_dashboard():
    threading.Thread(target=run_web, daemon=True).start()
    logger.info("✅ لوحة التحكم تعمل على البورت 8000")
