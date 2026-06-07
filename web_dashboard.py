from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from utils import database as db
import uvicorn
import threading
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Shafaq Bot Dashboard")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        chats_list = await db.get_all_active_chats()
        chats = len(chats_list)

        # المستخدمون الكلي
        users = 0
        for cid in chats_list:
            users += await db.get_total_members(int(cid))

        # المحظورون
        ban_list = []
        total_bans = 0
        for cid in chats_list:
            bans = await db.get_ban_list(int(cid))
            total_bans += len(bans)
            ban_list.extend(bans[:3])
        ban_list = ban_list[:15]

        # التحذيرات (نحسبها من أول 5 مجموعات)
        total_warnings = 0
        for cid in chats_list[:5]:
            top = await db.get_top_members(int(cid), limit=10)
            # نحاول نجيب التحذيرات
            pass

        # الأقفال
        active_locks = 0
        lock_types = ["links", "tags", "media", "files", "video", "voice", "gifs"]
        total_locks = len(chats_list[:5]) * len(lock_types)
        for cid in chats_list[:5]:
            for lock_type in lock_types:
                if await db.is_locked(int(cid), lock_type):
                    active_locks += 1
        lock_percent = int((active_locks / total_locks * 100)) if total_locks > 0 else 0

        # التذكيرات
        reminders = await db.load_all_reminders()
        total_reminders = len(reminders)

        # آخر الأحداث
        events = []
        for cid in chats_list[:5]:
            chat_events = await db.get_event_log(int(cid), limit=5)
            events.extend(chat_events)
        events = sorted(events, key=lambda x: x.get("created_at", ""), reverse=True)[:20]

        # أكثر المستخدمين نشاطاً
        top_members = []
        for cid in chats_list[:3]:
            chat_name = await db.get_chat_name(int(cid))
            members = await db.get_top_members(int(cid), limit=3)
            for m in members:
                m["chat_name"] = chat_name
                top_members.append(m)
        top_members = sorted(top_members, key=lambda x: x.get("message_count", 0), reverse=True)[:10]

        # نظام الأزمات
        crisis_data = []
        for cid in chats_list:
            chat_name = await db.get_chat_name(int(cid))
            enabled = await db.get_crisis_enabled(int(cid))
            words = await db.get_crisis_words(int(cid))
            crisis_data.append({
                "chat_name": chat_name,
                "enabled": enabled,
                "word_count": len(words),
            })

        # كلمات الأزمة
        all_crisis_words = []
        for cid in chats_list:
            chat_name = await db.get_chat_name(int(cid))
            words_data = await db.get_crisis_words(int(cid))
            words = [w.get("word", "") for w in words_data if w.get("word")]
            if words:
                all_crisis_words.append({"chat_name": chat_name, "words": words})

        # الكلمات المحظورة
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

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

def start_dashboard():
    threading.Thread(target=run_web, daemon=True).start()
    logger.info("✅ لوحة التحكم تعمل على البورت 8000")
