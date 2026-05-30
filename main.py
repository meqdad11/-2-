import logging
import os
import re
from telegram import Update, Chat as TGChat
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    filters,
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
    cmd_add_word,
    cmd_remove_word,
    cmd_list_words,
    cmd_mute,
    cmd_unmute,
    cmd_lock,
    cmd_unlock,
    cmd_report,
    cmd_shafaq,
    cmd_reminder,
    on_chat_member_updated,
    job_expire_bans,
    job_weekly_report,
    job_daily_report,
    job_daily_quote,
    track_message,
    filter_banned_words,
    auto_reply,
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

_ARABIC_CMDS = {
    "ايدي": cmd_id,
    "حظر": cmd_ban,
    "رفع الحظر": cmd_unban,
    "رفع_الحظر": cmd_unban,
    "تحذير": cmd_warn,
    "قائمة": cmd_banlist,
    "معلومات": cmd_baninfo,
    "تحقق": cmd_checkban,
    "سجل": cmd_eventlog,
    "تحميل": cmd_download,
    "أضف كلمة": cmd_add_word,
    "احذف كلمة": cmd_remove_word,
    "الكلمات المحظورة": cmd_list_words,
    "بحث": cmd_sc_search,
    "يوتيوب": cmd_yt_search,
    "كتم": cmd_mute,
    "رفع الكتم": cmd_unmute,
    "مسح التحذير": cmd_clearwarn,
    "التحذيرات": cmd_warnings,
    "أغلق المجموعة": cmd_lock,
    "افتح المجموعة": cmd_unlock,
    "تقرير": cmd_report,
    "القواعد": cmd_rules,
    "شفق": cmd_shafaq,
    "تذكير": cmd_reminder,
}

async def handle_text(update: Update, context):
    msg = update.message
    if not msg or not msg.text:
        return
    text = msg.text.strip()
    for arabic_cmd, handler in _ARABIC_CMDS.items():
        if text == arabic_cmd or text.startswith(arabic_cmd + " "):
            args = text[len(arabic_cmd):].strip().split() if len(text) > len(arabic_cmd) else []
            context.args = args
            await handler(update, context)
            return
    await handle_media_url(update, context)
    await filter_banned_words(update, context)
    await auto_reply(update, context)
    await track_message(update, context)

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN غير محدد")

    async def post_init(app):
        await db.init_db()

    app = (
        ApplicationBuilder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("warn", cmd_warn))
    app.add_handler(CommandHandler("clearwarn", cmd_clearwarn))
    app.add_handler(CommandHandler("warnings", cmd_warnings))
    app.add_handler(CommandHandler("banlist", cmd_banlist))
    app.add_handler(CommandHandler("baninfo", cmd_baninfo))
    app.add_handler(CommandHandler("checkban", cmd_checkban))
    app.add_handler(CommandHandler("eventlog", cmd_eventlog))
    app.add_handler(CommandHandler("setrules", cmd_setrules))
    app.add_handler(CommandHandler("rules", cmd_rules))
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("unmute", cmd_unmute))
    app.add_handler(CommandHandler("lock", cmd_lock))
    app.add_handler(CommandHandler("unlock", cmd_unlock))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("addword", cmd_add_word))
    app.add_handler(CommandHandler("removeword", cmd_remove_word))
    app.add_handler(CommandHandler("wordlist", cmd_list_words))
    app.add_handler(CommandHandler("scsearch", cmd_sc_search))
    app.add_handler(CommandHandler("ytsearch", cmd_yt_search))
    app.add_handler(CommandHandler("download", cmd_download))
    app.add_handler(CommandHandler("reminder", cmd_reminder))
    app.add_handler(CallbackQueryHandler(callback_download, pattern=r"^dl_(audio|video)\|"))
    app.add_handler(CallbackQueryHandler(callback_sc_download, pattern=r"^sc_dl\|"))
    app.add_handler(CallbackQueryHandler(callback_yt_pick, pattern=r"^yt_pick\|"))
    app.add_handler(ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    from zoneinfo import ZoneInfo
    from datetime import time as dtime
    TIMEZONE = ZoneInfo("Asia/Riyadh")

    job_queue.run_repeating(job_expire_bans, interval=300, first=10)
job_queue.run_daily(job_daily_report, time=dtime(hour=8, minute=0, tzinfo=TIMEZONE))
job_queue.run_daily(job_daily_quote, time=dtime(hour=9, minute=0, tzinfo=TIMEZONE))
job_queue.run_daily(
    job_weekly_report,
    time=dtime(hour=20, minute=0, tzinfo=TIMEZONE),
    days=(4,),
)
    app.run_polling(
        allowed_updates=["message", "chat_member", "callback_query"],
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()