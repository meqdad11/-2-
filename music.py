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

MAX_FILE_MB = 45

SOUNDCLOUD_DOMAINS = ("soundcloud.com",)
VIDEO_ONLY_DOMAINS = ("tiktok.com", "instagram.com")
YOUTUBE_DOMAINS = ("youtube.com", "youtu.be")

ALL_DOMAINS = SOUNDCLOUD_DOMAINS + VIDEO_ONLY_DOMAINS + YOUTUBE_DOMAINS

URL_PATTERN = re.compile(
    r'https?://(?:www\.)?(?:youtube\.com|youtu\.be|tiktok\.com|instagram\.com|soundcloud\.com)'
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

def _download_media(url: str, audio_only: bool) -> dict:
    tmp_dir = tempfile.mkdtemp()
    if audio_only:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tmp_dir, "%(title)s.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }],
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "max_filesize": MAX_FILE_MB * 1024 * 1024,
        }
    else:
        ydl_opts = {
            "format": "best[filesize<45M]/best[height<=720]/best",
            "outtmpl": os.path.join(tmp_dir, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if "entries" in info:
                info = info["entries"][0]
        title    = info.get("title", "media")
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
    with open(path, "rb") as f:
        if audio_only:
            await message.reply_audio(
                audio=f,
                title=info["title"],
                performer=info["uploader"],
                duration=info["duration"],
            )
        else:
            await message.reply_video(video=f, caption=info["title"])
    os.remove(path)

async def handle_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
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
        await msg.reply_text("شو تبي أحمل؟", reply_markup=keyboard)


async def callback_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
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
        await status.edit_text("❌ تعذّر التحميل.")


async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "أرسل رابط مباشرة للتحميل\n"
            "الروابط المدعومة: يوتيوب، تيك توك، انستقرام، ساوند كلاود"
        )
        return
    url = extract_url(" ".join(context.args))
    if not url:
        await update.message.reply_text("❌ لم يُعثر على رابط مدعوم.")
        return
    url_type = get_url_type(url)
    if url_type == "audio":
        status = await update.message.reply_text("⏳ جارٍ التحميل...")
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, _download_media, url, True)
            await status.edit_text("📤 جارٍ الإرسال...")
            await send_media(update.message, info["path"], info, True)
            await status.delete()
        except Exception as e:
            await status.edit_text("❌ تعذّر التحميل.")
    elif url_type == "video":
        status = await update.message.reply_text("⏳ جارٍ التحميل...")
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, _download_media, url, False)
            await status.edit_text("📤 جارٍ الإرسال...")
            await send_media(update.message, info["path"], info, False)
            await status.delete()
        except Exception as e:
            await status.edit_text("❌ تعذّر التحميل.")
    else:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎵 صوت فقط", callback_data=f"dl_audio|{url}"),
            InlineKeyboardButton("🎬 فيديو",    callback_data=f"dl_video|{url}"),
        ]])
        await update.message.reply_text("ايش أحمل؟", reply_markup=keyboard)


def _search_youtube(query: str) -> List[Dict]:
    """البحث في يوتيوب عن الفيديوهات"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'playlistend': 5,  # أول 5 نتائج
        }
        search_url = f"ytsearch5:{query}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            results = []
            if 'entries' in info:
                for entry in info['entries'][:5]:
                    results.append({
                        'title': entry.get('title', 'بدون عنوان'),
                        'url': entry.get('url', ''),
                        'duration': fmt_dur(entry.get('duration', 0)),
                        'id': entry.get('id', ''),
                    })
            return results
    except Exception as e:
        logger.error("خطأ البحث في يوتيوب: %s", e)
        return []


def _search_soundcloud(query: str) -> List[Dict]:
    """البحث في ساوند كلاود عن الأغاني"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
        }
        search_url = f"scsearch5:{query}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            results = []
            if 'entries' in info:
                for entry in info['entries'][:5]:
                    results.append({
                        'title': entry.get('title', 'بدون عنوان'),
                        'url': entry.get('url', ''),
                        'duration': fmt_dur(entry.get('duration', 0)),
                        'id': entry.get('id', ''),
                    })
            return results
    except Exception as e:
        logger.error("خطأ البحث في ساوند كلاود: %s", e)
        return []


async def cmd_sc_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """البحث في ساوند كلاود"""
    if not context.args:
        await update.message.reply_text(
            "الاستخدام: بحث <اسم الأغنية>\n"
            "مثال: بحث عمرو دياب"
        )
        return
    
    query = " ".join(context.args)
    status = await update.message.reply_text("🔍 جاري البحث في ساوند كلاود...")
    
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _search_soundcloud, query)
        
        if not results:
            await status.edit_text("❌ لم يتم العثور على نتائج.")
            return
        
        keyboard = []
        for i, result in enumerate(results, 1):
            btn_text = f"{i}. {result['title'][:30]}..." if len(result['title']) > 30 else f"{i}. {result['title']}"
            keyboard.append([InlineKeyboardButton(
                btn_text,
                callback_data=f"sc_dl|{result['url']}"
            )])
        
        await status.edit_text(
            f"🎵 نتائج البحث عن '{query}':\n",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error("خطأ: %s", e)
        await status.edit_text("❌ حدث خطأ في البحث.")


async def cmd_yt_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """البحث في يوتيوب"""
    if not context.args:
        await update.message.reply_text(
            "الاستخدام: يوتيوب <اسم الفيديو>\n"
            "مثال: يوتيوب كليب أم عمرو دياب"
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
        
        keyboard = []
        for i, result in enumerate(results, 1):
            btn_text = f"{i}. {result['title'][:30]}..." if len(result['title']) > 30 else f"{i}. {result['title']}"
            keyboard.append([InlineKeyboardButton(
                btn_text,
                callback_data=f"yt_pick|{result['url']}"
            )])
        
        await status.edit_text(
            f"🎬 نتائج البحث عن '{query}':\n",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error("خطأ: %s", e)
        await status.edit_text("❌ حدث خطأ في البحث.")


async def callback_sc_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, url = query.data.split("|", 1)
    status = await query.message.reply_text("⏳ جارٍ التحميل...")
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _download_media, url, True)
        await status.edit_text("📤 جارٍ الإرسال...")
        await send_media(query.message, info["path"], info, True)
        await status.delete()
    except Exception as e:
        logger.error("خطأ: %s", e)
        await status.edit_text("❌ تعذّر التحميل.")


async def callback_yt_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, url = query.data.split("|", 1)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎵 صوت فقط", callback_data=f"dl_audio|{url}"),
        InlineKeyboardButton("🎬 فيديو",    callback_data=f"dl_video|{url}"),
    ]])
    await query.message.edit_text("شو تبي؟", reply_markup=keyboard)
