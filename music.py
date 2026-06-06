import re
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)
USERBOT_CHAT_ID = 729970974  # معرف حسابك

URL_PATTERN = re.compile(r'(https?://\S+)')
pending_downloads = {}

async def cmd_download(update, context): await update.message.reply_text("ℹ️ أرسل رابطاً مباشراً.")
async def cmd_sc_search(update, context): await update.message.reply_text("ℹ️ أرسل رابطاً مباشراً.")
async def cmd_yt_search(update, context): await update.message.reply_text("ℹ️ أرسل رابطاً مباشراً.")

async def handle_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post
    if not msg or not msg.text:
        return
    url_match = URL_PATTERN.search(msg.text)
    if not url_match:
        return
    url = url_match.group()

    try:
        # نرسل أمر /forward إلى اليوزربوت مع الرابط ومعرف الدردشة الأصلية
        await context.bot.send_message(
            chat_id=USERBOT_CHAT_ID,
            text=f"/forward {url} {msg.chat.id}"
        )
        await msg.reply_text("⏳ جارٍ التحميل عبر المساعد...")
    except Exception as e:
        logger.error(f"فشل إرسال الأمر لليوزربوت: {e}")
        await msg.reply_text("❌ تعذر الاتصال بالمساعد.")

async def handle_downloader_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or msg.from_user.id != USERBOT_CHAT_ID:
        return

    # اليوزربوت يرسل الملف إلينا (شفق) بعد تحميله
    # نبحث عن الطلب الأصلي (chat_id) ونرسل الملف
    if not pending_downloads:
        return
    req_id, chat_id = next(iter(pending_downloads.items()))
    del pending_downloads[req_id]

    try:
        if msg.video:
            await context.bot.send_video(chat_id=chat_id, video=msg.video.file_id, caption=msg.caption)
        elif msg.audio:
            await context.bot.send_audio(chat_id=chat_id, audio=msg.audio.file_id, title=msg.audio.title, performer=msg.audio.performer)
        elif msg.document:
            await context.bot.send_document(chat_id=chat_id, document=msg.document.file_id)
    except Exception as e:
        logger.error(f"فشل إرسال الملف للمستخدم: {e}")

async def callback_download(update, context): pass
async def callback_sc_download(update, context): pass
async def callback_yt_pick(update, context): pass
async def callback_sc_pick(update, context): pass
async def handle_userbot_response(update, context): pass
