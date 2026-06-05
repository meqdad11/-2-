import asyncio
import logging
import datetime
import pytz

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    ChosenInlineResultHandler,
    filters,
)
from telegram import Update

from utils import database as db
from config import TELEGRAM_BOT_TOKEN
from commands import ARABIC_COMMANDS
from utils.helpers import is_admin

from handlers.admin import (
    cmd_ban, cmd_unban, cmd_warn, cmd_clearwarn, cmd_warnings,
    cmd_banlist, cmd_baninfo, cmd_checkban, cmd_eventlog,
    cmd_setrules, cmd_mute, cmd_unmute, cmd_lock, cmd_unlock,
)
from handlers.user import (
    cmd_start, cmd_id, cmd_rules,
    auto_reply, track_message, cmd_my_reminders,
    handle_whisper_message,
)
from handlers.moderation import (
    cmd_add_word, cmd_remove_word, cmd_list_words,
    filter_banned_words, process_custom_replies_and_commands,
)
from handlers.jobs import (
    cmd_report, job_expire_bans, 
    job_daily_quote, job_reschedule_reminders,
    _send_daily_reminder,
)
from handlers.ai import (
    cmd_shafaq, cmd_choose_model, callback_choose_model,
)
from handlers.events import on_chat_member_updated
from handlers.resources import (
    cmd_add_resource, cmd_list_resources, cmd_delete_resource,
)
from music import (
    cmd_download, cmd_sc_search, cmd_yt_search,
    handle_media_url, callback_download,
    callback_sc_download, callback_yt_pick,
    handle_userbot_response,
)
from handlers.locks import filter_locked_content

from handlers.menu import cmd_menu
from handlers.buttons import callback_menu
from handlers.interactive import handle_interactive_messages

from handlers.admin import (
    cmd_promote_admin, cmd_demote_admin, cmd_list_admins,
    cmd_demote_all, cmd_purge_bans, cmd_purge_muted,
    cmd_tag_all, cmd_my_rank, cmd_his_rank, confirm_demote_all,
)
from handlers.user import (
    cmd_whisper, cmd_get_invite, cmd_surah, cmd_quran_page,
    cmd_speak, cmd_voice_to_text, cmd_kickme,
    cmd_enable_welcome, cmd_disable_welcome, cmd_bio, cmd_owner,
    cmd_create_anon_link, cmd_my_messages,
)
from handlers.moderation import (
    cmd_add_reply, cmd_remove_reply, cmd_list_replies,
    cmd_add_command, cmd_remove_command, cmd_list_commands,
)
from handlers.ai import cmd_gemini, cmd_limit
from handlers.dev import cmd_add_dev, cmd_remove_dev, cmd_broadcast, cmd_bot_stats

from handlers.crisis import (
    check_crisis_words,
)

from handlers.inline import handle_inline_query, handle_chosen_inline_result

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SAUDI_TZ = pytz.timezone('Asia/Riyadh')

async def handle_text(update: Update, context):
    msg = update.message
    if not msg or not msg.text:
        return
    text = msg.text.strip()
    chat_id = msg.chat.id
    user = update.effective_user

    if context.user_data.get("anon_target"):
        target_id = context.user_data.pop("anon_target")
        await db.save_anonymous_message("", text, update.effective_user.id)
        try:
            await context.bot.send_message(
                target_id,
                f"📨 **رسالة جديدة (صارحني):**\n\n{text}\n\n"
                f"لعرض جميع رسائلك: استخدم أمر `رسائلي`.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"فشل إرسال إشعار الرسالة المجهولة: {e}")
        await update.message.reply_text("✅ تم إرسال رسالتك المجهولة.")
        return

    if msg.reply_to_message and text == "حذف":
        if not await is_admin(update, context):
            try:
                await context.bot.send_message(user.id, "⛔ هذا الأمر للمشرفين فقط.")
            except:
                pass
            try:
                await msg.delete()
            except:
                pass
            return
        try:
            await context.bot.delete_message(chat_id, msg.reply_to_message.message_id)
            await msg.delete()
        except Exception as e:
            try:
                await context.bot.send_message(
                    user.id,
                    "❌ لا يمكن حذف هذه الرسالة (قد تكون قديمة أو ليس لدي صلاحية)."
                )
            except:
                pass
            try:
                await msg.delete()
            except:
                pass
        return

    if (context.user_data.get('waiting_google') == chat_id or
        context.user_data.get('purge_mode') == chat_id or
        context.user_data.get('waiting_remind') == chat_id or
        context.user_data.get('waiting_translate') == chat_id or
        context.user_data.get('waiting_broadcast') == chat_id):
        await handle_interactive_messages(update, context)
        return

    if text == "تأكيد" and context.user_data.get('awaiting_demote_all') == chat_id:
        await confirm_demote_all(update, context)
        return

    for arabic_cmd, handler in ARABIC_COMMANDS.items():
        if text == arabic_cmd or text.startswith(arabic_cmd + " "):
            args = text[len(arabic_cmd):].strip().split() if len(text) > len(arabic_cmd) else []
            context.args = args
            await handler(update, context)
            return

    await process_custom_replies_and_commands(update, context)
    await handle_media_url(update, context)
    await filter_banned_words(update, context)
    await auto_reply(update, context)
    await track_message(update, context)
    await check_crisis_words(update, context)

async def handle_channel_post(update: Update, context):
    msg = update.channel_post
    if not msg or not msg.text:
        logger.info("📭 استلام رسالة قناة بدون نص")
        return
    logger.info(f"📢 رسالة جديدة في القناة: {msg.text[:100]}")
    await handle_media_url(update, context)

async def post_init(app):
    await db.init_db()
    reminders = await db.load_all_reminders()
    if reminders:
        count = 0
        for r in reminders:
            try:
                h, m = map(int, r["reminder_time"].split(":"))
                app.job_queue.run_daily(
                    _send_daily_reminder,
                    time=datetime.time(hour=h, minute=m, tzinfo=SAUDI_TZ),
                    chat_id=r["chat_id"],
                    data={"user_id": r["user_id"], "text": r["reminder_text"]},
                    name=f"daily_reminder_{r['id']}"
                )
                count += 1
            except Exception as e:
                logger.error(f"فشل إعادة جدولة تذكير: {e}")
        if count:
            logger.info(f"✅ تم إعادة جدولة {count} تذكير يومي")

def register_handlers(app):
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
    app.add_handler(CommandHandler("model", cmd_choose_model))
    app.add_handler(CommandHandler("myreminders", cmd_my_reminders))

    app.add_handler(CallbackQueryHandler(callback_download, pattern=r"^dl_(audio|video)\|"))
    app.add_handler(CallbackQueryHandler(callback_sc_download, pattern=r"^sc_dl\|"))
    app.add_handler(CallbackQueryHandler(callback_yt_pick, pattern=r"^yt_pick\|"))
    app.add_handler(CallbackQueryHandler(callback_choose_model, pattern=r"^model_"))
    app.add_handler(CallbackQueryHandler(callback_menu))

    app.add_handler(ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER))

    # معالج استقبال الملفات من اليوزربوت (حسابك الشخصي)
    app.add_handler(MessageHandler(
        (filters.VIDEO | filters.AUDIO | filters.Document.ALL) & filters.ChatType.PRIVATE,
        handle_userbot_response
    ))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, handle_text))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_text))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.CHANNEL, handle_channel_post))
    app.add_handler(MessageHandler(filters.ALL & filters.ChatType.GROUPS, filter_locked_content))

    app.add_handler(InlineQueryHandler(handle_inline_query))
    app.add_handler(ChosenInlineResultHandler(handle_chosen_inline_result))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_whisper_message))

def register_jobs(app):
    jq = app.job_queue
    jq.run_repeating(job_expire_bans, interval=300, first=10)
    jq.run_daily(
        job_daily_quote,
        time=datetime.time(hour=9, minute=0, second=0, tzinfo=SAUDI_TZ)
    )

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
        allowed_updates=["message", "channel_post", "edited_channel_post", "chat_member", "callback_query", "inline_query", "chosen_inline_result"],
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()