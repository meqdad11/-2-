import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# يوزر بوت التحميل المتعاون معنا
DOWNLOADER_BOT = "@wtttbot"

# لتخزين الطلبات المعلقة
pending_downloads = {}

# دوال وهمية لأوامر البحث (تبقى للتوافق)
async def cmd_download(update, context): await update.message.reply_text("ℹ️ أرسل رابطاً مباشراً.")
async def cmd_sc_search(update, context): await update.message.reply_text("ℹ️ أرسل رابطاً مباشراً.")
async def cmd_yt_search(update, context): await update.message.reply_text("ℹ️ أرسل رابطاً مباشراً.")

# ---------- استقبال الروابط من المستخدم ----------
async def handle_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post
    if not msg or not msg.text:
        return

    try:
        # إعادة توجيه رسالة المستخدم إلى @wtttbot
        forwarded = await msg.forward(chat_id=DOWNLOADER_BOT)
        # تخزين معرف الدردشة الأصلي (لإعادة الفيديو لاحقاً)
        pending_downloads[forwarded.message_id] = msg.chat.id
        await msg.reply_text("⏳ جارٍ التحميل عبر مساعد التحميل...")
    except Exception as e:
        logger.error(f"فشل إعادة التوجيه: {e}")
        await msg.reply_text("❌ تعذر الاتصال بمساعد التحميل.")

# ---------- استقبال الفيديو من @wtttbot وإرساله للمستخدم ----------
async def handle_wttt_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or msg.from_user.username != DOWNLOADER_BOT.replace("@", ""):
        return

    chat_id = None
    # @wtttbot يرد على الرسالة المُعاد توجيهها، فنجد الدردشة الأصلية
    if msg.reply_to_message and msg.reply_to_message.message_id in pending_downloads:
        chat_id = pending_downloads.pop(msg.reply_to_message.message_id)
    else:
        # محاولة أخيرة باستخدام آخر طلب
        if pending_downloads:
            _, chat_id = pending_downloads.popitem()

    if not chat_id:
        await msg.reply_text("❌ خطأ: لا يمكن تحديد وجهة الملف.")
        return

    # إعادة إرسال الملف للمستخدم
    try:
        if msg.video:
            await context.bot.send_video(chat_id=chat_id, video=msg.video.file_id, caption=msg.caption)
        elif msg.audio:
            await context.bot.send_audio(chat_id=chat_id, audio=msg.audio.file_id, title=msg.audio.title, performer=msg.audio.performer)
        elif msg.document:
            await context.bot.send_document(chat_id=chat_id, document=msg.document.file_id)
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"ℹ️ {msg.text}")
    except Exception as e:
        logger.error(f"فشل إرسال الملف للمستخدم: {e}")

# دوال فارغة للتوافق
async def callback_download(update, context): pass
async def callback_sc_download(update, context): pass
async def callback_yt_pick(update, context): pass
async def callback_sc_pick(update, context): pass
async def handle_userbot_response(update, context): pass