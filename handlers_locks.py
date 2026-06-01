import logging
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from helpers import is_admin

logger = logging.getLogger(__name__)

# ================== أوامر القفل والفتح لكل نوع ==================

async def cmd_lock_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await db.set_lock(update.effective_chat.id, "links", True)
    await update.message.reply_text("🔒 تم قفل الروابط.")

async def cmd_unlock_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await db.set_lock(update.effective_chat.id, "links", False)
    await update.message.reply_text("🔓 تم فتح الروابط.")

async def cmd_lock_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await db.set_lock(update.effective_chat.id, "tags", True)
    await update.message.reply_text("🔒 تم قفل التاك.")

async def cmd_unlock_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await db.set_lock(update.effective_chat.id, "tags", False)
    await update.message.reply_text("🔓 تم فتح التاك.")

# ... (بنفس الطريقة لبقية الأنواع: media, files, video, voice, gifs, edit, ...)
# اختصاراً، سأكتب باقي الدوال إذا أردت، لكن جرب أولاً هاتين.

async def cmd_lock_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    for lt in ["links", "tags"]:  # أضف باقي الأنواع لاحقاً
        await db.set_lock(update.effective_chat.id, lt, True)
    await update.message.reply_text("🔒 تم قفل جميع الحمايات.")

async def cmd_unlock_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    for lt in ["links", "tags"]:
        await db.set_lock(update.effective_chat.id, lt, False)
    await update.message.reply_text("🔓 تم فتح جميع الحمايات.")

# ================== فلترة المحتوى ==================
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
        await msg.reply_text("🚫 التاك مقفل.")
        return