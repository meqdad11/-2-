import logging
import os
import re
import traceback

from telegram import Update, Chat as TGChat
from telegram.ext import (
    Application,
    CommandHandler,
    ChatMemberHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import database as db
from handlers import (
    cmd_start,
    cmd_id,
    cmd_ban,
    cmd_unban,
    cmd_warn,
    cmd_clearwarn,
    cmd_warnings,
    cmd_banlist,
    cmd_baninfo,
    cmd_checkban,
    cmd_eventlog,
    cmd_setrules,
    cmd_rules,
    on_chat_member_updated,
    job_expire_bans,
    track_message,
    cmd_add_word,
    cmd_remove_word,
    cmd_list_words,
    filter_banned_words,
    cmd_mute,
    cmd_unmute,
    cmd_lock,
    cmd_unlock,
)
from music import (
    cmd_download,
    cmd_sc_search,
    cmd_yt_search,
    handle_media_url,
    callback_download,
    callback_sc_download,
    callback_yt_pick,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Arabic slash-command keyword → handler mapping
_ARABIC_CMDS = {
    "ايدي":              cmd_id,
    "حظر":               cmd_ban,
    "رفع الحظر":         cmd_unban,
    "رفع_الحظر":         cmd_unban,
    "تحذير":             cmd_warn,
    "قائمة":             cmd_banlist,
    "معلومات":           cmd_baninfo,
    "تحقق":              cmd_checkban,
    "سجل":               cmd_eventlog,
    "تحميل":             cmd_download,
    "أضف كلمة":          cmd_add_word,
    "احذف كلمة":         cmd_remove_word,
    "الكلمات المحظورة":  cmd_list_words,
    "بحث":               cmd_sc_search,
    "يوتيوب":            cmd_yt_search,
    "كتم":               cmd_mute,
    "رفع الكتم":         cmd_unmute,
    "أغلق المجموعة":     cmd_lock,
    "افتح المجموعة":     cmd_unlock,
}


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("استثناء غير معالج:\n%s", traceback.format_exc())


async def all_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Single catch-all for every text message.

    Routes:
      • /english_command  → CommandHandler takes it (never reaches here)
      • /عربي             → matched below by prefix check
      • plain text        → message count only
    """
    msg = update.message
    if not msg or not msg.text:
        return

    text = msg.text.strip()
    chat_type = update.effective_chat.type if update.effective_chat else None
    user_id = update.effective_user.id if update.effective_user else "?"

    logger.info("رسالة واردة | المستخدم:%s | النوع:%s | النص:%r", user_id, chat_type, text[:60])

    # ── Detect Arabic slash commands (e.g. /حظر, /ايدي) ──────────────────────
    if text.startswith("/"):
        for keyword, func in _ARABIC_CMDS.items():
            if text == f"/{keyword}" or text.startswith(f"/{keyword} "):
                parts = text.split()
                context.args = parts[1:] if len(parts) > 1 else []
                logger.info("أمر عربي بسلاش: /%s", keyword)
                await func(update, context)
                return
        # Starts with / but no match → ignore (unknown command)
        return

    # ── Detect Arabic keywords without slash (e.g. ايدي, حظر 123) ─────────────
    for keyword, func in _ARABIC_CMDS.items():
        if text == keyword or text.startswith(keyword + " "):
            parts = text.split()
            context.args = parts[1:] if len(parts) > 1 else []
            logger.info("أمر عربي بدون سلاش: %s", keyword)
            await func(update, context)
            return

    # (message counting is handled separately in group=1)


async def post_init(application: Application) -> None:
    await db.init_db()
    logger.info("تم تهيئة قاعدة البيانات")
    application.job_queue.run_repeating(job_expire_bans, interval=60, first=10)
    logger.info("تم جدولة مهمة انتهاء مدد الحظر")


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("متغير البيئة TELEGRAM_BOT_TOKEN غير مضبوط")

    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    # ── Error handler ─────────────────────────────────────────────────────────
    app.add_error_handler(error_handler)

    # ── English /commands ─────────────────────────────────────────────────────
    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(CommandHandler("id",        cmd_id))
    app.add_handler(CommandHandler("ban",       cmd_ban))
    app.add_handler(CommandHandler("unban",     cmd_unban))
    app.add_handler(CommandHandler("warn",      cmd_warn))
    app.add_handler(CommandHandler("clearwarn", cmd_clearwarn))
    app.add_handler(CommandHandler("warnings",  cmd_warnings))
    app.add_handler(CommandHandler("banlist",   cmd_banlist))
    app.add_handler(CommandHandler("baninfo",   cmd_baninfo))
    app.add_handler(CommandHandler("checkban",  cmd_checkban))
    app.add_handler(CommandHandler("eventlog",  cmd_eventlog))
    app.add_handler(CommandHandler("setrules",  cmd_setrules))
    app.add_handler(CommandHandler("rules",     cmd_rules))
    app.add_handler(CommandHandler("download",  cmd_download))
    app.add_handler(CommandHandler("addword",   cmd_add_word))
    app.add_handler(CommandHandler("removeword", cmd_remove_word))
    app.add_handler(CommandHandler("wordlist",  cmd_list_words))
    app.add_handler(CommandHandler("mute",      cmd_mute))
    app.add_handler(CommandHandler("unmute",    cmd_unmute))
    app.add_handler(CommandHandler("lock",      cmd_lock))
    app.add_handler(CommandHandler("unlock",    cmd_unlock))
    app.add_handler(CommandHandler("scsearch",  cmd_sc_search))
    app.add_handler(CommandHandler("ytsearch",  cmd_yt_search))

    # ── Callback queries ──────────────────────────────────────────────────────
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(callback_download,    pattern=r"^dl_(audio|video)\|"))
    app.add_handler(CallbackQueryHandler(callback_sc_download, pattern=r"^sc_dl\|"))
    app.add_handler(CallbackQueryHandler(callback_yt_pick,     pattern=r"^yt_pick\|"))

    # ── Banned words filter (group=2) ─────────────────────────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_banned_words), group=2)

    # ── Auto media URL detection (group=3) ────────────────────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_media_url), group=3)

    # ── All text messages (Arabic slash-commands + message counting) ───────────
    app.add_handler(MessageHandler(filters.TEXT, all_messages_handler))

    # ── Message counter (group=1 → fires for ALL text, even after commands) ───
    app.add_handler(MessageHandler(filters.TEXT, track_message), group=1)

    # ── Member join/leave events ──────────────────────────────────────────────
    app.add_handler(
        ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER)
    )

    logger.info("جارٍ تشغيل البوت...")
    app.run_polling(
        allowed_updates=["message", "chat_member", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
