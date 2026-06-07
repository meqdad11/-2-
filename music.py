import logging
import os
import asyncio
import tempfile
import aiohttp
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB حد تيليغرام

# ========================================
# دوال مساعدة
# ========================================

def _is_media_url(text: str) -> bool:
    """تحقق إذا كان النص رابط وسائط مدعوم"""
    supported = [
        "soundcloud.com", "tiktok.com", "instagram.com",
        "twitter.com", "x.com", "facebook.com", "fb.watch",
        "vimeo.com", "dailymotion.com", "twitch.tv",
        "reddit.com", "pinterest.com", "tumblr.com",
        "bilibili.com", "nicovideo.jp", "streamable.com",
    ]
    text = text.strip().lower()
    if not text.startswith("http"):
        return False
    return any(domain in text for domain in supported)

async def _download_media(url: str, audio_only: bool = False) -> tuple[str, str]:
    """
    تحميل الميديا باستخدام yt-dlp
    يرجع (مسار الملف, اسم الملف)
    """
    tmp_dir = tempfile.mkdtemp()

    if audio_only:
        ydl_opts = [
            "yt-dlp",
            "--no-playlist",
            "-x", "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", f"{tmp_dir}/%(title)s.%(ext)s",
            "--max-filesize", "50m",
            url
        ]
    else:
        ydl_opts = [
            "yt-dlp",
            "--no-playlist",
            "-f", "best[filesize<50M]/best",
            "-o", f"{tmp_dir}/%(title)s.%(ext)s",
            "--max-filesize", "50m",
            url
        ]

    proc = await asyncio.create_subprocess_exec(
        *ydl_opts,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.error(f"yt-dlp error: {stderr.decode()}")
        raise Exception("فشل التحميل")

    # إيجاد الملف المحمّل
    files = list(Path(tmp_dir).iterdir())
    if not files:
        raise Exception("لم يُنشأ ملف")

    file_path = str(files[0])
    file_name = files[0].name
    return file_path, file_name

# ========================================
# البحث في YouTube عبر Invidious
# ========================================

async def _search_youtube(query: str, limit: int = 5) -> list:
    """البحث في يوتيوب عبر Invidious API"""
    instances = [
        "https://invidious.nerdvpn.de",
        "https://inv.nadeko.net",
        "https://invidious.privacydev.net",
    ]

    for instance in instances:
        try:
            url = f"{instance}/api/v1/search?q={query}&type=video&fields=title,videoId,author,lengthSeconds"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = []
                        for item in data[:limit]:
                            duration = item.get("lengthSeconds", 0)
                            mins = duration // 60
                            secs = duration % 60
                            results.append({
                                "title": item.get("title", "بدون عنوان"),
                                "video_id": item.get("videoId", ""),
                                "author": item.get("author", ""),
                                "duration": f"{mins}:{secs:02d}",
                                "url": f"https://www.youtube.com/watch?v={item.get('videoId', '')}",
                            })
                        return results
        except Exception as e:
            logger.warning(f"Invidious instance {instance} failed: {e}")
            continue

    return []

# ========================================
# البحث في SoundCloud
# ========================================

async def _search_soundcloud(query: str, limit: int = 5) -> list:
    """البحث في SoundCloud عبر API غير رسمي"""
    try:
        search_url = f"https://api-v2.soundcloud.com/search/tracks?q={query}&limit={limit}&client_id=a3e059563d7fd3372b49b37f00a00bcf"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
            async with session.get(search_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    for item in data.get("collection", [])[:limit]:
                        duration = item.get("duration", 0) // 1000
                        mins = duration // 60
                        secs = duration % 60
                        results.append({
                            "title": item.get("title", "بدون عنوان"),
                            "author": item.get("user", {}).get("username", ""),
                            "duration": f"{mins}:{secs:02d}",
                            "url": item.get("permalink_url", ""),
                        })
                    return results
    except Exception as e:
        logger.error(f"SoundCloud search error: {e}")
    return []

# ========================================
# الأوامر الرئيسية
# ========================================

async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /download"""
    if not context.args:
        await update.message.reply_text("📎 أرسل الرابط مباشرة في المحادثة أو استخدم:\n/download [رابط]")
        return
    url = context.args[0]
    await _handle_url(update, context, url)

async def cmd_yt_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بحث يوتيوب"""
    if not context.args:
        await update.message.reply_text("🔍 استخدم: /ytsearch [كلمة البحث]")
        return
    query = " ".join(context.args)
    msg = await update.message.reply_text("🔍 جارٍ البحث في يوتيوب...")
    results = await _search_youtube(query)
    if not results:
        await msg.edit_text("❌ لم تُوجد نتائج.")
        return
    keyboard = []
    for i, r in enumerate(results):
        label = f"🎬 {r['title'][:35]} | {r['duration']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"yt_pick|{i}")])
    context.user_data["yt_results"] = results
    await msg.edit_text(
        f"🎬 نتائج البحث عن: *{query}*\nاختر ما تريد تحميله:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def cmd_sc_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بحث SoundCloud"""
    if not context.args:
        await update.message.reply_text("🔍 استخدم: /scsearch [كلمة البحث]")
        return
    query = " ".join(context.args)
    msg = await update.message.reply_text("🔍 جارٍ البحث في SoundCloud...")
    results = await _search_soundcloud(query)
    if not results:
        await msg.edit_text("❌ لم تُوجد نتائج.")
        return
    keyboard = []
    for i, r in enumerate(results):
        label = f"🎵 {r['title'][:35]} | {r['duration']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"sc_pick|{i}")])
    context.user_data["sc_results"] = results
    await msg.edit_text(
        f"🎵 نتائج البحث عن: *{query}*\nاختر ما تريد تحميله:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ========================================
# معالجة الروابط التلقائية
# ========================================

async def handle_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اكتشاف الروابط تلقائياً في الرسائل"""
    msg = update.message
    if not msg or not msg.text:
        return
    text = msg.text.strip()
    if not _is_media_url(text):
        return
    await _handle_url(update, context, text)

async def _handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """معالجة رابط وعرض خيارات التحميل"""
    keyboard = [
        [
            InlineKeyboardButton("🎵 صوت", callback_data=f"dl_audio|{url}"),
            InlineKeyboardButton("🎬 فيديو", callback_data=f"dl_video|{url}"),
        ]
    ]
    await update.message.reply_text(
        f"🔗 تم اكتشاف رابط\nاختر صيغة التحميل:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================================
# معالجة الأزرار
# ========================================

async def callback_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحميل صوت أو فيديو من رابط"""
    query = update.callback_query
    await query.answer()
    data = query.data  # dl_audio|URL أو dl_video|URL
    parts = data.split("|", 1)
    if len(parts) != 2:
        return
    mode, url = parts
    audio_only = mode == "dl_audio"

    await query.message.edit_text("⏳ جارٍ التحميل...")

    try:
        file_path, file_name = await _download_media(url, audio_only=audio_only)
        file_size = os.path.getsize(file_path)

        if file_size > MAX_FILE_SIZE:
            await query.message.edit_text("❌ الملف أكبر من 50MB.")
            os.remove(file_path)
            return

        await query.message.edit_text("📤 جارٍ الرفع...")
        with open(file_path, "rb") as f:
            if audio_only:
                await query.message.reply_audio(audio=f, title=file_name)
            else:
                await query.message.reply_video(video=f)
        await query.message.delete()
        os.remove(file_path)

    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.message.edit_text("❌ فشل التحميل. تأكد من صحة الرابط.")

async def callback_yt_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختيار نتيجة يوتيوب"""
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("|")[1])
    results = context.user_data.get("yt_results", [])
    if not results or idx >= len(results):
        await query.message.edit_text("❌ انتهت صلاحية النتائج.")
        return
    url = results[idx]["url"]
    keyboard = [
        [
            InlineKeyboardButton("🎵 صوت", callback_data=f"dl_audio|{url}"),
            InlineKeyboardButton("🎬 فيديو", callback_data=f"dl_video|{url}"),
        ]
    ]
    await query.message.edit_text(
        f"🎬 *{results[idx]['title']}*\nاختر الصيغة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def callback_sc_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختيار نتيجة SoundCloud"""
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("|")[1])
    results = context.user_data.get("sc_results", [])
    if not results or idx >= len(results):
        await query.message.edit_text("❌ انتهت صلاحية النتائج.")
        return
    url = results[idx]["url"]
    keyboard = [
        [
            InlineKeyboardButton("🎵 صوت", callback_data=f"dl_audio|{url}"),
            InlineKeyboardButton("🎬 فيديو", callback_data=f"dl_video|{url}"),
        ]
    ]
    await query.message.edit_text(
        f"🎵 *{results[idx]['title']}*\nاختر الصيغة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def callback_sc_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """للتوافق مع main.py"""
    await callback_download(update, context)
