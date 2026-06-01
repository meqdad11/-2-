import logging
import random
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from config import TIMEZONE
from helpers import is_admin, get_reply_user

# ================================================

logger = logging.getLogger(__name__)

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
        "بوت شفق 🌅\n\n"
        "━━━━━━━━━━━━━━━\n"
        "👮 أوامر المشرفين\n"
        "━━━━━━━━━━━━━━━\n"
        "🚫 الحظر:\n"
        "• حظر — حظر عضو\n"
        "• حظر 123 7d سبب — حظر مؤقت\n"
        "• رفع الحظر — رفع الحظر\n"
        "• قائمة — المحظورون\n"
        "• معلومات — تفاصيل الحظر\n"
        "• تحقق — هل هو محظور؟\n\n"
        "⚠️ التحذيرات:\n"
        "• تحذير — تحذير (3 = حظر تلقائي)\n"
        "• مسح التحذير — مسح التحذيرات\n"
        "• التحذيرات — عدد التحذيرات\n\n"
        "🔇 الكتم:\n"
        "• كتم — كتم عضو\n"
        "• كتم 123 1h — كتم مؤقت\n"
        "• رفع الكتم — رفع الكتم\n\n"
        "⚙️ الإدارة:\n"
        "• أغلق المجموعة / افتح المجموعة\n"
        "• أضف كلمة / احذف كلمة\n"
        "• الكلمات المحظورة\n"
        "• سجل — آخر الأحداث\n"
        "• تقرير — تقرير فوري\n"
        "• /setrules — تعيين القواعد\n"
        "• أضف مورد العنوان | المحتوى\n"
        "• احذف مورد <رقم>\n\n"
        "━━━━━━━━━━━━━━━\n"
        "👥 للجميع\n"
        "━━━━━━━━━━━━━━━\n"
        "• ايدي — معلوماتك\n"
        "• القواعد — قواعد المجموعة\n"
        "• الموارد — قائمة الموارد\n"
        "• الموارد <كلمة> — بحث في الموارد\n"
        "• شفق <سؤال> — اسأل الذكاء الاصطناعي\n"
        "• تذكير 20:00 نص — تذكير\n"
        "• تذكير يومي 20:00 نص — تذكير يومي\n\n"
        "━━━━━━━━━━━━━━━\n"
        "🎵 الميديا\n"
        "━━━━━━━━━━━━━━━\n"
        "• أرسل رابط مباشرة — تحميل\n"
        "• يوتيوب <اسم> — بحث\n"
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
        target = reply_user
        label = "معلومات العضو"
    else:
        target = user
        label = "معلوماتك"

    username = f"@{target.username}" if target.username else "غير محدد"
    bio = "غير محدد"
    msg_count = 0

    try:
        full_chat = await context.bot.get_chat(target.id)
        if full_chat.bio:
            bio = full_chat.bio
    except Exception:
        pass

    if in_group:
        msg_count = await db.get_message_count(target.id, chat.id)

    caption = (
        f"{label}:\n"
        f"الاسم: {target.first_name}\n"
        f"اليوزر: {username}\n"
        f"المعرف: {target.id}\n"
        f"البايو: {bio}\n"
        f"💬 الرسائل: {msg_count}"
    )

    try:
        photos = await context.bot.get_user_profile_photos(target.id, limit=1)
        if photos.total_count > 0:
            await update.message.reply_photo(
                photo=photos.photos[0][-1].file_id,
                caption=caption
            )
            return
    except Exception:
        pass

    await update.message.reply_text(caption)

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

# ================================================
# ========== الأوامر الجديدة المضافة ==========
# ================================================

# 1. أمر "اهمس"
async def cmd_whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ هذا الأمر مخصص للمجموعات فقط.")
        return
    if not context.args:
        await update.message.reply_text("❗️ الاستخدام: اهمس @username الرسالة")
        return
    target_username = context.args[0]
    if target_username.startswith('@'):
        target_username = target_username[1:]
    whisper_text = " ".join(context.args[1:])
    if not whisper_text:
        await update.message.reply_text("❌ لا يمكن إرسال همسة فارغة.")
        return
    try:
        target_user = await context.bot.get_chat(target_username)
    except:
        await update.message.reply_text(f"❌ لم أجد المستخدم {target_username}.")
        return
    try:
        await context.bot.send_message(
            chat_id=target_user.id,
            text=f"🔊 لديك همسة من {update.effective_user.mention_html()}:\n\n{whisper_text}",
            parse_mode="HTML"
        )
        await update.message.reply_text(f"✅ تم الإرسال إلى {target_user.mention_html()}!", parse_mode="HTML")
    except:
        await update.message.reply_text("❌ لم أستطع الإرسال. قد يكون المستخدم حظر البوت أو لم يبدأ محادثة معه.")

# 2. أمر "افتاري" (رابط المجموعة)
async def cmd_get_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    try:
        link = await context.bot.create_chat_invite_link(update.effective_chat.id, member_limit=1)
        await update.message.reply_text(f"🔗 رابط المجموعة:\n{link.invite_link}")
    except:
        await update.message.reply_text("❌ لا يمكن إنشاء رابط، تأكد من صلاحيات البوت.")

# 3. أمر "سورة" (آية عشوائية من سورة)
async def cmd_surah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: سورة [اسم السورة]")
        return
    surah_name = " ".join(context.args).strip()
    # محاكاة بسيطة (يمكن ربطها بـ API حقيقي)
    await update.message.reply_text(f"📖 سورة {surah_name}:\n(هذه خدمة تجريبية، سيتم ربطها بـ API لاحقاً)")

# 4. أمر "قران" (صفحة من القرآن)
async def cmd_quran_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: قران [رقم الصفحة]")
        return
    try:
        page = int(context.args[0])
        await update.message.reply_text(f"📖 صفحة {page} من القرآن الكريم:\n(خدمة تجريبية، سيتم ربطها بـ API لاحقاً)")
    except:
        await update.message.reply_text("الرقم غير صالح.")

# 5. أمر "انطقي" (نطق النص)
async def cmd_speak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: انطقي [النص]")
        return
    text = " ".join(context.args)
    await update.message.reply_text(f"🔊 (محاكاة نطق): {text}")

# 6. أمر "وش يقول" (تحويل الصوت لنص)
async def cmd_voice_to_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not update.message.reply_to_message.voice:
        await update.message.reply_text("الرجاء الرد على رسالة صوتية (فويس).")
        return
    await update.message.reply_text("🎙️ (خدمة تحويل الصوت لنص غير متاحة حالياً، سيتم تفعيلها لاحقاً)")

# 7. أمر "جيمناي" (ذكاء اصطناعي)
async def cmd_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: جيمناي [سؤالك]")
        return
    query = " ".join(context.args)
    await update.message.reply_text(f"🧠 رد تجريبي على '{query}' (يُربط لاحقاً بـ Gemini API)")

# 8. أمر "الحد" (تغيير نموذج الذكاء الاصطناعي)
async def cmd_model_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚙️ إعدادات النماذج غير مفعلة حالياً.")

# 9. أمر "اطردني" (للمستخدم أن يطرد نفسه)
async def cmd_kickme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.unban_chat_member(chat_id, user_id)
        await update.message.reply_text("✅ تم طردك بناءً على طلبك.")
    except:
        await update.message.reply_text("❌ لا أستطيع طردك، تأكد من صلاحياتي.")

# 10. أمر "تفعيل الترحيب"
async def cmd_enable_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await db.set_setting(update.effective_chat.id, "welcome_enabled", "yes")
    await update.message.reply_text("✅ تم تفعيل الترحيب.")

# 11. أمر "تعطيل الترحيب"
async def cmd_disable_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await db.set_setting(update.effective_chat.id, "welcome_enabled", "no")
    await update.message.reply_text("✅ تم تعطيل الترحيب.")

# 12. أمر "بايـو" (عرض بايو العضو)
async def cmd_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        full = await context.bot.get_chat(user.id)
        bio = full.bio if full.bio else "لا يوجد بايو."
        await update.message.reply_text(f"📝 بايو العضو {user.first_name}:\n{bio}")
    except:
        await update.message.reply_text("لا يمكن جلب البايو حالياً.")

# 13. أمر "المالك" (عرض معلومات المطور)
async def cmd_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👨‍💻 **المطور:** [Me8dad](https://t.me/Me8dad)\nللمساعدة والدعم.", parse_mode="Markdown")