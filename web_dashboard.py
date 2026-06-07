from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from utils import database as db
import uvicorn
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Shafaq Bot Dashboard")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        # جلب الإحصائيات من Supabase مباشرة
        chats_list = await db.get_all_active_chats()
        chats = len(chats_list)

        # عدد المستخدمين الكلي
        users = 0
        for chat_id in chats_list:
            users += await db.get_total_members(chat_id)

        # آخر 20 حدث
        events = []
        for chat_id in chats_list[:5]:  # أول 5 مجموعات فقط لتجنب البطء
            chat_events = await db.get_event_log(chat_id, limit=5)
            events.extend(chat_events)
        events = sorted(events, key=lambda x: x.get("created_at", ""), reverse=True)[:20]

        # الأقفال
        active_locks = 0
        total_locks = 0
        for chat_id in chats_list[:5]:
            for lock_type in ["links", "tags", "media", "files", "video", "voice", "gifs"]:
                total_locks += 1
                if await db.is_locked(chat_id, lock_type):
                    active_locks += 1

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        chats = users = active_locks = total_locks = 0
        events = []

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "chats": chats,
        "users": users,
        "events": events,
        "active_locks": active_locks,
        "total_locks": total_locks,
    })

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

def start_dashboard():
    threading.Thread(target=run_web, daemon=True).start()
    logger.info("✅ لوحة التحكم تعمل على البورت 8000")

