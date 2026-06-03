import asyncio
import logging
import os
import re
import tempfile
from typing import List, Dict

import yt_dlp
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

SEARCH_CACHE = {}
MAX_FILE_MB = 45

SOUNDCLOUD_DOMAINS = ("soundcloud.com",)
VIDEO_ONLY_DOMAINS = ("vt.tiktok.com", "instagram.com")
YOUTUBE_DOMAINS = ("youtube.com", "youtu.be")
ALL_DOMAINS = SOUNDCLOUD_DOMAINS + VIDEO_ONLY_DOMAINS + YOUTUBE_DOMAINS

URL_PATTERN = re.compile(
    r'https?://(?:(?:www\.|vm\.|vt\.)?tiktok\.com|(?:www\.)?youtube\.com|youtu\.be|(?:www\.)?instagram\.com|(?:www\.|on\.)?soundcloud\.com)'
    r'[^\s]*',
    re.IGNORECASE
)

def extract_url(text: str):
    match = URL_PATTERN.search(text)
    return match.group(0) if match else None

def get_url_type(url: str) -> str:
    if any(d in url for d in SOUNDCLOUD_DOMAINS):
        return "audio"
    if any(d in url for d in VIDEO_ONLY_DOMAINS):
        return "video"
    return "ask"

def fmt_dur(seconds) -> str:
    try:
        s = int(seconds)
        return f"{s//60}:{s%60:02d}"
    except Exception:
        return ""

def _get_common_opts():
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 5,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"],
                "skip": ["hls", "dash"],
            }
        },
        "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36",
    }
    if os.path.exists("cookies.txt"):
        opts["cookiefile"] = "cookies.txt"
    return opts

def _download_media(url: str, audio_only: bool) -> dict:
    tmp_dir = tempfile.mkdtemp()
    base_opts = _get_common_opts()
    if audio_only:
        ydl_opts = {
            **base_opts,
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tmp_dir, "%(title)s.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }],
            "max_filesize": MAX_FILE_MB * 1024 * 1024,
        }
    else:
        ydl_opts = {
            **base_opts,
            "format": "best[filesize<45M]/best[height<=720]/best",
            "outtmpl": os.path.join(tmp_dir, "%(title)s.%(ext)s"),
            "max_filesize": MAX_FILE_MB * 1024 * 1024,
        }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if "entries" in info:
                info = info["entries"][0]
        title = info.get("title", "media")
        duration = info.get("duration", 0)
        uploader = info.get("uploader", "")
        for fname in os.listdir(tmp_dir):
            fpath = os.path.join(tmp_dir, fname)
            if os.path.getsize(fpath) > 0:
                return {"path": fpath, "title": title,
                        "duration": duration, "uploader": uploader}
        raise FileNotFoundError("لم يُنشأ الملف")
    except Exception as e:
        raise Exception(f"فشل التحميل: {e}")

async def send_media(message, path: str, info: dict, audio_only: bool):
    size = os.path.getsize(path)
    if size > MAX_FILE_MB * 1024 * 1024:
        os.remove(path)
        raise Exception(f"الملف أكبر من {MAX_FILE_MB}MB")
    
    channel_button = [[InlineKeyboardButton("📢 قناة تحديثات شفق", url="https://t.me/shafaqmeqdad")]]
    reply_markup = InlineKeyboardMarkup(channel_button)
    
    with open(path, "rb") as f:
        if audio_only:
            await message.reply_audio(
                audio=f,
                title=info["title"][:100],
                performer=info["uploader"][:100] if info["uploader"] else "Unknown",
                duration=int(info["duration"]) if info["duration"] else 0,
                reply_markup=reply_markup
            )
        else:
            await message.reply_video(
                video=f,
                caption=info["title"][:100],
                reply_markup=reply_markup
            )
    os.remove(path)

async def handle_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post
    if not msg or not msg.text:
        return
    url = extract_url(msg.text)
    if not url:
        return
    url_type = get_url_type(url)
    if url_type == "audio":
        status = await msg.reply_text("⏳ جارٍ التحميل...")
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, _download_media, url, True)
            await status.edit_text("📤 جارٍ الإرسال...")
            await send_media(msg, info["path"], info, True)
            await status.delete()
        except Exception as e:
            logger.error("خطأ تحميل صوت: %s", e)
            await status.edit_text("❌ تعذّر التحميل.")
    elif url_type == "video":
        status = await msg.reply_text("⏳ جارٍ التحميل...")
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, _download_media, url, False)
            await status.edit_text("📤 جارٍ الإرسال...")
            await send_media(msg, info["path"], info, False)
            await status.delete()
        except Exception as e:
            logger.error("خطأ تحميل فيديو: %s", e)
            await status.edit_text("❌ تعذّر التحميل.")
    else:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎵 صوت فقط", callback_data=f"dl_audio|{url}"),
            InlineKeyboardButton("🎬 فيديو",    callback_data=f"dl_video|{url}"),
        ]])
        await msg.reply_text("ايش أحمل؟", reply_markup=keyboard)

async def callback_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        action, url = query.data.split("|", 1)
        audio_only = action == "dl_audio"
        status = await query.message.reply_text("⏳ جارٍ التحميل...")
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, _download_media, url, audio_only)
            await status.edit_text("📤 جارٍ الإرسال...")
            await send_media(query.message, info["path"], info, audio_only)
            await status.delete()
        except Exception as e:
            logger.error("خطأ تحميل: %s", e)
            await status.edit_text(f"❌ تعذّر التحميل: {str(e)[:40]}")
    except Exception as e:
        logger.error("خطأ في معالجة الزر: %s", e)
        await query.message.reply_text("❌ حدث خطأ في معالجة الطلب.")

async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "أرسل رابط مباشرة للتحميل\n"
            "الروابط المدعومة: يوتيوب، تيك توك، انستقرام"
        )
        return
    url = extract_url(" ".join(context.args))
    if not url:
        await update.message.reply_text("❌ لم يُعثر على رابط مدعوم.")
        return
    url_type = get_url_type(url)
    if url_type == "audio":
        await update.message.reply_text(
            "❌ ساوند كلاود غير متاح حالياً.\n\n"
            "💡 الحل: ابحث عن الأغنية على اليوتيوب\n"
            "اكتب: يوتيوب <اسم الأغنية>"
        )
    elif url_type == "video":
        status = await update.message.reply_text("⏳ جارٍ التحميل...")
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, _download_media, url, False)
            await status.edit_text("📤 جارٍ الإرسال...")
            await send_media(update.message, info["path"], info, False)
            await status.delete()
        except Exception as e:
            await status.edit_text(f"❌ تعذّر التحميل: {str(e)[:50]}")
    else:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎵 صوت فقط", callback_data=f"dl_audio|{url}"),
            InlineKeyboardButton("🎬 فيديو",    callback_data=f"dl_video|{url}"),
        ]])
        await update.message.reply_text("ايش أحمل؟", reply_markup=keyboard)

def _search_youtube(query: str) -> List[Dict]:
    try:
        logger.info(f"بدء البحث في يوتيوب: {query}")
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'playlistend': 5,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'web'],
                    'skip': ['hls', 'dash'],
                }
            },
            'user_agent': "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36",
        }
        if os.path.exists("cookies.txt"):
            ydl_opts['cookiefile'] = 'cookies.txt'
        
        search_url = f"ytsearch5:{query}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            results = []
            if 'entries' in info:
                for entry in info['entries'][:5]:
                    if entry and entry.get('id'):
                        results.append({
                            'title': entry.get('title', 'بدون عنوان'),
                            'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                            'duration': fmt_dur(entry.get('duration', 0)),
                            'id': entry.get('id', ''),
                        })
            logger.info(f"وجدنا {len(results)} نتائج في يوتيوب")
            return results
    except Exception as e:
        logger.error(f"خطأ البحث في يوتيوب: {e}")
        return []

async def cmd_sc_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "ساوند كلاود غير متاح حالياً ❌\n\n"
            "استخدم اليوتيوب بدلاً منه:\n"
            "يوتيوب <اسم الأغنية>\n\n"
            "مثال: يوتيوب فيروز"
        )
        return
    query = " ".join(context.args)
    await update.message.reply_text(
        f"ساوند كلاود غير متاح حالياً ❌\n\n"
        f"سأبحث عن '{query}' على اليوتيوب بدلاً منه 🎵"
    )
    context.args = context.args
    await cmd_yt_search(update, context)

async def cmd_yt_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "الاستخدام: يوتيوب <اسم الفيديو>\n"
            "مثال: يوتيوب فيروز"
        )
        return
    query = " ".join(context.args)
    status = await update.message.reply_text("🔍 جاري البحث في يوتيوب...")
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _search_youtube, query)
        if not results:
            await status.edit_text("❌ لم يتم العثور على نتائج.")
            return
        cache_id = f"yt_{query[:20]}"
        SEARCH_CACHE[cache_id] = results
        keyboard = []
        for i, result in enumerate(results, 1):
            btn_text = f"{i}. {result['title'][:20]}..." if len(result['title']) > 20 else f"{i}. {result['title']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"yt_pick|{cache_id}|{i-1}")])
        await status.edit_text(f"🎬 نتائج البحث عن '{query}':\n\nاختر فيديو:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"خطأ في cmd_yt_search: {e}")
        await status.edit_text(f"❌ حدث خطأ في البحث: {str(e)[:40]}")

async def callback_sc_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "❌ ساوند كلاود غير متاح حالياً.\n\n"
        "💡 استخدم اليوتيوب بدلاً منه لتحميل الأغاني"
    )

async def callback_yt_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split("|")
        cache_id = parts[1]
        index = int(parts[2])
        if cache_id not in SEARCH_CACHE:
            await query.message.reply_text("❌ انتهت مدة البحث. حاول مجددا.")
            return
        results = SEARCH_CACHE[cache_id]
        if index >= len(results):
            await query.message.reply_text("❌ خيار غير صحيح.")
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