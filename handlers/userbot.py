import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# ---------- بيانات اليوزربوت (حسابك الشخصي) ----------
USERBOT_CHAT_ID = 729970974  # معرف حسابك على تيليجرام (المطور)

async def cmd_send_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رابط المجموعة إلى عضو محظور سابقًا عبر اليوزربوت"""
    if not context.args:
        await update.message.reply_text("❌ استخدم: ارسل_رابط <معرف_العضو>")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ معرف العضو يجب أن يكون رقمًا.")
        return

    try:
        from telegram import Bot
        import os as _os
        bot = Bot(token=_os.environ.get("TELEGRAM_BOT_TOKEN"))
        cmd = f"/send_invite {target_id}"
        await bot.send_message(chat_id=USERBOT_CHAT_ID, text=cmd)
        await update.message.reply_text(f"✅ تم إرسال رابط المجموعة إلى {target_id} عبر المساعد.")
    except Exception as e:
        logger.error(f"فشل إرسال أمر الدعوة: {e}")
        await update.message.reply_text("❌ تعذر إرسال الدعوة حاليًا.")

async def cmd_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة خاصة إلى أي عضو عبر اليوزربوت"""
    if len(context.args) < 2:
        await update.message.reply_text("❌ استخدم: ارسل_رسالة <معرف_العضو> <النص>")
        return
    try:
        target_id = int(context.args[0])
        message = " ".join(context.args[1:])
    except ValueError:
        await update.message.reply_text("❌ معرف العضو يجب أن يكون رقمًا.")
        return

    try:
        from telegram import Bot
        import os as _os
        bot = Bot(token=_os.environ.get("TELEGRAM_BOT_TOKEN"))
        cmd = f"/msg {target_id} {message}"
        await bot.send_message(chat_id=USERBOT_CHAT_ID, text=cmd)
        await update.message.reply_text(f"✅ تم إرسال الرسالة إلى {target_id} عبر المساعد.")
    except Exception as e:
        logger.error(f"فشل إرسال الأمر: {e}")
        await update.message.reply_text("❌ تعذر إرسال الرسالة حاليًا.")