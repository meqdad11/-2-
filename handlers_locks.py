import logging
from telegram import Update, ChatPermissions
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

# قاموس ترجمة للعرض (اختياري)
LOCK_NAMES = {
    "links": "الروابط", "tags": "التاك", "media": "الميديا", "files": "الملفات",
    "video": "الفيديو", "voice": "الفويسات", "gifs": "المتحركات", "edit": "التعديل",
    "editmedia": "تعديل الميديا", "repeat": "التكرار", "join": "الدخول", "forward": "التوجيه",
    "id": "ايدي", "badwords": "السب", "spam": "السبام", "replies": "الردود",
    "notifications": "الاشعارات", "persian": "الفارسية", "bots": "البوتات", "iranian": "دخول الايراني",
    "longtext": "الكلام الكثير", "quran": "القرآن", "porn": "الاباحي", "ai": "الذكاء الاصطناعي",
    "autoreply": "الرد التلقائي", "games": "الألعاب", "marketnews": "اخبار السوق", "whisper": "الهمسة"
}

# ========== دالة فلترة المحتوى الرئيسية ==========
async def filter_locked_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        # يمكن إضافة فحص للوسائط لاحقاً
        return
    chat_id = msg.chat.id
    text = msg.text.lower()

    # قفل الروابط
    if ("http://" in text or "https://" in text or "www." in text or ".com" in text):
        if await db.is_locked(chat_id, "links"):
            await msg.delete()
            await msg.reply_text("🚫 الروابط مقفلة في هذه المجموعة.")
            return

    # قفل التاك
    if "@" in text and await db.is_locked(chat_id, "tags"):
        await msg.delete()
        await msg.reply_text("🚫 التاك (المشن) مقفل.")
        return

    # قفل الكلمات المحظورة
    banned_words = await db.get_banned_words(chat_id)
    if any(word in text for word in banned_words) and await db.is_locked(chat_id, "badwords"):
        await msg.delete()
        await msg.reply_text("🚫 الكلمات الممنوعة غير مسموحة.")
        return

# ========== دوال القفل والفتح لكل نوع (للاستخدام عبر الأوامر الكتابية) ==========
# سيتم إنشاؤها ديناميكياً لتجنب تكرار الكود
async def _lock(update: Update, context: ContextTypes.DEFAULT_TYPE, lock_type: str):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await db.set_lock(update.effective_chat.id, lock_type, True)
    name = LOCK_NAMES.get(lock_type, lock_type)
    await update.message.reply_text(f"🔒 تم قفل {name}.")

async def _unlock(update: Update, context: ContextTypes.DEFAULT_TYPE, lock_type: str):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await db.set_lock(update.effective_chat.id, lock_type, False)
    name = LOCK_NAMES.get(lock_type, lock_type)
    await update.message.reply_text(f"🔓 تم فتح {name}.")

# إنشاء الدوال لكل نوع
for lt in LOCK_TYPES:
    # قفل
    async def make_lock_func(lock_type=lt):
        async def func(update, context):
            await _lock(update, context, lock_type)
        return func
    # فتح
    async def make_unlock_func(lock_type=lt):
        async def func(update, context):
            await _unlock(update, context, lock_type)
        return func
    globals()[f"cmd_lock_{lt}"] = make_lock_func(lt)
    globals()[f"cmd_unlock_{lt}"] = make_unlock_func(lt)

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