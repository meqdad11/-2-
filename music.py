import re, logging, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)
USERBOT_CHAT_ID = 729970974
URL_PATTERN = re.compile(r'(https?://\S+)')

# دوال وهمية لاستيراد الأوامر
async def cmd_download(update, context): await update.message.reply_text("ℹ️ أرسل رابطاً مباشراً.")
async def cmd_sc_search(update, context): await update.message.reply_text("ℹ️ أرسل رابطاً مباشراً.")
async def cmd_yt_search(update, context): await update.message.reply_text("ℹ️ أرسل رابطاً مباشراً.")

# ---------- استقبال الروابط ----------
async def handle_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post
    if not msg or not msg.text: return
    url_match = URL_PATTERN.search(msg.text)
    if not url_match: return
    url = url_match.group()

    # عرض أزرار الاختيار
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎬 فيديو", callback_data=f"dl_video|{url}"),
        InlineKeyboardButton("🎵 صوت",   callback_data=f"dl_audio|{url}"),
    ]])
    await msg.reply_text("اختر نوع التحميل:", reply_markup=keyboard)

# ---------- معالج الأزرار ----------
async def callback_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        action, url = query.data.split("|", 1)
        audio_only = (action == "dl_audio")
        chat_id = query.message.chat.id

        # إرسال أمر التحميل إلى اليوزربوت
        cmd = f"/download {'audio' if audio_only else 'video'} {url} {chat_id}"
        await context.bot.send_message(chat_id=USERBOT_CHAT_ID, text=cmd)

        # حذف رسالة الأزرار وإظهار رسالة انتظار
        await query.message.delete()
        await context.bot.send_message(chat_id=chat_id, text="⏳ جارٍ التحميل...")
    except Exception as e:
        logger.error(f"خطأ في callback_download: {e}")
        await query.message.edit_text("❌ فشل إرسال الطلب.")

# ---------- دوال فارغة للتوافق ----------
async def handle_userbot_response(update, context): pass
async def callback_sc_download(update, context): pass
async def callback_yt_pick(update, context): pass
async def callback_sc_pick(update, context): pass
async def handle_downloader_response(update, context): pass