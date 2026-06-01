import logging
import datetime

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    filters,
)
from telegram import Update

import database as db
from config import TELEGRAM_BOT_TOKEN
from commands import ARABIC_COMMANDS

from handlers_admin import (
    cmd_ban, cmd_unban, cmd_warn, cmd_clearwarn, cmd_warnings,
    cmd_banlist, cmd_baninfo, cmd_checkban, cmd_eventlog,
    cmd_setrules, cmd_mute, cmd_unmute, cmd_lock, cmd_unlock,
)
from handlers_user import (
    cmd_start, cmd_id, cmd_rules,
    auto_reply, track_message,
)
from handlers_moderation import (
    cmd_add_word, cmd_remove_word, cmd_list_words,
    filter_banned_words,
)
from handlers_jobs import (
    cmd_report, job_expire_bans, 
    job_daily_quote,
)
from handlers_ai import (
    cmd_shafaq, cmd_choose_model, callback_choose_model,
)
from handlers_events import on_chat_member_updated
from handlers_resources import (
    cmd_add_resource, cmd_list_resources, cmd_delete_resource,
)
from music import (
    cmd_download, cmd_sc_search, cmd_yt_search,
    handle_media_url, callback_download,
    callback_sc_download, callback_yt_pick,
)
from handlers_menu import callback_menu, handle_interactive_messages  # <--- أضفنا handle_interactive_messages

# ========== إعداد التسجيل ==========
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ========== معالج الرسائل النصية ==========
async def handle_text(update: Update, context):
    msg = update.message
    if not msg or not msg.text:
        return
    text = msg.text.strip()
    chat_id = msg.chat.id

    # التحقق من وجود طلب معلق (بحث، مسح، تذكير...)
    if (context.user_data.get('waiting_google') == chat_id or
        context.user_data.get('purge_mode') == chat_id or
        context.user_data.get('waiting_remind') == chat_id or
        context.user_data.get('waiting_translate') == chat_id or
        context.user_data.get('waiting_broadcast') == chat_id):
        from handlers_menu import handle_interactive_messages
        await handle_interactive_messages(update, context)
        return

    # الأوامر العربية
    for arabic_cmd, handler in ARABIC_COMMANDS.items():
        if text == arabic_cmd or text.startswith(arabic_cmd + " "):
            args = text[len(arabic_cmd):].strip().split() if len(text) > len(arabic_cmd) else []
            context.args = args
            await handler(update, context)
            return

    await handle_media_url(update, context)
    await filter_banned_words(update, context)
    await auto_reply(update, context)
    await track_message(update, context)
# ========== تهيئة التطبيق ==========
async def post_init(app):
    await db.init_db()

# ========== تسجيل الهاندلرز ==========
def register_handlers(app):

    # أوامر سلاش
    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("id",         cmd_id))
    app.add_handler(CommandHandler("ban",        cmd_ban))
    app.add_handler(CommandHandler("unban",      cmd_unban))
    app.add_handler(CommandHandler("warn",       cmd_warn))
    app.add_handler(CommandHandler("clearwarn",  cmd_clearwarn))
    app.add_handler(CommandHandler("warnings",   cmd_warnings))
    app.add_handler(CommandHandler("banlist",    cmd_banlist))
    app.add_handler(CommandHandler("baninfo",    cmd_baninfo))
    app.add_handler(CommandHandler("checkban",   cmd_checkban))
    app.add_handler(CommandHandler("eventlog",   cmd_eventlog))
    app.add_handler(CommandHandler("setrules",   cmd_setrules))
    app.add_handler(CommandHandler("rules",      cmd_rules))
    app.add_handler(CommandHandler("mute",       cmd_mute))
    app.add_handler(CommandHandler("unmute",     cmd_unmute))
    app.add_handler(CommandHandler("lock",       cmd_lock))
    app.add_handler(CommandHandler("unlock",     cmd_unlock))
    app.add_handler(CommandHandler("report",     cmd_report))
    app.add_handler(CommandHandler("addword",    cmd_add_word))
    app.add_handler(CommandHandler("removeword", cmd_remove_word))
    app.add_handler(CommandHandler("wordlist",   cmd_list_words))
    app.add_handler(CommandHandler("scsearch",   cmd_sc_search))
    app.add_handler(CommandHandler("ytsearch",   cmd_yt_search))
    app.add_handler(CommandHandler("download",   cmd_download))
    app.add_handler(CommandHandler("model",      cmd_choose_model))

    # أزرار inline
    app.add_handler(CallbackQueryHandler(callback_download,     pattern=r"^dl_(audio|video)\|"))
    app.add_handler(CallbackQueryHandler(callback_sc_download,  pattern=r"^sc_dl\|"))
    app.add_handler(CallbackQueryHandler(callback_yt_pick,      pattern=r"^yt_pick\|"))
    app.add_handler(CallbackQueryHandler(callback_choose_model, pattern=r"^model_"))
    app.add_handler(CallbackQueryHandler(callback_menu))

    # أحداث الأعضاء
    app.add_handler(ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER))

    # الرسائل النصية
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    # معالج الرسائل التفاعلية (لأوامر مثل مسح، تذكير، ترجمة، بحث جوجل، بث)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_interactive_messages))

# ========== تسجيل الجوبز الدورية ==========
def register_jobs(app):
    jq = app.job_queue
    jq.run_repeating(job_expire_bans, interval=300, first=10)
    jq.run_daily(
        job_daily_quote,
        time=datetime.time(hour=9, minute=0, tzinfo=datetime.timezone.utc)
    )

# ========== نقطة الدخول الرئيسية ==========
def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN غير محدد")

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    register_handlers(app)
    register_jobs(app)

    app.run_polling(
        allowed_updates=["message", "chat_member", "callback_query"],
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()