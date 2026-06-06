import re
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# يوزر بوت التحميل الجديد
DOWNLOADER_BOT = "@Glory120_bot"

# لتخزين معرف الدردشة الأصلي للمستخدمين مؤقتاً
pending_downloads = {}

# نمط استخراج أي رابط
URL_PATTERN = re.compile(r'(https?://\S+)')

# دوال وهمية للاستيراد من commands.py
async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ أرسل رابط الفيديو مباشرة ليتم تحميله.")

async def cmd_sc_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ أرسل رابط ساوند كلاود مباشرة ليتم تحميله.")

async def cmd_yt_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ أرسل رابط يوتيوب مباشرة ليتم تحميله.")

# معالج استقبال الروابط وإرسالها إلى بوت التحميل
async def handle_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post
    if not msg or not msg.text:
        return

    url_match = URL_PATTERN.search(msg.text)
    if not url_match:
        return

    url = url_match.group()
    try:
        # إعادة توجيه رسالة المستخدم كاملة إلى بوت التحميل
        forwarded = await msg.forward(chat_id=DOWNLOADER_BOT)
        # تخزين معرف الدردشة الأصلي لاستخدامه لاحقاً
        pending_downloads[forwarded.message_id] = msg.chat.id
        await msg.reply_text("⏳ جارٍ التحميل عبر مساعد التحميل...")
    except Exception as e:
        logger.error(f"فشل إرسال الرابط لبوت التحميل: {e}")
        await msg.reply_text("❌ تعذر الاتصال بمساعد التحميل.")

# معالج استقبال الملف من بوت التحميل وإرساله للمستخدم
async def handle_downloader_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or msg.from_user.username != DOWNLOADER_BOT.replace("@", ""):
        return

    # معرفة الدردشة الأصلية من الرسالة المردود عليها
    chat_id = None
    if msg.reply_to_message and msg.reply_to_message.message_id in pending_downloads:
        chat_id = pending_downloads.pop(msg.reply_to_message.message_id)
    else:
        # إذا لم نجد، نرسل للمستخدم افتراضياً (يمكن تحسينه)
        chat_id = msg.chat.id

    # إعادة إرسال الملف إلى الدردشة الأصلية
    try:
        if msg.video:
            await context.bot.send_video(chat_id=chat_id, video=msg.video.file_id, caption=msg.caption)
        elif msg.audio:
            await context.bot.send_audio(chat_id=chat_id, audio=msg.audio.file_id, title=msg.audio.title, performer=msg.audio.performer)
        elif msg.document:
            await context.bot.send_document(chat_id=chat_id, document=msg.document.file_id)
        elif msg.text:
            await context.bot.send_message(chat_id=chat_id, text=f"ℹ️ {msg.text}")
        else:
            await context.bot.send_message(chat_id=chat_id, text="✅ تم استلام ملف لا يمكن إعادة توجيهه.")
    except Exception as e:
        logger.error(f"فشل إرسال الملف للمستخدم: {e}")

# دوال فارغة للتوافق
async def callback_download(update, context): pass
async def callback_sc_download(update, context): pass
async def callback_yt_pick(update, context): pass
async def callback_sc_pick(update, context): pass
async def handle_userbot_response(update, context): pass