import asyncio
import logging
import os
import tempfile

import yt_dlp
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

MAX_FILE_MB = 45  # Telegram bot limit is 50MB; leave margin


def _download_audio(query: str) -> dict:
    """Run in a thread — downloads audio and returns info dict."""
    tmp_dir = tempfile.mkdtemp()

    # Determine if query is a URL or a search term
    is_url = query.startswith("http://") or query.startswith("https://")
    search  = query if is_url else f"ytsearch1:{query}"

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

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search, download=True)
        if "entries" in info:
            info = info["entries"][0]

    # Find the downloaded mp3
    title = info.get("title", "audio")
    duration = info.get("duration", 0)
    uploader = info.get("uploader", "")

    # Locate the file
    for fname in os.listdir(tmp_dir):
        if fname.endswith(".mp3"):
            return {
                "path": os.path.join(tmp_dir, fname),
                "title": title,
                "duration": duration,
                "uploader": uploader,
            }

    raise FileNotFoundError("لم يُنشأ ملف الصوت")


async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحميل <رابط أو اسم أغنية>"""
    if not context.args:
        await update.message.reply_text(
            "الاستخدام:\n"
            "تحميل <رابط يوتيوب>\n"
            "تحميل <اسم الأغنية>"
        )
        return

    query = " ".join(context.args).strip()
    status_msg = await update.message.reply_text("⏳ جارٍ البحث والتحميل...")

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _download_audio, query)

        file_path = info["path"]
        file_size = os.path.getsize(file_path)

        if file_size > MAX_FILE_MB * 1024 * 1024:
            await status_msg.edit_text("❌ الملف أكبر من 45MB — جرب أغنية أقصر.")
            os.remove(file_path)
            return

        await status_msg.edit_text("📤 جارٍ الإرسال...")

        with open(file_path, "rb") as f:
            await update.message.reply_audio(
                audio=f,
                title=info["title"],
                performer=info["uploader"],
                duration=info["duration"],
            )

        await status_msg.delete()
        os.remove(file_path)

    except yt_dlp.utils.DownloadError as e:
        logger.warning("خطأ تحميل: %s", e)
        await status_msg.edit_text("❌ تعذّر التحميل — تأكد من الرابط أو اسم الأغنية.")
    except Exception as e:
        logger.error("خطأ غير متوقع في التحميل: %s", e)
        await status_msg.edit_text("❌ حدث خطأ أثناء التحميل.")
