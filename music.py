import logging
import os
import asyncio
import tempfile
import re
import aiohttp
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
CHANNEL_URL = "https://t.me/shafaqmeqdad"

# ========================================
# تصنيف الدومينات
# ========================================

AUDIO_ONLY_DOMAINS = ["soundcloud.com"]

VIDEO_ONLY_DOMAINS = [
    "tiktok.com", "vt.tiktok.com",
    "instagram.com",
    "twitter.com", "x.com",
    "facebook.com", "fb.watch",
    "vimeo.com", "dailymotion.com",
    "twitch.tv", "reddit.com",
    "streamable.com", "bilibili.com",
]

BOTH_DOMAINS = []  # يوتيوب وما شابه

SUPPORTED_DOMAINS = AUDIO_ONLY_DOMAINS + VIDEO_ONLY_DOMAINS + BOTH_DOMAINS

def _detect_mode(url: str) -> str:
    """أرجع: 'audio' أو 'video' أو 'both'"""
    url_lower = url.lower()
    if any(d in url_lower for d in AUDIO_ONLY_DOMAINS):
        return "audio"
    if any(d in url_lower for d in VIDEO_ONLY_DOMAINS):
        return "video"
    return "both"

# ========================================
# استخراج الروابط من النص
# ========================================

def _extract_url(text: str) -> str | None:
    urls = re.findall(r'https?://\S+', text)
    for url in urls:
        url = url.rstrip(')')
        if any(domain in url for domain in SUPPORTED_DOMAINS):
            return url
    return None

def _is_media_url(text: str) -> str | None:
    text = text.strip()
    if text.startswith("http") and any(d in text for d in SUPPORTED_DOMAINS):
        return text.split()[0]
    return _extract_url(text)

# ========================================
# التحميل عبر yt-dlp
# ========================================

async def _download_media(url: str, audio_only: bool = False) -> tuple[str, str]:
    tmp_dir = tempfile.mkdtemp()

    if audio_only:
        cmd = [
            "yt-dlp", "--no-playlist",
            "-x", "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", f"{tmp_dir}/%(title)s.%(ext)s",
            "--max-filesize", "50m",
            "--no-warnings",
            url
        ]
    else:
        cmd = [
            "yt-dlp", "--no-playlist",
            "-f", "best[filesize<50M]/best",
            "-o", f"{tmp_dir}/%(title)s.%(ext)s",
            "--max-filesize", "50m",
            "--no-warnings",
            url
        ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        err = stderr.decode()
        logger.error(f"yt-dlp error: {err}")
        raise Exception(err)

    files = list(Path(tmp_dir).iterdir())
    if not files:
        raise Exception("لم يُنشأ ملف")

    return str(files[0]), files[0].name

# ========================================
# البحث في YouTube
# ========================================

INVIDIOUS_INSTANCES = [
    "https://invidious.nerdvpn.de",
    "https://inv.nadeko.net",
    "https://invidious.privacydev.net",
    "https://yt.artemislena.eu",
    "https://invidious.flokinet.to",
]

async def _search_youtube(query: str, limit: int = 5) -> list:
    for instance in INVIDIOUS_INSTANCES:
        try:
            url = f"{instance}/api/v1/search?q={query}&type=video&fields=title,videoId,author,lengthSeconds"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
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
                        if results:
                            return results
        except Exception as e:
            logger.warning(f"Invidious {instance} failed: {e}")
            continue
    return []

# ========================================
# البحث في SoundCloud
# ========================================

SC_CLIENT_IDS = [
    "a3e059563d7fd3372b49b37f00a00bcf",
    "iZIs9mchVcX5lhVRyQGGAYlNPVldzAoX",
    "2t9loNQH90kzJcsFCODdigxfp325aq4z",
]

async def _search_soundcloud(query: str, limit: int = 5) -> list:
    for client_id in SC_CLIENT_IDS:
        try:
            url = f"https://api-v2.soundcloud.com/search/tracks?q={query}&limit={limit}&client_id={client_id}"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as resp:
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
                        if results:
                            return results
        except Exception as e:
            logger.warning(f"SC client_id {client_id} failed: {e}")
            continue

    # fallback عبر yt-dlp
    try:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", f"scsearch{limit}:{query}",
            "--print", "%(title)s|||%(webpage_url)s|||%(duration)s|||%(uploader)s",
            "--no-playlist", "--no-warnings",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        results = []
        for line in stdout.decode().strip().split("\n"):
            parts = line.split("|||")
            if len(parts) >= 2:
                duration = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
                mins = duration // 60
                secs = duration % 60
                results.append({
                    "title": parts[0],
                    "author": parts[3] if len(parts) > 3 else "",
                    "duration": f"{mins}:{secs:02d}",
                    "url": parts[1],
                })
        return results
    except Exception as e:
        logger.error(f"SC yt-dlp search failed: {e}")
        return []

# ========================================
# الأوامر
# ========================================

async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("📎 أرسل رابطاً مباشرة أو: حمل [رابط]")
        return
    url = context.args[0]
    await _handle_url(update, context, url)

async def cmd_yt_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔍 استخدم: يوت [كلمة البحث]")
        return
    query = " ".join(context.args)
    msg = await update.message.reply_text("🔍 جارٍ البحث في يوتيوب...")
    results = await _search_youtube(query)
    if not results:
        await msg.edit_text("❌ لم تُوجد نتائج. جرب كلمة أخرى.")
        return
    keyboard = []
    for i, r in enumerate(results):
        label = f"🎬 {r['title'][:38]} | {r['duration']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"yt_pick|{i}")])
    context.user_data["yt_results"] = results
    await msg.edit_text(
        f"🎬 نتائج: *{query}*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def cmd_sc_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔍 استخدم: بحث [كلمة البحث]")
        return
    query = " ".join(context.args)
    msg = await update.message.reply_text("🔍 جارٍ البحث في SoundCloud...")
    results = await _search_soundcloud(query)
    if not results:
        await msg.edit_text("❌ لم تُوجد نتائج. جرب كلمة أخرى.")
        return
    keyboard = []
    for i, r in enumerate(results):
        label = f"🎵 {r['title'][:38]} | {r['duration']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"sc_pick|{i}")])
    context.user_data["sc_results"] = results
    await msg.edit_text(
        f"🎵 نتائج: *{query}*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ========================================
# معالجة الروابط التلقائية
# ========================================

async def handle_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    url = _is_media_url(msg.text)
    if not url:
        return
    await _handle_url(update, context, url)

async def _handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    mode = _detect_mode(url)

    if mode == "audio":
        # تحميل مباشر بدون خيار
        keyboard = [[
            InlineKeyboardButton("🎵 تحميل صوت", callback_data=f"dl_audio|{url}"),
        ]]
    elif mode == "video":
        keyboard = [[
            InlineKeyboardButton("🎬 تحميل فيديو", callback_data=f"dl_video|{url}"),
            InlineKeyboardButton("🎵 صوت فقط", callback_data=f"dl_audio|{url}"),
        ]]
    else:
        keyboard = [[
            InlineKeyboardButton("🎵 صوت", callback_data=f"dl_audio|{url}"),
            InlineKeyboardButton("🎬 فيديو", callback_data=f"dl_video|{url}"),
        ]]

    await update.message.reply_text(
        "🔗 اختر صيغة التحميل:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================================
# زر القناة
# ========================================

def _channel_markup():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📢 قناة تحديثات شفق", url=CHANNEL_URL)
    ]])

# ========================================
# معالجة الأزرار
# ========================================

async def callback_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("|", 1)
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
                await query.message.reply_audio(
                    audio=f,
                    title=file_name,
                    reply_markup=_channel_markup()
                )
            else:
                await query.message.reply_video(
                    video=f,
                    reply_markup=_channel_markup()
                )
        await query.message.delete()
        os.remove(file_path)

    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.message.edit_text("❌ فشل التحميل. تأكد من صحة الرابط.")

async def callback_yt_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("|")[1])
    results = context.user_data.get("yt_results", [])
    if not results or idx >= len(results):
        await query.message.edit_text("❌ انتهت صلاحية النتائج.")
        return
    url = results[idx]["url"]
    # يوتيوب يدعم الاثنين
    keyboard = [[
        InlineKeyboardButton("🎵 صوت", callback_data=f"dl_audio|{url}"),
        InlineKeyboardButton("🎬 فيديو", callback_data=f"dl_video|{url}"),
    ]]
    await query.message.edit_text(
        f"🎬 *{results[idx]['title']}*\nاختر الصيغة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def callback_sc_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("|")[1])
    results = context.user_data.get("sc_results", [])
    if not results or idx >= len(results):
        await query.message.edit_text("❌ انتهت صلاحية النتائج.")
        return
    url = results[idx]["url"]
    # ساوند كلاود صوت فقط
    keyboard = [[
        InlineKeyboardButton("🎵 تحميل صوت", callback_data=f"dl_audio|{url}"),
    ]]
    await query.message.edit_text(
        f"🎵 *{results[idx]['title']}*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def callback_sc_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await callback_download(update, context)
