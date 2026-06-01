import logging
from functools import partial
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from helpers import is_admin

logger = logging.getLogger(__name__)

# قائمة أنواع الأقفال
LOCK_TYPES = [
    "links", "tags", "media", "files", "video", "voice", "gifs",
    "edit", "editmedia", "repeat", "join", "forward", "id", "badwords",
    "spam", "replies", "notifications", "persian", "bots", "iranian",
    "longtext", "quran", "porn", "ai", "autoreply", "games", "marketnews", "whisper"
]

LOCK_NAMES = {
    "links": "الروابط", "tags": "التاك", "media": "الميديا", "files": "الملفات",
    "video": "الفيديو", "voice": "الفويسات", "gifs": "المتحركات", "edit": "التعديل",
    "editmedia": "تعديل الميديا", "repeat": "التكرار", "join": "الدخول", "forward": "التوجيه",
    "id": "ايدي", "badwords": "السب", "spam": "السبام", "replies": "الردود",
    "notifications": "الاشعارات", "persian": "الفارسية", "bots": "البوتات", "iranian": "دخول الايراني",
    "longtext": "الكلام الكثير", "quran": "القرآن", "porn": "الاباحي", "ai": "الذكاء الاصطناعي",
    "autoreply": "الرد التلقائي", "games": "الألعاب", "marketnews": "اخبار السوق", "whisper": "الهمسة"
}

# دالة عامة للقفل
async def _lock_general(update: Update, context: ContextTypes.DEFAULT_TYPE, lock_type: str):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await db.set_lock(update.effective_chat.id, lock_type, True)
    await update.message.reply_text(f"🔒 تم قفل {LOCK_NAMES.get(lock_type, lock_type)}.")

# دالة عامة للفتح
async def _unlock_general(update: Update, context: ContextTypes.DEFAULT_TYPE, lock_type: str):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await db.set_lock(update.effective_chat.id, lock_type, False)
    await update.message.reply_text(f"🔓 تم فتح {LOCK_NAMES.get(lock_type, lock_type)}.")

# إنشاء الدوال باستخدام partial وتسجيلها في النطاق العام
for lt in LOCK_TYPES:
    setattr(__import__(__name__), f"cmd_lock_{lt}", partial(_lock_general, lock_type=lt))
    setattr(__import__(__name__), f"cmd_unlock_{lt}", partial(_unlock_general, lock_type=lt))

# دوال خاصة بقفل/فتح الكل
async def cmd_lock_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    for lt in LOCK_TYPES:
        await db.set_lock(update.effective_chat.id, lt, True)
    await update.message.reply_text("🔒 تم قفل جميع الحمايات.")

async def cmd_unlock_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    for lt in LOCK_TYPES:
        await db.set_lock(update.effective_chat.id, lt, False)
    await update.message.reply_text("🔓 تم فتح جميع الحمايات.")

# دالة فلترة المحتوى (كما هي)
async def filter_locked_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    chat_id = msg.chat.id
    text = msg.text.lower()

    if ("http://" in text or "https://" in text or "www." in text or ".com" in text):
        if await db.is_locked(chat_id, "links"):
            await msg.delete()
            await msg.reply_text("🚫 الروابط مقفلة في هذه المجموعة.")
            return
    if "@" in text and await db.is_locked(chat_id, "tags"):
        await msg.delete()
        await msg.reply_text("🚫 التاك (المشن) مقفل.")
        return
    banned_words = await db.get_banned_words(chat_id)
    if any(word in text for word in banned_words) and await db.is_locked(chat_id, "badwords"):
        await msg.delete()
        await msg.reply_text("🚫 الكلمات الممنوعة غير مسموحة.")
        return