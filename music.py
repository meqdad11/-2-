import re
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

DOWNLOADER_BOT = "@Glory120_bot"  # يوزر بوت التحميل
pending_downloads = {}
URL_PATTERN = re.compile(r'(https?://\S+)')

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
        # إرسال الرابط كنص إلى بوت التحميل (وليس إعادة توجيه)
        sent = await context.bot.send_message(chat_id=DOWNLOADER_BOT, text=url)
        # ربط معرف الدردشة الأصلية بالرسالة المرسلة (لمعرفة أين نرد لاحقاً)
        pending_downloads[sent.message_id] = msg.chat.id
        await msg.reply_text("⏳ جارٍ التحميل عبر مساعد التحميل...")
    except Exception as e:
        logger.error(f"فشل إرسال الرابط لبوت التحميل: {e}")
        await msg.reply_text("❌ تعذر الاتصال بمساعد التحميل. تأكد من أن بوت التحميل يعمل وأنك أرسلت له /start.")

async def handle_downloader_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or msg.from_user.username != DOWNLOADER_BOT.replace("@", ""):
        return

    # البحث عن الدردشة الأصلية (التي طلبت التحميل)
    chat_id = None
    # إذا كان رداً على رسالة أرسلها شفق، نأخذ معرف الدردشة المخزن
    if msg.reply_to_message and msg.reply_to_message.message_id in pending_downloads:
        chat_id = pending_downloads.pop(msg.reply_to_message.message_id)
    else:
        # وإلا نستخدم آخر طلب معروف (حل مؤقت)
        if pending_downloads:
            _, chat_id = pending_downloads.popitem()

    if not chat_id:
        await msg.reply_text("❌ لا يمكن تحديد مستلم الملف.")
        return

    try:
        if msg.video:
            await context.bot.send_video(chat_id=chat_id, video=msg.video.file_id, caption=msg.caption)
        elif msg.audio:
            await context.bot.send_audio(chat_id=chat_id, audio=msg.audio.file_id, title=msg.audio.title, performer=msg.audio.performer)
        elif msg.document:
            await context.bot.send_document(chat_id=chat_id, document=msg.document.file_id)
        elif msg.text:
            await context.bot.send_message(chat_id=chat_id, text=msg.text)
        else:
            await context.bot.send_message(chat_id=chat_id, text="✅ تم استلام ملف ولكن لا يمكن إعادة توجيهه.")
    except Exception as e:
        logger.error(f"فشل إرسال الملف للمستخدم: {e}")

# دوال فارغة للتوافق
async def callback_download(update, context): pass
async def callback_sc_download(update, context): pass
async def callback_yt_pick(update, context): pass
async def callback_sc_pick(update, context): pass
async def handle_userbot_response(update, context): pass