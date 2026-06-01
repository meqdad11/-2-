import logging
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
import database as db
from helpers import is_admin

logger = logging.getLogger(__name__)

# قائمة أنواع الأقفال (تأكد من تطابقها مع الموجودة في database.ALL_LOCK_TYPES)
LOCK_TYPES = [
    "links", "tags", "media", "files", "video", "voice", "gifs",
    "edit", "editmedia", "repeat", "join", "forward", "id", "badwords",
    "spam", "replies", "notifications", "persian", "bots", "iranian",
    "longtext", "quran", "porn", "ai", "autoreply", "games", "marketnews", "whisper"
]

# ========== دالة فلترة المحتوى الرئيسية ==========
async def filter_locked_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تمنع الرسائل المخالفة بناءً على الأقفال المفعلة في المجموعة"""
    msg = update.message
    if not msg or not msg.text:
        # للوسائط الأخرى (صور، فيديو، ملصقات) يمكن إضافة فحص لاحقاً
        return
    chat_id = msg.chat.id
    text = msg.text.lower()

    # قفل الروابط
    if ("http://" in text or "https://" in text or "www." in text or ".com" in text):
        if await db.is_locked(chat_id, "links"):
            await msg.delete()
            await msg.reply_text("🚫 الروابط مقفلة في هذه المجموعة.")
            return

    # قفل التاك (منشن)
    if "@" in text and await db.is_locked(chat_id, "tags"):
        await msg.delete()
        await msg.reply_text("🚫 التاك (المشن) مقفل.")
        return

    # قفل الكلمات المحظورة (السب)
    banned_words = await db.get_banned_words(chat_id)
    if any(word in text for word in banned_words) and await db.is_locked(chat_id, "badwords"):
        await msg.delete()
        await msg.reply_text("🚫 الكلمات الممنوعة غير مسموحة.")
        return

    # باقي الأقفال (مثل الميديا، الفيديو، الصوت، الملفات) سنضيفها لاحقاً حسب الحاجة.
    # يمكن توسيعها بسهولة.

# ========== دوال مساعدة للقفل/الفتح (للاستخدام عبر الأزرار) ==========
async def lock_type(update: Update, context: ContextTypes.DEFAULT_TYPE, lock_key: str):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await db.set_lock(update.effective_chat.id, lock_key, True)
    await update.message.reply_text(f"🔒 تم قفل {lock_key}.")

async def unlock_type(update: Update, context: ContextTypes.DEFAULT_TYPE, lock_key: str):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await db.set_lock(update.effective_chat.id, lock_key, False)
    await update.message.reply_text(f"🔓 تم فتح {lock_key}.")

# يمكن إنشاء دوال لكل نوع تلقائياً (اختياري)
# لكن الأزرار في handlers_menu تستخدم db.set_lock مباشرة، لذلك هذه الدوال اختيارية.