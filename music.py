import re, logging, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)
USERBOT_CHAT_ID = 729970974
URL_PATTERN = re.compile(r'(https?://\S+)')

# دوال وهمية للاستيراد
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

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎬 فيديو", callback_data=f"dl_video|{url}"),
        InlineKeyboardButton("🎵 صوت",   callback_data=f"dl_audio|{url}"),
    ]])
    await msg.reply_text("اختر نوع التحميل:", reply_markup=keyboard)

# ---------- أزرار الاختيار ----------
async def callback_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        action, url = query.data.split("|", 1)
        audio_only = (action == "dl_audio")
        chat_id = query.message.chat.id
        # نرسل الأمر إلى اليوزربوت
        cmd = f"/forward_{'audio' if audio_only else 'video'} {url} {chat_id}"
        await context.bot.send_message(chat_id=USERBOT_CHAT_ID, text=cmd)
        await query.message.edit_text("⏳ جارٍ التحميل...")
    except Exception as e:
        logger.error(f"خطأ: {e}")
        await query.message.edit_text("❌ فشل إرسال الطلب.")

# ---------- استقبال الملف من اليوزربوت ----------
async def handle_userbot_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or msg.from_user.id != USERBOT_CHAT_ID:
        return
    # نحتاج معرفة chat_id الأصلي (سنخزنه مؤقتاً في callback_download)
    # هنا سنستخدم طريقة بسيطة: نبحث عن آخر طلب (أو نضيف pending)
    # لكن للتبسيط: نرسل الملف إلى الدردشة التي وردت في الرسالة المرسلة من اليوزربوت
    # لكن اليوزربوت سيضيف chat_id في النص. سنحسنها.
    # حالياً سنرد على نفس دردشة اليوزربوت (خاص) وهذا سيُرسل للمستخدم إذا كان في الخاص
    # لكن المجموعة تحتاج chat_id. سنقوم بتخزينها.
    # سأضيف pending_requests في التعديل القادم.
    pass

# دوال فارغة
async def callback_sc_download(update, context): pass
async def callback_yt_pick(update, context): pass
async def callback_sc_pick(update, context): pass
async def handle_downloader_response(update, context): pass