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

# قائمة بخوادم Cobalt المحدثة والمختارة لتجاوز القيود
COBALT_INSTANCES = [
    "https://api.cobalt.tools/api/json",
    "https://cobalt.sh/api/json",
    "https://co.wuk.sh/api/json",
    "https://api.v0.cobalt.tools/api/json"
]

# ========================================
# تصنيف المواقع
# ========================================

AUDIO_ONLY_DOMAINS = ["soundcloud.com"]
VIDEO_ONLY_DOMAINS = ["tiktok.com", "vt.tiktok.com", "instagram.com", "twitter.com", "x.com"]
YOUTUBE_DOMAINS = ["youtube.com", "youtu.be"]
BOTH_DOMAINS = ["facebook.com", "fb.watch", "vimeo.com", "dailymotion.com", "twitch.tv", "reddit.com", "streamable.com", "bilibili.com"]

SUPPORTED_DOMAINS = AUDIO_ONLY_DOMAINS + VIDEO_ONLY_DOMAINS + YOUTUBE_DOMAINS + BOTH_DOMAINS

def _detect_mode(url: str):
    if any(d in url for d in AUDIO_ONLY_DOMAINS):
        return "audio"
    if any(d in url for d in VIDEO_ONLY_DOMAINS):
        return "video"
    if any(d in url for d in YOUTUBE_DOMAINS):
        return "youtube"
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
# التحميل عبر Cobalt V3 (تجاوز القيود المتقدم)
# ========================================

async def _cobalt_download(url: str, audio_only: bool = False) -> tuple[str, str]:
    payload = {
        "url": url,
        "downloadMode": "audio" if audio_only else "auto",
        "audioFormat": "mp3",
        "videoQuality": "720",
        "youtubeVideoCodec": "h264",
        "youtubeVideoContainer": "mp4",
        "alwaysProxy": True,  # تفعيل البروكسي دائماً لتجاوز حظر IP
        "disableMetadata": True # تسريع المعالجة
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    last_error = "فشل الاتصال بخوادم التحميل"
    
    for instance in COBALT_INSTANCES:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=50)) as session:
                async with session.post(instance, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                    
                    status = data.get("status")
                    if status == "error":
                        err_code = data.get("error", {}).get("code", "")
                        if "login" in err_code or "sign" in err_code:
                            last_error = "login_required"
                        else:
                            last_error = err_code
                        continue

                    download_url = None
                    filename = "media.mp4"

                    if status in ("redirect", "tunnel"):
                        download_url = data.get("url")
                        filename = data.get("filename", filename)
                    elif status == "local-processing":
                        tunnels = data.get("tunnel", [])
                        if tunnels:
                            download_url = tunnels[0]
                            output = data.get("output", {})
                            filename = output.get("filename", filename)
                    elif status == "picker":
                        items = data.get("picker", [])
                        if items:
                            download_url = items[0].get("url")
                            filename = items[0].get("filename", filename)

                    if download_url:
                        tmp_dir = tempfile.mkdtemp()
                        file_path = f"{tmp_dir}/{filename}"
                        async with session.get(download_url) as file_resp:
                            if file_resp.status == 200:
                                with open(file_path, "wb") as f:
                                    async for chunk in file_resp.content.iter_chunked(1024 * 128):
                                        f.write(chunk)
                                return file_path, filename
        except Exception as e:
            logger.warning(f"Instance {instance} failed: {e}")
            continue

    if last_error == "login_required":
        raise Exception("المنصة تطلب تسجيل دخول إجباري لهذا الرابط. حاول مع رابط آخر.")
    raise Exception(f"فشل التحميل. السبب: {last_error}")

# ========================================
# التحميل عبر yt-dlp
# ========================================

async def _download_media(url: str, audio_only: bool = False) -> tuple[str, str]:
    tmp_dir = tempfile.mkdtemp()
    
    # محاولة التحميل باستخدام yt-dlp مع بروكسي عام إذا كان متاحاً
    common_args = [
        "--no-playlist", "--max-filesize", "50m", "--no-warnings",
        "--geo-bypass", # محاولة تجاوز الحظر الجغرافي
    ]

    if audio_only:
        cmd = ["yt-dlp"] + common_args + [
            "-x", "--audio-format", "mp3", "--audio-quality", "0",
            "-o", f"{tmp_dir}/%(title)s.%(ext)s", url
        ]
    else:
        cmd = ["yt-dlp"] + common_args + [
            "-f", "best[filesize<50M]/best",
            "-o", f"{tmp_dir}/%(title)s.%(ext)s", url
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
# إرسال الملف
# ========================================

def _channel_markup():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📢 قناة تحديثات شفق", url=CHANNEL_URL)
    ]])

async def _send_file(message, file_path: str, file_name: str, audio_only: bool):
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        await message.reply_text("❌ الملف أكبر من 50MB.")
        os.remove(file_path)
        return
    try:
        with open(file_path, "rb") as f:
            if audio_only:
                await message.reply_audio(audio=f, title=file_name, reply_markup=_channel_markup())
            else:
                await message.reply_video(video=f, reply_markup=_channel_markup(), supports_streaming=True)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def _auto_download(message, url: str, audio_only: bool, use_cobalt: bool = True):
    status_msg = await message.reply_text("⏳ جارٍ التحميل...")
    try:
        if use_cobalt:
            try:
                file_path, file_name = await _cobalt_download(url, audio_only=audio_only)
            except Exception as e:
                if "تسجيل دخول" in str(e): raise e
                logger.warning(f"Cobalt failed, fallback to yt-dlp: {e}")
                file_path, file_name = await _download_media(url, audio_only=audio_only)
        else:
            file_path, file_name = await _download_media(url, audio_only=audio_only)

        await status_msg.edit_text("📤 جارٍ الرفع...")
        await _send_file(message, file_path, file_name, audio_only=audio_only)
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Download error: {e}")
        err_str = str(e)
        if "تسجيل دخول" in err_str:
            await status_msg.edit_text("⚠️ هذا الرابط محمي بخصوصية عالية ويطلب تسجيل دخول. يرجى تجربة رابط آخر عام.")
        elif "filesize" in err_str.lower():
            await status_msg.edit_text("❌ حجم الملف يتجاوز 50 ميجابايت.")
        else:
            await status_msg.edit_text("❌ فشل التحميل. قد يكون الرابط غير مدعوم أو محظوراً حالياً.")

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
                            results.append({
                                "title": item.get("title", "بدون عنوان"),
                                "video_id": item.get("videoId", ""),
                                "author": item.get("author", ""),
                                "duration": f"{duration // 60}:{duration % 60:02d}",
                                "url": f"https://www.youtube.com/watch?v={item.get('videoId', '')}",
                            })
                        if results: return results
        except: continue
    return []

# ========================================
# البحث في SoundCloud
# ========================================

SC_CLIENT_IDS = ["a3e059563d7fd3372b49b37f00a00bcf", "iZIs9mchVcX5lhVRyQGGAYlNPVldzAoX"]

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
                            results.append({
                                "title": item.get("title", "بدون عنوان"),
                                "author": item.get("user", {}).get("username", ""),
                                "duration": f"{duration // 60}:{duration % 60:02d}",
                                "url": item.get("permalink_url", ""),
                            })
                        if results: return results
        except: continue
    return []

# ========================================
# الأوامر ومعالجة الأزرار (نفس منطق الكود الأصلي مع تحسين الاستدعاء)
# ========================================

async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("📎 أرسل رابطاً مباشرة أو: حمل [رابط]")
        return
    await _handle_url(update, context, context.args[0])

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
    keyboard = [[InlineKeyboardButton(f"🎬 {r['title'][:38]} | {r['duration']}", callback_data=f"yt_pick|{i}")] for i, r in enumerate(results)]
    context.user_data["yt_results"] = results
    await msg.edit_text(f"🎬 نتائج: *{query}*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

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
    keyboard = [[InlineKeyboardButton(f"🎵 {r['title'][:38]} | {r['duration']}", callback_data=f"sc_pick|{i}")] for i, r in enumerate(results)]
    context.user_data["sc_results"] = results
    await msg.edit_text(f"🎵 نتائج: *{query}*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def handle_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text: return
    url = _is_media_url(msg.text)
    if url: await _handle_url(update, context, url)

async def _handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    mode = _detect_mode(url)
    keyboard = [[InlineKeyboardButton("🎵 صوت", callback_data=f"dl_audio|{url}"), InlineKeyboardButton("🎬 فيديو", callback_data=f"dl_video|{url}")]]
    if mode == "audio": await _auto_download(update.message, url, audio_only=True)
    elif mode == "video": await _auto_download(update.message, url, audio_only=False)
    else: await update.message.reply_text("🔗 اختر صيغة التحميل:", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("|", 1)
    if len(parts) != 2: return
    mode, url = parts
    await query.message.edit_text("⏳ جارٍ التحميل...")
    try:
        file_path, file_name = await _cobalt_download(url, audio_only=(mode == "dl_audio"))
        await query.message.edit_text("📤 جارٍ الرفع...")
        await _send_file(query.message, file_path, file_name, audio_only=(mode == "dl_audio"))
        await query.message.delete()
    except Exception as e:
        err_msg = str(e)
        if "تسجيل دخول" in err_msg:
            await query.message.edit_text("⚠️ الرابط يطلب تسجيل دخول. جرب رابطاً عاماً.")
        else:
            await query.message.edit_text(f"❌ فشل التحميل: {err_msg}")

async def callback_yt_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("|")[1])
    results = context.user_data.get("yt_results", [])
    if not results or idx >= len(results): return
    url = results[idx]["url"]
    keyboard = [[InlineKeyboardButton("🎵 صوت", callback_data=f"dl_audio|{url}"), InlineKeyboardButton("🎬 فيديو", callback_data=f"dl_video|{url}")]]
    await query.message.edit_text(f"🎬 *{results[idx]['title']}*\nاختر الصيغة:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def callback_sc_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("|")[1])
    results = context.user_data.get("sc_results", [])
    if not results or idx >= len(results): return
    url = results[idx]["url"]
    await query.message.edit_text("⏳ جارٍ التحميل...")
    try:
        file_path, file_name = await _download_media(url, audio_only=True)
        await query.message.edit_text("📤 جارٍ الرفع...")
        await _send_file(query.message, file_path, file_name, audio_only=True)
        await query.message.delete()
    except: await query.message.edit_text("❌ فشل التحميل.")

async def callback_sc_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await callback_download(update, context)
