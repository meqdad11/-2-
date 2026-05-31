import logging
import random
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from helpers import is_admin, get_reply_user

# ================================================

logger = logging.getLogger(__name__)
TIMEZONE = ZoneInfo("Asia/Riyadh")

AUTO_REPLIES = {
    "صباح الخير": ["صباح النور ☀️"],
    "صباح النور": ["صباح الورد 🌹"],
    "صباح الورد": ["صباح السعادة ☀️"],
    "مساء الخير": ["مساء النور 🌙"],
    "مساء النور": ["مساء الورد 🌹"],
    "مساء الورد": ["مساء السعادة 🌙"],
}

# ================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "بوت شفق نشط ✅\n\n"
        "👮 أوامر المشرفين:\n"
        "حظر — حظر عضو (رد أو معرف)\n"
        "حظر 123 7d سبب — حظر مؤقت\n"
        "رفع الحظر — رفع الحظر\n"
        "تحذير — تحذير (3 = حظر تلقائي)\n"
        "مسح التحذير — مسح تحذيرات عضو\n"
        "التحذيرات — عدد تحذيرات عضو\n"
        "كتم — كتم عضو\n"
        "كتم 123 1h — كتم مؤقت\n"
        "رفع الكتم — رفع الكتم\n"
        "قائمة — المحظورون\n"
        "معلومات — تفاصيل الحظر\n"
        "تحقق — هل هو محظور؟\n"
        "سجل — آخر الأحداث\n"
        "تقرير — تقرير فوري\n"
        "أضف كلمة — إضافة كلمة محظورة\n"
        "احذف كلمة — حذف كلمة\n"
        "الكلمات المحظورة — القائمة\n"
        "أغلق المجموعة — إغلاق\n"
        "افتح المجموعة — فتح\n"
        "/setrules — تعيين القواعد\n\n"
        "👥 للجميع:\n"
        "ايدي — معلوماتك + صورتك\n"
        "القواعد — قواعد المجموعة\n"
        "شفق <سؤال> — اسأل الذكاء الاصطناعي\n"
        "تذكير 20:00 نص — تذكير لمرة واحدة\n"
        "تذكير يومي 20:00 نص — تذكير يومي\n\n"
        "🎵 الميديا:\n"
        "أرسل رابط مباشرة — تحميل\n\n"
        "🤖 تلقائي:\n"
        "طرد المحظورين تلقائياً\n"
        "حذف الكلمات المحظورة\n"
        "ترحيب بالأعضاء الجدد\n"
        "اقتباس يومي الساعة 9 صباحاً\n"
        "تقرير يومي وأسبوعي"
    )

# ================================================

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    reply_user = get_reply_user(update)
    from telegram import Chat as TGChat
    in_group = chat.type in (TGChat.GROUP, TGChat.SUPERGROUP)
    if reply_user and reply_user.id != user.id:
        if not in_group or not await is_admin(update, context):
            await update.message.reply_text("لا يمكنك عرض بيانات عضو آخر.")
            return
        username = f"@{reply_user.username}" if reply_user.username else "غير محدد"
        try:
            photos = await context.bot.get_user_profile_photos(reply_user.id, limit=1)
            if photos.total_count > 0:
                await update.message.reply_photo(
                    photo=photos.photos[0][-1].file_id,
                    caption=(
                        f"معلومات العضو:\n"
                        f"الاسم: {reply_user.first_name}\n"
                        f"اليوزر: {username}\n"
                        f"المعرف: {reply_user.id}"
                    )
                )
                return
        except Exception:
            pass
        await update.message.reply_text(
            f"معلومات العضو:\n"
            f"الاسم: {reply_user.first_name}\n"
            f"اليوزر: {username}\n"
            f"المعرف: {reply_user.id}"
        )
    else:
        username = f"@{user.username}" if user.username else "غير محدد"
        try:
            photos = await context.bot.get_user_profile_photos(user.id, limit=1)
            if photos.total_count > 0:
                await update.message.reply_photo(
                    photo=photos.photos[0][-1].file_id,
                    caption=(
                        f"معلوماتك:\n"
                        f"الاسم: {user.first_name}\n"
                        f"اليوزر: {username}\n"
                        f"المعرف: {user.id}"
                    )
                )
                return
        except Exception:
            pass
        await update.message.reply_text(
            f"معلوماتك:\n"
            f"الاسم: {user.first_name}\n"
            f"اليوزر: {username}\n"
            f"المعرف: {user.id}"
        )

# ================================================

async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    rules = await db.get_setting(chat_id, "rules")
    if rules:
        await update.message.reply_text(f"📋 قواعد المجموعة:\n{rules}")
    else:
        await update.message.reply_text("لم يتم تعيين قواعد بعد.")

# ================================================

async def cmd_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import Chat as TGChat
    from datetime import timedelta, time as dtime
    if update.effective_chat.type != TGChat.PRIVATE:
        await update.message.reply_text("أمر التذكير يعمل في الخاص فقط.")
        return
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "الاستخدام:\n"
            "تذكير 20:00 نص الرسالة\n"
            "تذكير يومي 20:00 نص الرسالة"
        )
        return
    daily = False
    if args[0] == "يومي":
        daily = True
        args = args[1:]
    time_str = args[0]
    text = " ".join(args[1:])
    if not text:
        await update.message.reply_text("اكتب نص التذكير بعد الوقت.")
        return
    try:
        hour, minute = map(int, time_str.split(":"))
        assert 0 <= hour <= 23 and 0 <= minute <= 59
    except Exception:
        await update.message.reply_text("صيغة الوقت خاطئة. استخدم مثلاً: 20:00")
        return
    user_id = update.effective_user.id
    now_local = datetime.now(TIMEZONE)
    if daily:
        target_time = dtime(hour=hour, minute=minute, second=0, tzinfo=TIMEZONE)
        context.job_queue.run_daily(
            _send_reminder,
            time=target_time,
            chat_id=user_id,
            name=f"reminder_{user_id}_{hour}_{minute}",
            data=text,
        )
        await update.message.reply_text(f"✅ تم ضبط تذكير يومي الساعة {time_str}:\n{text}")
    else:
        from datetime import timedelta
        target = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now_local:
            target += timedelta(days=1)
        delay = (target - now_local).total_seconds()
        context.job_queue.run_once(
            _send_reminder,
            when=delay,
            chat_id=user_id,
            name=f"reminder_{user_id}_{hour}_{minute}",
            data=text,
        )
        await update.message.reply_text(f"✅ تم ضبط تذكير الساعة {time_str}:\n{text}")

# ================================================

async def _send_reminder(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=f"🔔 تذكير:\n{context.job.data}"
    )

# ================================================

async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    from telegram import Chat as TGChat
    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return
    text = msg.text.strip()
    for keyword, replies in AUTO_REPLIES.items():
        if keyword in text:
            await msg.reply_text(random.choice(replies))
            return
    if context.bot.username and f"@{context.bot.username.lower()}" in text.lower():
        await msg.reply_text("هلا! كيف أقدر أساعدك؟ 😊")

# ================================================

async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    from telegram import Chat as TGChat
    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return
    user = update.effective_user
    chat = update.effective_chat
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    await db.increment_message_count(user.id, chat.id, full_name)
    await db.save_chat_name(chat.id, chat.title or str(chat.id))