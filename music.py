import asyncio
import logging
import os
import tempfile
import subprocess

import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

MAX_FILE_MB = 45
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024

# إضافة منصات جديدة
SUPPORTED_DOMAINS = (
    "youtube.com", "youtu.be",
    "tiktok.com", "vm.tiktok.com",
    "instagram.com", "instagr.am",
    "soundcloud.com",
    "twitter.com", "x.com",
    "facebook.com", "fb.watch",
    "spotify.com",
    "deezer.com",
)

def is_media_url(text: str) -> bool:
    text = text.strip()
    if not (text.startswith("http://") or text.startswith("https://")):
        return False
    return any(d in text for d in SUPPORTED_DOMAINS)

def fmt_dur(seconds) -> str:
    try:
        s = int(seconds)
        if s >= 3600:
            return f"{s//3600}:{(s%3600)//60:02d}:{s%60:02d}"
        return f"{s//60}:{s%60:02d}"
    except Exception:
        return ""

def compress_video(input_path: str, output_path: str) -> bool:
    """ضغط الفيديو إذا كان كبير"""
    try:
        cmd = [
            "ffmpeg", "-i", input_path,
            "-vf", "scale=480:-2",
            "-c:v", "libx264", "-crf", "28", "-preset", "fast",
            "-c:a", "aac", "-b:a", "96k",
            "-movflags", "+faststart",
            "-y", output_path
        ]
        subprocess.run(cmd, capture_output=True, timeout=300)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.warning("فشل الضغط: %s", e)
        return False

def compress_audio(input_path: str, output_path: str) -> bool:
    """ضغط الصوت إذا كان كبير"""
    try:
        cmd = [
            "ffmpeg", "-i", input_path,
            "-c:a", "libmp3lame", "-b:a", "96k",
            "-y", output_path
        ]
        subprocess.run(cmd, capture_output=True, timeout=300)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.warning("فشل ضغط الصوت: %s", e)
        return False
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
            "cookiefile": None,
            "geo_bypass": True,
            "extractor_retries": 3,
        }
    else:
        ydl_opts = {
            "format": "best[ext=mp4]/best[height<=720]/best",
            "outtmpl": os.path.join(tmp_dir, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "cookiefile": None,
            "geo_bypass": True,
            "extractor_retries": 3,
        }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if "entries" in info:
                info = info["entries"][0]
            
            title = info.get("title", "media")
            duration = info.get("duration", 0)
            uploader = info.get("uploader", info.get("channel", ""))
            
            for fname in os.listdir(tmp_dir):
                fpath = os.path.join(tmp_dir, fname)
                if os.path.isfile(fpath):
                    return {
                        "path": fpath,
                        "title": title,
                        "duration": duration,
                        "uploader": uploader,
                        "tmp_dir": tmp_dir
                    }
            raise FileNotFoundError("لم يُنشأ الملف")
    except Exception as e:
        for f in os.listdir(tmp_dir):
            try:
                os.remove(os.path.join(tmp_dir, f))
            except:
                pass
        os.rmdir(tmp_dir)
        raise e

def _search_soundcloud(query: str, max_results: int = 5) -> list:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "geo_bypass": True,
    }
    search = f"scsearch{max_results}:{query}"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search, download=False)
            entries = info.get("entries", []) if info else []
            results = []
            for e in entries:
                if e:
                    results.append({
                        "title": e.get("title", "بدون عنوان"),
                        "uploader": e.get("uploader", ""),
                        "duration": e.get("duration", 0),
                        "url": e.get("url") or e.get("webpage_url", ""),
                    })
            return results
    except Exception as e:
        logger.warning("فشل بحث ساوند كلاود: %s", e)
        try:
            ydl_opts["extract_flat"] = False
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search, download=False)
                entries = info.get("entries", []) if info else []
                results = []
                for e in entries:
                    if e:
                        results.append({
                            "title": e.get("title", "بدون عنوان"),
                            "uploader": e.get("uploader", ""),
                            "duration": e.get("duration", 0),
                            "url": e.get("webpage_url", e.get("url", "")),
                        })
                return results
        except Exception as e2:
            logger.error("فشل بحث ساوند كلاود نهائياً: %s", e2)
            return []

def _search_youtube(query: str, max_results: int = 5) -> list:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "geo_bypass": True,
    }
    search = f"ytsearch{max_results}:{query}"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search, download=False)
            entries = info.get("entries", []) if info else []
            results = []
            for e in entries:
                if e:
                    results.append({
                        "title": e.get("title", "بدون عنوان"),
                        "uploader": e.get("uploader", e.get("channel", "")),
                        "duration": e.get("duration", 0),
                        "url": f"https://youtube.com/watch?v={e.get('id', '')}",
                    })
            return results
    except Exception as e:
        logger.error("خطأ بحث يوتيوب: %s", e)
        return []
async def handle_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    url = msg.text.strip()
    if not is_media_url(url):
        return
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎵 صوت فقط", callback_data=f"dl_audio|{url}"),
        InlineKeyboardButton("🎬 فيديو", callback_data=f"dl_video|{url}"),
    ]])
    await msg.reply_text("شو تبي أحمل؟", reply_markup=keyboard)

async def callback_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, url = query.data.split("|", 1)
    audio_only = action == "dl_audio"
    
    status = await query.message.reply_text("⏳ جارٍ التحميل...")
    tmp_dir = None
    
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _download_media, url, audio_only)
        path = info["path"]
        tmp_dir = info.get("tmp_dir")
        file_size = os.path.getsize(path)
        
        if file_size > MAX_FILE_BYTES:
            await status.edit_text("📦 الملف كبير، جارٍ الضغط...")
            
            compressed_path = os.path.join(tmp_dir, "compressed_" + os.path.basename(path))
            
            if audio_only:
                success = compress_audio(path, compressed_path)
            else:
                success = compress_video(path, compressed_path)
            
            if success and os.path.getsize(compressed_path) <= MAX_FILE_BYTES:
                path = compressed_path
                file_size = os.path.getsize(path)
            else:
                await status.edit_text(
                    f"❌ الملف كبير جداً ({file_size // (1024*1024)}MB).\n"
                    f"الحد الأقصى: {MAX_FILE_MB}MB حتى بعد الضغط."
                )
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
        
    except Exception as e:
        logger.error("خطأ تحميل: %s", e)
        error_msg = str(e)
        if "Sign in to confirm" in error_msg:
            await status.edit_text("❌ يوتيوب يطلب تسجيل الدخول. جرب رابط آخر.")
        elif "Unsupported URL" in error_msg:
            await status.edit_text("❌ الرابط غير مدعوم حالياً.")
        elif "Private video" in error_msg:
            await status.edit_text("❌ الفيديو خاص أو محذوف.")
        else:
            await status.edit_text(f"❌ تعذّر التحميل: {error_msg[:100]}")
    finally:
        if tmp_dir and os.path.exists(tmp_dir):
            for f in os.listdir(tmp_dir):
                try:
                    os.remove(os.path.join(tmp_dir, f))
                except:
                    pass
            try:
                os.rmdir(tmp_dir)
            except:
                pass

async def cmd_sc_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: بحث <اسم الأغنية>")
        return
    
    query = " ".join(context.args)
    status = await update.message.reply_text(f"🔍 جارٍ البحث عن: {query}")
    
    try:
        loop = asyncio.get_event_loop()
        
        yt_results = await loop.run_in_executor(None, _search_youtube, query, 5)
        
        sc_results = []
        try:
            sc_results = await loop.run_in_executor(None, _search_soundcloud, query, 5)
        except Exception as e:
            logger.warning("بحث ساوند كلاود فشل: %s", e)
        
        results = yt_results + sc_results
        
        if not results:
            await status.edit_text("❌ لم يُعثر على نتائج. جرب كلمات مختلفة.")
            return
        
        buttons = []
        for i, r in enumerate(results[:8]):
            dur = fmt_dur(r["duration"])
            source = "🎵" if "soundcloud" in r["url"] else "▶️"
            label = f"{source} {r['title'][:30]} — {dur}"
            buttons.append([InlineKeyboardButton(label, callback_data=f"sc_dl|{r['url']}")])
        
        await status.edit_text(
            f"نتائج البحث: {query}\nاختر:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception as e:
        logger.error("خطأ بحث: %s", e)
        await status.edit_text(f"❌ حدث خطأ: {str(e)[:200]}")

async def callback_sc_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, url = query.data.split("|", 1)
    
    status = await query.message.reply_text("⏳ جارٍ التحميل...")
    tmp_dir = None
    
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _download_media, url, True)
        path = info["path"]
        tmp_dir = info.get("tmp_dir")
        file_size = os.path.getsize(path)
        
        if file_size > MAX_FILE_BYTES:
            compressed_path = os.path.join(tmp_dir, "compressed.mp3")
            if compress_audio(path, compressed_path) and os.path.getsize(compressed_path) <= MAX_FILE_BYTES:
                path = compressed_path
            else:
                await status.edit_text(f"❌ الملف كبير ({file_size // (1024*1024)}MB).")
                return
        
        await status.edit_text("📤 جارٍ الإرسال...")
        
        with open(path, "rb") as f:
            await query.message.reply_audio(
                audio=f, title=info["title"],
                performer=info["uploader"], duration=info["duration"],
            )
        await status.delete()
        
    except Exception as e:
        logger.error("خطأ تحميل: %s", e)
        await status.edit_text(f"❌ تعذّر التحميل: {str(e)[:100]}")
    finally:
        if tmp_dir and os.path.exists(tmp_dir):
            for f in os.listdir(tmp_dir):
                try:
                    os.remove(os.path.join(tmp_dir, f))
                except:
                    pass
            try:
                os.rmdir(tmp_dir)
            except:
                pass

async def cmd_yt_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: يوتيوب <اسم الفيديو>")
        return
    
    query = " ".join(context.args)
    status = await update.message.reply_text(f"🔍 جارٍ البحث في يوتيوب: {query}")
    
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _search_youtube, query, 8)
        
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
        await status.edit_text(f"❌ حدث خطأ: {str(e)[:200]}")

async def callback_yt_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, url = query.data.split("|", 1)
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎵 صوت فقط", callback_data=f"dl_audio|{url}"),
        InlineKeyboardButton("🎬 فيديو", callback_data=f"dl_video|{url}"),
    ]])
    await query.message.reply_text("هل تبغاها؟", reply_markup=keyboard)

async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "الاستخدام:\n"
            "أرسل رابط مباشرة للتحميل\n"
            "بحث <اسم الأغنية> — للبحث\n"
            "يوتيوب <اسم الفيديو> — للبحث في يوتيوب"
        )
        return
    
    url = " ".join(context.args).strip()
    if not is_media_url(url):
        await update.message.reply_text("❌ الرابط غير مدعوم.\nالمنصات المدعومة: يوتيوب، تيك توك، انستقرام، ساوند كلاود، تويتر، فيسبوك")
        return
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎵 صوت فقط", callback_data=f"dl_audio|{url}"),
        InlineKeyboardButton("🎬 فيديو", callback_data=f"dl_video|{url}"),
    ]])
    await update.message.reply_text("شو تبي أحمل؟", reply_markup=keyboard)
