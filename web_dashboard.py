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

# إعداد القوالب (سنضعها في مجلد "templates")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    # جلب إحصائيات سريعة من قاعدة البيانات
    chats = len(await db.get_all_active_chats())
    users = sum(1 for s in db._cache.get("user_stats", {}).values())
    events = list(db._cache.get("ban_log", [])[-20:])  # آخر 20 حدث
    locks = db._cache.get("group_locks", {})
    active_locks = sum(1 for l in locks.values() if l.get("is_locked"))
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "chats": chats,
        "users": users,
        "events": events,
        "active_locks": active_locks,
        "total_locks": len(locks)
    })

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

# تشغيل الويب في خيط منفصل عند استدعاء هذه الدالة
def start_dashboard():
    threading.Thread(target=run_web, daemon=True).start()