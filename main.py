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
    job_daily_report,
    track_message,
    cmd_add_word,
    cmd_remove_word,
    cmd_list_words,
    filter_banned_words,
    cmd_mute,
    cmd_unmute,
    cmd_lock,
    cmd_unlock,
    cmd_report,
    cmd_weekly_report,
    cmd_daily_report,
    cmd_setadmingroup,
    cmd_focus,
    check_focus_answer,
    cmd_gamescore,
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
# ── Arabic slash-command keyword → handler mapping ──────────────────────────
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
    "أغلق المجموعة": cmd_lock,
    "افتح المجموعة": cmd_unlock,
    "قواعد": cmd_rules,
    "تقرير": cmd_report,
    "تقرير اسبوعي": cmd_weekly_report,
    "تقرير_اسبوعي": cmd_weekly_report,
    "تقرير يومي": cmd_daily_report,
    "تقرير_يومي": cmd_daily_report,
    "قروب المشرفين": cmd_setadmingroup,
    "قروب_المشرفين": cmd_setadmingroup,
    "تركيز": cmd_focus,
    "نقاطي": cmd_gamescore,
}

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("استثناء غير معالج:\n%s", traceback.format_exc())
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ حدث خطأ غير متوقع. تم تسجيل الخطأ للمراجعة."
            )
        except Exception:
            pass
async def all_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        return

    # ── Detect Arabic keywords without slash (e.g. ايدي, حظر 123) ─────────────
    for keyword, func in _ARABIC_CMDS.items():
        if text == keyword or text.startswith(keyword + " "):
            parts = text.split()
            context.args = parts[1:] if len(parts) > 1 else []
            logger.info("أمر عربي بدون سلاش: %s", keyword)
            await func(update, context)
            return

    # ── Check for focus game answers ──────────────────────────────────────────
    await check_focus_answer(update, context)
async def post_init(application: Application) -> None:
    await db.init_db()
    logger.info("تم تهيئة قاعدة البيانات")
    
    # مهمة انتهاء الحظر كل دقيقة
    application.job_queue.run_repeating(job_expire_bans, interval=60, first=10)
    logger.info("تم جدولة مهمة انتهاء مدد الحظر")
    
    # التقرير الأسبوعي (كل يوم أحد الساعة 9 صباحاً)
    application.job_queue.run_daily(
        send_weekly_reports,
        time=__import__('datetime').time(hour=9, minute=0),
        days=(6,)  # الأحد
    )
    logger.info("تم جدولة التقرير الأسبوعي")
    
    # التقرير اليومي (كل يوم الساعة 12 منتصف الليل)
    application.job_queue.run_daily(
        send_daily_reports,
        time=__import__('datetime').time(hour=0, minute=0),
    )
    logger.info("تم جدولة التقرير اليومي")

async def send_weekly_reports(context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers import generate_full_report
        chats = await db.get_all_chats()
        for chat_id in chats:
            admin_group_id = await db.get_setting(chat_id, "admin_group_id")
            if not admin_group_id:
                continue
            try:
                admin_group_id = int(admin_group_id)
            except ValueError:
                continue
            
            report = await generate_full_report(chat_id, days=7)
            try:
                await context.bot.send_message(admin_group_id, report)
            except Exception as e:
                logger.warning("فشل إرسال التقرير الأسبوعي للمجموعة %s: %s", chat_id, e)
    except Exception as e:
        logger.error("خطأ في إرسال التقارير الأسبوعية: %s", e)

async def send_daily_reports(context: ContextTypes.DEFAULT_TYPE):
    try:
        await job_daily_report(context)
    except Exception as e:
        logger.error("خطأ في إرسال التقارير اليومية: %s", e)

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
    app.add_handler(CommandHandler("download", cmd_download))
    app.add_handler(CommandHandler("addword", cmd_add_word))
    app.add_handler(CommandHandler("removeword", cmd_remove_word))
    app.add_handler(CommandHandler("wordlist", cmd_list_words))
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("unmute", cmd_unmute))
    app.add_handler(CommandHandler("lock", cmd_lock))
    app.add_handler(CommandHandler("unlock", cmd_unlock))
    app.add_handler(CommandHandler("scsearch", cmd_sc_search))
    app.add_handler(CommandHandler("ytsearch", cmd_yt_search))
    
    # أوامر جديدة
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("weeklyreport", cmd_weekly_report))
    app.add_handler(CommandHandler("dailyreport", cmd_daily_report))
    app.add_handler(CommandHandler("setadmingroup", cmd_setadmingroup))
    app.add_handler(CommandHandler("focus", cmd_focus))
    app.add_handler(CommandHandler("gamescore", cmd_gamescore))

    # ── Callback queries ──────────────────────────────────────────────────────
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(callback_download, pattern=r"^dl_(audio|video)\|"))
    app.add_handler(CallbackQueryHandler(callback_sc_download, pattern=r"^sc_dl\|"))
    app.add_handler(CallbackQueryHandler(callback_yt_pick, pattern=r"^yt_pick\|"))

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
