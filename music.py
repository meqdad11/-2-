import asyncio
import logging
import os
import re
import tempfile
from typing import List, Dict

import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# ---------- ثوابت ----------
MAX_FILE_MB = 45
YOUTUBE_DOMAINS = ("youtube.com", "youtu.be")
TIKTOK_DOMAINS = ("tiktok.com", "vt.tiktok.com", "vm.tiktok.com")
SOUNDCLOUD_DOMAINS = ("soundcloud.com",)

URL_PATTERN = re.compile(
    r'https?://(?:(?:www\.|vm\.|vt\.)?tiktok\.com|(?:www\.)?youtube\.com|youtu\.be|(?:www\.)?instagram\.com|(?:www\.|on\.)?soundcloud\.com)[^\s]*',
    re.IGNORECASE
)

# ---------- بيانات اليوزربوت (حسابك الشخصي) ----------
USERBOT_CHAT_ID = 729970974  # معرف حسابك على تيليجرام (المطور)

# ذاكرة مؤقتة لتخزين الطلبات: request_id -> (chat_id, message_id)
pending_requests = {}
request_counter = 0

def extract_url(text: str):
    match = URL_PATTERN.search(text)
    return match.group(0) if match else None

def get_url_type(url: str) -> str:
    if any(d in url for d in SOUNDCLOUD_DOMAINS):
        return "audio"
    if any(d in url for d in TIKTOK_DOMAINS):
        return "tiktok"
    return "ask"

def fmt_dur(seconds) -> str:
    try:
        s = int(seconds)
        return f"{s//60}:{s%60:02d}"
    except:
        return ""

# ---------- دوال التحميل المباشر (للاستخدام الطارئ فقط، لكننا عطلناها) ----------

def _get_common_opts():
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 5,
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "tv_embedded"],
                "skip": ["hls", "dash"],
            }
        },
        "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36",
    }
    cookies_data = os.environ.get("COOKIES_DATA")
    if cookies_data:
        cookies_path = "/tmp/cookies.txt"
        with open(cookies_path, "w") as f:
            f.write(cookies_data)
        opts["cookiefile"] = cookies_path
    elif os.path.exists("cookies.txt"):
        opts["cookiefile"] = "cookies.txt"
    return opts

async def _send_to_userbot(url: str, audio_only: bool, chat_id: int, message_id: int):
    """إرسال أمر التحميل إلى حسابك الشخصي (اليوزربوت)"""
    global request_counter
    request_counter += 1
    req_id = f"{chat_id}_{message_id}_{request_counter}"
    pending_requests[req_id] = (chat_id, message_id)
    
    # بناء الأمر: /download [url] [audio إن وجد]
    cmd = f"/download {url}"
    if audio_only:
        cmd += " audio"
    
    try:
        from telegram import Bot
        import os as _os
        bot = Bot(token=_os.environ.get("TELEGRAM_BOT_TOKEN"))
        # نرسل الأمر إلى حسابك الشخصي
        await bot.send_message(chat_id=USERBOT_CHAT_ID, text=cmd)
        logger.info(f"أرسلنا أمر التحميل إلى اليوزربوت: {cmd}")
        return req_id
    except Exception as e:
        logger.error(f"فشل إرسال الأمر لليوزربوت: {e}")
        pending_requests.pop(req_id, None)
        return None

async def handle_userbot_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال الملفات القادمة من اليوزربوت (حسابك الشخصي) وإرسالها للمستخدم الأصلي"""
    msg = update.message
    if not msg or not msg.from_user:
        return
    
    # التأكد أن المرسل هو حسابك الشخصي وليس أي أحد آخر
    if msg.from_user.id != USERBOT_CHAT_ID:
        return
    
    # نبحث عن أول طلب معلق (نظام بسيط، يمكن تحسينه لاحقًا)
    if not pending_requests:
        return
    
    # نأخذ أول طلب في الذاكرة
    req_id, (chat_id, message_id) = next(iter(pending_requests.items()))
    del pending_requests[req_id]
    
    # إعادة إرسال الملف للمستخدم
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
            pass  # ربما رسالة نصية (خطأ)
    except Exception as e:
        logger.error(f"فشل إعادة إرسال الملف للمستخدم: {e}")
    finally:
        # حذف الرسالة المؤقتة من اليوزربوت (اختياري)
        try:
            await msg.delete()
        except:
            pass

# ---------- معالجة الرابط المباشر (من المستخدم) ----------
async def handle_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post
    if not msg or not msg.text:
        return
    url = extract_url(msg.text)
    if not url:
        return
    url_type = get_url_type(url)
    
    if url_type == "audio":
        req_id = await _send_to_userbot(url, True, msg.chat.id, msg.message_id)
        if req_id:
            await msg.reply_text("🎵 تم إرسال الطلب إلى مساعد التحميل... قد يستغرق الأمر قليلاً.")
        else:
            await msg.reply_text("❌ تعذر الاتصال بمساعد التحميل.")
    elif url_type == "tiktok":
        req_id = await _send_to_userbot(url, False, msg.chat.id, msg.message_id)
        if req_id:
            await msg.reply_text("📱 تم إرسال الطلب إلى مساعد التحميل...")
        else:
            await msg.reply_text("❌ تعذر الاتصال بمساعد التحميل.")
    else:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎵 صوت فقط", callback_data=f"dl_audio|{url}"),
            InlineKeyboardButton("🎬 فيديو",    callback_data=f"dl_video|{url}"),
        ]])
        await msg.reply_text("اختر نوع التحميل:", reply_markup=keyboard)

# ---------- الأزرار (اختيار فيديو/صوت) ----------
async def callback_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        action, url = query.data.split("|", 1)
        audio_only = (action == "dl_audio")
        chat_id = query.message.chat.id
        message_id = query.message.message_id
        
        req_id = await _send_to_userbot(url, audio_only, chat_id, message_id)
        if req_id:
            await query.message.edit_text("⏳ جارٍ إرسال الطلب لمساعد التحميل...")
        else:
            await query.message.edit_text("❌ تعذر الاتصال بمساعد التحميل.")
    except Exception as e:
        logger.error(f"خطأ في callback_download: {e}")
        await query.message.reply_text("❌ حدث خطأ في معالجة الطلب.")

# ---------- أمر /download (للتوافق) ----------
async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("أرسل رابط مباشرة للتحميل")
        return
    url = extract_url(" ".join(context.args))
    if not url:
        await update.message.reply_text("❌ لم يُعثر على رابط مدعوم.")
        return
    url_type = get_url_type(url)
    if url_type == "audio":
        req_id = await _send_to_userbot(url, True, update.effective_chat.id, update.message.message_id)
        await update.message.reply_text("🎵 تم إرسال الطلب..." if req_id else "❌ فشل")
    else:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎵 صوت فقط", callback_data=f"dl_audio|{url}"),
            InlineKeyboardButton("🎬 فيديو",    callback_data=f"dl_video|{url}"),
        ]])
        await update.message.reply_text("اختر نوع التحميل:", reply_markup=keyboard)

# ---------- البحث في يوتيوب (يعمل عادي) ----------
async def cmd_yt_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: يوتيوب <اسم الفيديو>")
        return
    query = " ".join(context.args)
    status = await update.message.reply_text("🔍 جاري البحث في يوتيوب...")
    try:
        results = _search_youtube(query)
        if not results:
            await status.edit_text("❌ لم يتم العثور على نتائج.")
            return
        SEARCH_CACHE[query] = results
        keyboard = []
        for i, result in enumerate(results, 1):
            btn_text = f"{i}. {result['title'][:20]}..." if len(result['title']) > 20 else f"{i}. {result['title']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"yt_pick|{query}|{i-1}")])
        await status.edit_text(f"🎬 نتائج البحث عن '{query}':\n\nاختر فيديو:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"خطأ في cmd_yt_search: {e}")
        await status.edit_text(f"❌ حدث خطأ في البحث: {str(e)[:40]}")

# ---------- اختيار نتيجة بحث ----------
async def callback_yt_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        _, cache_key, index = query.data.split("|")
        index = int(index)
        results = SEARCH_CACHE.get(cache_key)
        if not results or index >= len(results):
            await query.message.reply_text("❌ انتهت مدة البحث. حاول مجددا.")
            return
        url = results[index]['url']
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎵 صوت فقط", callback_data=f"dl_audio|{url}"),
            InlineKeyboardButton("🎬 فيديو",    callback_data=f"dl_video|{url}"),
        ]])
        await query.message.edit_text("شو تبي؟", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"خطأ في callback_yt_pick: {e}")
        await query.message.reply_text("❌ حدث خطأ في معالجة الطلب.")

# ---------- دالة البحث (مساعد) ----------
SEARCH_CACHE = {}

def _search_youtube(query: str) -> List[Dict]:
    try:
        ydl_opts = {
            'quiet': True, 'no_warnings': True,
            'extract_flat': 'in_playlist', 'playlistend': 5,
            'extractor_args': {'youtube': {'player_client': ['ios', 'android', 'tv_embedded'], 'skip': ['hls', 'dash']}},
            'user_agent': "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            results = []
            if 'entries' in info:
                for entry in info['entries'][:5]:
                    if entry and entry.get('id'):
                        results.append({
                            'title': entry.get('title', 'بدون عنوان'),
                            'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                            'duration': fmt_dur(entry.get('duration', 0)),
                        })
            return results
    except Exception as e:
        logger.error(f"خطأ البحث في يوتيوب: {e}")
        return []

# ---------- الدوال المتبقية (تيك توك، ساوند كلاود) ----------
async def cmd_sc_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ساوند كلاود غير متاح حالياً. استخدم يوتيوب.")

async def callback_sc_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("غير متاح")