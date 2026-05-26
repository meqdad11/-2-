import asyncio
import logging
import os
import tempfile

import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

MAX_FILE_MB = 45

SUPPORTED_DOMAINS = (
    "youtube.com", "youtu.be",
    "tiktok.com",
    "instagram.com",
    "soundcloud.com",
)

def is_media_url(text: str) -> bool:
    text = text.strip()
    if not (text.startswith("http://") or text.startswith("https://")):
        return False
    return any(d in text for d in SUPPORTED_DOMAINS)

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
        }
    else:
        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": os.path.join(tmp_dir, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if "entries" in info:
            info = info["entries"][0]
    title = info.get("title", "media")
    duration = info.get("duration", 0)
    uploader = info.get("uploader", "")
    for fname in os.listdir(tmp_dir):
        return {"path": os.path.join(tmp_dir, fname), "title": title,
                "duration": duration, "uploader": uploader}
    raise FileNotFoundError("لم يُنشأ الملف")
def _search_soundcloud(query: str, max_results: int = 5) -> list:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }
    search = f"scsearch{max_results}:{query}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search, download=False)
        entries = info.get("entries", []) if info else []
        results = []
        for e in entries:
            if e:
                results.append({
                    "title":    e.get("title", "بدون عنوان"),
                    "uploader": e.get("uploader", ""),
                    "duration": e.get("duration", 0),
                    "url":      e.get("url") or e.get("webpage_url", ""),
                })
        return results


def _search_youtube(query: str, max_results: int = 5) -> list:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }
    search = f"ytsearch{max_results}:{query}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search, download=False)
        entries = info.get("entries", []) if info else []
        results = []
        for e in entries:
            if e:
                results.append({
                    "title":    e.get("title", "بدون عنوان"),
                    "uploader": e.get("uploader", e.get("channel", "")),
                    "duration": e.get("duration", 0),
                    "url":      f"https://youtube.com/watch?v={e.get('id', '')}",
                })
        return results
async def handle_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    url = msg.text.strip()
    if not is_media_url(url):
        return
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
        path = info["path"]
        if os.path.getsize(path) > MAX_FILE_MB * 1024 * 1024:
            await status.edit_text("❌ الملف أكبر من 45MB.")
            os.remove(path)
            return
        await status.edit_text("📤 جارٍ الإرسال...")
        with open(path, "rb") as f:
            if audio_only:
                await query.message.reply_audio(
                    audio=f, title=info["title"],
                    performer=info["uploader"], duration=info["duration"],
                )
            else:
                await query.message.reply_video(video=f, caption=info["title"])
        await status.delete()
        os.remove(path)
    except Exception as e:
        logger.error("خطأ تحميل: %s", e)
        await status.edit_text("❌ تعذّر التحميل.")
async def cmd_sc_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: بحث <اسم الأغنية>")
        return
    query = " ".join(context.args)
    status = await update.message.reply_text(f"🔍 جارٍ البحث عن: {query}")
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _search_soundcloud, query)
        if not results:
            await status.edit_text("❌ لم يُعثر على نتائج.")
            return
        buttons = []
        for i, r in enumerate(results):
            dur = fmt_dur(r["duration"])
            label = f"{i+1}. {r['title'][:35]} — {dur}"
            buttons.append([InlineKeyboardButton(label, callback_data=f"sc_dl|{r['url']}")])
        await status.edit_text(
            f"🎵 نتائج البحث: {query}\nاختر أغنية:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception as e:
        logger.error("خطأ بحث ساوند كلاود: %s", e)
        await status.edit_text("❌ حدث خطأ أثناء البحث.")


async def callback_sc_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, url = query.data.split("|", 1)
    status = await query.message.reply_text("⏳ جارٍ التحميل من SoundCloud...")
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _download_media, url, True)
        path = info["path"]
        if os.path.getsize(path) > MAX_FILE_MB * 1024 * 1024:
            await status.edit_text("❌ الملف أكبر من 45MB.")
            os.remove(path)
            return
        await status.edit_text("📤 جارٍ الإرسال...")
        with open(path, "rb") as f:
            await query.message.reply_audio(
                audio=f, title=info["title"],
                performer=info["uploader"], duration=info["duration"],
            )
        await status.delete()
        os.remove(path)
    except Exception as e:
        logger.error("خطأ تحميل ساوند كلاود: %s", e)
        await status.edit_text("❌ تعذّر التحميل.")
async def cmd_yt_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: يوتيوب <اسم الفيديو>")
        return
    query = " ".join(context.args)
    status = await update.message.reply_text(f"🔍 جارٍ البحث في يوتيوب: {query}")
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _search_youtube, query)
        if not results:
            await status.edit_text("❌ لم يُعثر على نتائج.")
            return
        buttons = []
        for i, r in enumerate(results):
            dur = fmt_dur(r["duration"])
            label = f"{i+1}. {r['title'][:35]} — {dur}"
            buttons.append([InlineKeyboardButton(label, callback_data=f"yt_pick|{r['url']}")])
        await status.edit_text(
            f"🎬 نتائج يوتيوب: {query}\nاختر:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception as e:
        logger.error("خطأ بحث يوتيوب: %s", e)
        await status.edit_text("❌ حدث خطأ أثناء البحث.")


async def callback_yt_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, url = query.data.split("|", 1)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎵 صوت فقط", callback_data=f"dl_audio|{url}"),
        InlineKeyboardButton("🎬 فيديو",    callback_data=f"dl_video|{url}"),
    ]])
    await query.message.reply_text("شو تبي؟", reply_markup=keyboard)


async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "الاستخدام:\n"
            "أرسل رابط مباشرة للتحميل\n"
            "بحث <اسم الأغنية> — للبحث في ساوند كلاود\n"
            "يوتيوب <اسم الفيديو> — للبحث في يوتيوب"
        )
        return
    url = " ".join(context.args).strip()
    if not is_media_url(url):
        await update.message.reply_text("❌ الرابط غير مدعوم.")
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎵 صوت فقط", callback_data=f"dl_audio|{url}"),
        InlineKeyboardButton("🎬 فيديو",    callback_data=f"dl_video|{url}"),
    ]])
    await update.message.reply_text("شو تبي أحمل؟", reply_markup=keyboard)