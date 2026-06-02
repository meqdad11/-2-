import logging
import random
import datetime
import pytz
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from quotes import DAILY_QUOTES

logger = logging.getLogger(__name__)

# ========== دالة الاقتباس اليومي ==========
async def job_daily_quote(context: ContextTypes.DEFAULT_TYPE):
    """إرسال اقتباس يومي لجميع المجموعات النشطة"""
    quote = random.choice(DAILY_QUOTES)
    chats = await db.get_all_active_chats()
    for chat_id in chats:
        try:
            await context.bot.send_message(chat_id, f"💬 **اقتباس اليوم:**\n\n{quote}", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"فشل إرسال الاقتباس للمجموعة {chat_id}: {e}")

# ========== دالة التقرير ==========
async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال تقرير للمشرفين"""
    user = update.effective_user
    chat = update.effective_chat
    msg = update.message
    if not msg:
        return
    report_text = msg.text.replace("/report", "").strip() if msg.text else ""
    if not report_text:
        await msg.reply_text("اكتب سبب التقرير بعد الأمر.\nمثال: /report شخص يخالف القواعد")
        return
    admins = await context.bot.get_chat_administrators(chat.id)
    reporter_name = user.full_name or user.first_name
    for admin in admins:
        if not admin.user.is_bot:
            try:
                await context.bot.send_message(
                    admin.user.id,
                    f"📢 **تقرير جديد**\nمن: {reporter_name}\nالمجموعة: {chat.title}\nالسبب: {report_text}"
                )
            except:
                pass
    await msg.reply_text("✅ تم إرسال تقريرك إلى المشرفين.")

# ========== دالة انتهاء صلاحية الحظر ==========
async def job_expire_bans(context: ContextTypes.DEFAULT_TYPE):
    """فحص الحظر المؤقت وانتهاء صلاحيته"""
    expired = await db.get_expired_bans()
    for ban in expired:
        user_id = ban["user_id"]
        chat_id = ban["chat_id"]
        try:
            await context.bot.unban_chat_member(chat_id, user_id)
            await db.remove_ban(user_id, chat_id)
            logger.info(f"تم رفع الحظر عن {user_id} في مجموعة {chat_id}")
        except Exception as e:
            logger.error(f"فشل رفع الحظر: {e}")