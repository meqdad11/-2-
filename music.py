import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# ضع يوزر بوت التحميل هنا
DOWNLOADER_BOT = "@Glory120_bot"

# لتخزين هوية المستخدم الأصلي (مؤقت)
pending_downloads = {}

async def handle_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    # إعادة توجيه الرسالة إلى بوت التحميل
    try:
        forwarded = await msg.forward(chat_id=DOWNLOADER_BOT)
        # خزّن: معرف الرسالة المُعاد توجيهها -> (chat_id الأصلي, user_id)
        pending_downloads[forwarded.message_id] = (msg.chat.id, msg.from_user.id)
    except Exception as e:
        logger.error(f"فشل التوجيه: {e}")
        await msg.reply_text("❌ تعذر إرسال الرابط لبوت التحميل.")

async def handle_downloader_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.from_user.username != DOWNLOADER_BOT.replace("@", ""):
        return

    # ابحث عن الطلب الأصلي
    if msg.reply_to_message and msg.reply_to_message.message_id in pending_downloads:
        chat_id, user_id = pending_downloads.pop(msg.reply_to_message.message_id)
    else:
        return

    # أرسل الملف إلى المستخدم الأصلي
    try:
        if msg.video:
            await context.bot.send_video(chat_id=chat_id, video=msg.video.file_id,
                                         caption=msg.caption or "تم التحميل بواسطة شفق")
        elif msg.audio:
            await context.bot.send_audio(chat_id=chat_id, audio=msg.audio.file_id,
                                         title=msg.audio.title, performer=msg.audio.performer)
        elif msg.document:
            await context.bot.send_document(chat_id=chat_id, document=msg.document.file_id)
        else:
            await context.bot.send_message(chat_id=chat_id, text="تم التحميل لكن تعذر إرسال الملف.")
    except Exception as e:
        logger.error(f"فشل إرسال الملف للمستخدم: {e}")