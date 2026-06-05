"""
ملف المستخدم - مع تعدد التذكيرات اليومية ونظام الهمسات الجديد
"""

import logging
import random
import uuid
import aiohttp
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes
from telegram import Chat as TGChat

from utils import database as db
from config import TIMEZONE
from utils.helpers import is_admin, get_reply_user
from handlers.jobs import _send_daily_reminder

logger = logging.getLogger(__name__)

AUTO_REPLIES = {
    "صباح الخير": ["صباح النور ☀️"],
    "صباح النور": ["صباح الورد 🌹"],
    "صباح الورد": ["صباح السعادة ☀️"],
    "مساء الخير": ["مساء النور 🌙"],
    "مساء النور": ["مساء الورد 🌹"],
    "مساء الورد": ["مساء السعادة 🌙"],
}

# ==================== START ====================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0].startswith("whisper_"):
        await handle_whisper_start(update, context)
        return

    if context.args and context.args[0].startswith("anon_"):
        link_id = context.args[0].replace("anon_", "")
        target_user_id = await db.get_user_by_link(link_id)
        if not target_user_id:
            await update.message.reply_text("❌ هذا الرابط غير صالح.")
            return
        context.user_data["anon_target"] = target_user_id
        await update.message.reply_text("📝 أرسل رسالتك المجهولة الآن.")
        return

    await update.message.reply_text(
        "بوت شفق 🌅\n\n"
        "👮 أوامر المشرفين + أوامر المستخدمين مفعلة"
    )

# ==================== ID ====================
async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    reply_user = get_reply_user(update)

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
    except:
        pass

    if in_group:
        msg_count = await db.get_message_count(target.id, chat.id)

    caption = f"{label}:\nالاسم: {target.first_name}\nاليوزر: {username}\nالمعرف: {target.id}\nالبايو: {bio}\n💬 الرسائل: {msg_count}"

    try:
        photos = await context.bot.get_user_profile_photos(target.id, limit=1)
        if photos.total_count > 0:
            await update.message.reply_photo(photo=photos.photos[0][-1].file_id, caption=caption)
            return
    except:
        pass

    await update.message.reply_text(caption)

# ==================== RULES ====================
async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    rules = await db.get_setting(chat_id, "rules")
    if rules:
        await update.message.reply_text(f"📋 قواعد المجموعة:\n{rules}")
    else:
        await update.message.reply_text("لم يتم تعيين قواعد بعد.")

# ==================== REMINDERS ====================
async def _send_reminder(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=f"🔔 تذكير:\n{context.job.data}",
        parse_mode="Markdown"
    )

async def cmd_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    if not context.args or len(context.args) < 2:
        await msg.reply_text(
            "📌 تذكير لمرة واحدة:\n"
            "تذكر 5 نص التذكير\n\n"
            "• الرقم = عدد الدقائق (1-1440)\n"
            "• مثال: تذكر 10 شرب الماء",
            parse_mode="Markdown"
        )
        return
    try:
        minutes = int(context.args[0])
        if minutes <= 0 or minutes > 1440:
            await msg.reply_text("❌ عدد الدقائق بين 1 و 1440.")
            return
    except ValueError:
        await msg.reply_text("❌ الرقم الأول غير صالح.")
        return
    reminder_text = " ".join(context.args[1:])
    if not reminder_text:
        await msg.reply_text("❌ اكتب نص التذكير.")
        return
    delay = minutes * 60
    try:
        context.job_queue.run_once(
            _send_reminder,
            when=delay,
            chat_id=msg.chat.id,
            name=f"reminder_{msg.chat.id}_{msg.message_id}",
            data=reminder_text
        )
        await msg.reply_text(f"✅ تم ضبط التذكير:\n⏰ بعد {minutes} دقيقة\n📝 {reminder_text}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"خطأ في التذكير: {e}")
        await msg.reply_text("❌ حدث خطأ.")

async def cmd_daily_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not context.args or len(context.args) < 2:
        await msg.reply_text(
            "📌 تذكير يومي:\n"
            "تذكير يومي 14:30 نص التذكير\n\n"
            "• الوقت بصيغة HH:MM (24 ساعة)\n"
            "• مثال: تذكير يومي 09:00 اجتماع العمل\n\n"
            "✏️ لإلغاء جميع التذكيرات: إلغاء تذكير يومي\n"
            "📋 لعرض التذكيرات: تذكيراتي",
            parse_mode="Markdown"
        )
        return

    time_str = context.args[0]
    reminder_text = " ".join(context.args[1:])

    if not reminder_text:
        await msg.reply_text("❌ اكتب نص التذكير.")
        return

    try:
        hour, minute = map(int, time_str.split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except:
        await msg.reply_text("❌ صيغة الوقت خاطئة. استخدم HH:MM (مثال: 14:30).")
        return

    try:
        saved = await db.save_reminder(user_id, chat_id, time_str, reminder_text)
        if not saved:
            await msg.reply_text("❌ فشل حفظ التذكير في قاعدة البيانات.")
            return

        target_time = dtime(hour=hour, minute=minute, second=0, tzinfo=TIMEZONE)
        context.job_queue.run_daily(
            _send_daily_reminder,
            time=target_time,
            chat_id=chat_id,
            data={"user_id": user_id, "text": reminder_text},
            name=f"daily_reminder_{saved['id']}"
        )

        await msg.reply_text(
            f"✅ تم ضبط التذكير اليومي:\n"
            f"⏰ الساعة {time_str}\n"
            f"📝 {reminder_text}\n\n"
            f"💾 التذكير محفوظ ولن يضيع بعد إعادة التشغيل.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"خطأ في التذكير اليومي: {e}")
        await msg.reply_text("❌ حدث خطأ.")

async def cmd_cancel_daily_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء جميع التذكيرات اليومية للمستخدم في هذه المحادثة"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    await db.delete_reminder(user_id, chat_id)

    jobs_removed = 0
    for job in context.job_queue.jobs():
        if job.name.startswith("daily_reminder_") and job.data:
            j_user_id = job.data.get("user_id")
            j_chat_id = job.chat_id
            if j_user_id == user_id and j_chat_id == chat_id:
                job.schedule_removal()
                jobs_removed += 1

    await update.message.reply_text(f"✅ تم إلغاء جميع تذكيراتك اليومية ({jobs_removed} تذكير).")

async def cmd_my_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة التذكيرات اليومية للمستخدم"""
    user_id = update.effective_user.id
    
    reminders = await db.get_user_reminders(user_id)
    
    if not reminders:
        await update.message.reply_text("📭 ليس لديك أي تذكيرات يومية.")
        return
    
    text = "📋 **تذكيراتك اليومية:**\n\n"
    for i, r in enumerate(reminders, 1):
        text += f"{i}. ⏰ {r['reminder_time']} - 📝 {r['reminder_text']}\n"
    text += "\nللإلغاء: إلغاء تذكير يومي"
    
    await update.message.reply_text(text, parse_mode="Markdown")

# ==================== مستخدمين نشطين ====================
async def cmd_active_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض عدد المستخدمين النشطين هذا الشهر"""
    count = await db.count_active_users()
    await update.message.reply_text(f"👥 المستخدمين النشطين هذا الشهر: {count}")

# ==================== AUTO REPLY ====================
async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return

    text = msg.text.strip()
    for keyword, replies in AUTO_REPLIES.items():
        if keyword in text:
            await msg.reply_text(random.choice(replies))
            return

    if context.bot.username and f"@{context.bot.username.lower()}" in text.lower():
        await msg.reply_text("هلا! كيف أقدر أساعدك؟ 😊")

# ==================== MESSAGE TRACKING ====================
async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return

    user = update.effective_user
    chat = update.effective_chat
    full_name = f"{user.first_name} {user.last_name or ''}".strip()

    await db.update_user_activity(user.id, chat.id)
    await db.increment_message_count(user.id, chat.id, full_name)
    await db.save_chat_name(chat.id, chat.title or str(chat.id))

# ==================== WHISPER (النظام الجديد) ====================
async def cmd_whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        await msg.reply_text("❌ هذا الأمر للمجموعات فقط.")
        return

    if not msg.reply_to_message:
        await msg.reply_text("❗️ رد على رسالة الشخص ثم اكتب: همسة")
        return

    target = msg.reply_to_message.from_user
    sender = msg.from_user

    if target.is_bot:
        await msg.reply_text("❌ لا يمكن إرسال همسة لبوت.")
        return

    if target.id == sender.id:
        await msg.reply_text("❌ لا يمكنك إرسال همسة لنفسك.")
        return

    # حذف رسالة الأمر فوراً
    try:
        await msg.delete()
    except:
        pass

    # تخزين معرف المستهدف في user_data
    context.user_data['whisper_target_id'] = target.id
    context.user_data['whisper_target_name'] = target.first_name
    context.user_data['whisper_sender_name'] = sender.first_name
    context.user_data['whisper_chat_id'] = update.effective_chat.id

    # زر يفتح نافذة Inline Query في نفس القروب
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "✍️ اكتب همستك",
            switch_inline_query_current_chat=""
        )
    ]])
    await msg.reply_to_message.reply_text(
        f"💌 **همسة خاصة** من {sender.first_name} إلى {target.first_name}\n\n"
        "اضغط الزر أعلاه 👆 واكتب همستك.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def handle_whisper_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج استقبال الرد على طلب الهمسة (ForceReply)"""
    msg = update.message
    if not msg or not msg.reply_to_message:
        return

    # التحقق من أن المستخدم لديه جلسة همسة نشطة
    target_id = context.user_data.get('whisper_target_id')
    if not target_id:
        return

    # التحقق من أن الرد هو على رسالة البوت التي طلبت الهمسة
    if not msg.reply_to_message.from_user.is_bot:
        return

    target_name = context.user_data.pop('whisper_target_name', 'المستلم')
    chat_id = context.user_data.pop('whisper_chat_id', None)
    sender = msg.from_user
    whisper_text = msg.text

    # تنظيف الحالة
    context.user_data.pop('whisper_target_id', None)

    # حذف رسالة الأمر الأصلية ورسالة الطلب ورسالة الهمسة
    try:
        await msg.delete()
        await msg.reply_to_message.delete()
    except:
        pass

    # إنشاء معرف فريد للهمسة
    whisper_id = str(uuid.uuid4())[:12]

    # تخزين الهمسة في bot_data
    context.bot_data[f'whisper_{whisper_id}'] = {
        'sender_id': sender.id,
        'sender_name': sender.first_name,
        'target_id': target_id,
        'target_name': target_name,
        'text': whisper_text,
        'created_at': datetime.now().isoformat()
    }

    # إرسال زر الهمسة إلى المجموعة
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("💌 عرض الهمسة", callback_data=f"show_whisper_{whisper_id}")
    ]])
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"💌 **همسة خاصة**\nمن {sender.first_name} إلى {target_name}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# دوال الهمسة القديمة (للحفاظ على التوافق)
async def delete_whisper_job(context: ContextTypes.DEFAULT_TYPE, whisper_id: str):
    storage = context.bot_data.get('whisper_storage', {})
    if whisper_id in storage:
        del storage[whisper_id]
        print(f"🗑️ تم حذف الهمسة {whisper_id} (انتهت صلاحيتها)")

async def handle_whisper_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not context.args or not context.args[0].startswith("whisper_"):
        return

    whisper_id = context.args[0].replace("whisper_", "")
    whisper_storage = context.bot_data.get('whisper_storage', {})
    whisper_data = whisper_storage.get(whisper_id)

    if not whisper_data:
        await msg.reply_text("❌ انتهت صلاحية الهمسة أو الرابط غير صالح (الهمسة صالحة لمدة 5 دقائق).")
        return

    if whisper_data["sender_id"] != msg.from_user.id:
        await msg.reply_text(
            f"❌ هذا الرابط مخصص لـ {whisper_data['sender_name']}.\n"
            f"لا يمكنك استخدامه لأنك لست المرسل."
        )
        return

    context.user_data["active_whisper_id"] = whisper_id
    context.user_data["whisper_target_id"] = whisper_data["target_id"]
    context.user_data["whisper_target_name"] = whisper_data["target_name"]
    context.user_data["whisper_sender_name"] = whisper_data["sender_name"]

    await msg.reply_text(
        f"🔒 **همسة إلى {whisper_data['target_name']}**\n\n"
        f"✍️ اكتب الهمسة الآن.\n"
        f"(ستُرسل باسمك: {whisper_data['sender_name']})",
        parse_mode="Markdown"
    )

async def handle_whisper_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg or update.effective_chat.type != "private":
        return

    whisper_id = context.user_data.get("active_whisper_id")
    if not whisper_id:
        return

    target_id = context.user_data.get("whisper_target_id")
    target_name = context.user_data.get("whisper_target_name")
    sender_name = context.user_data.get("whisper_sender_name")

    if not target_id:
        await msg.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")
        context.user_data.pop("active_whisper_id", None)
        return

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                f"🔒 **همسة جديدة**\n\n"
                f"📤 من: **{sender_name}**\n"
                f"💬 الهمسة:\n"
                f"_{msg.text}_"
            ),
            parse_mode="Markdown"
        )

        await msg.reply_text(
            f"✅ **تم إرسال الهمسة بنجاح إلى {target_name}**\n\n"
            f"📝 نص همستك:\n_{msg.text}_",
            parse_mode="Markdown"
        )

        storage = context.bot_data.get('whisper_storage', {})
        if whisper_id in storage:
            del storage[whisper_id]

    except Exception as e:
        logger.error(f"خطأ في إرسال الهمسة: {e}")
        await msg.reply_text("❌ فشل إرسال الهمسة. تأكد من أن البوت ليس محظوراً من قبل المستخدم.")

    context.user_data.pop("active_whisper_id", None)
    context.user_data.pop("whisper_target_id", None)
    context.user_data.pop("whisper_target_name", None)
    context.user_data.pop("whisper_sender_name", None)

# ==================== GET INVITE ====================
async def cmd_get_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    try:
        link = await context.bot.create_chat_invite_link(update.effective_chat.id, member_limit=1)
        await update.message.reply_text(f"🔗 رابط المجموعة:\n{link.invite_link}")
    except:
        await update.message.reply_text("❌ لا يمكن إنشاء رابط.")

# ==================== SURAH & QURAN ====================
async def cmd_surah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: سورة [رقم السورة]\nمثال: سورة 1")
        return
    try:
        surah_num = int(context.args[0])
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.alquran.cloud/v1/surah/{surah_num}") as resp:
                if resp.status != 200:
                    await update.message.reply_text("❌ سورة غير موجودة.")
                    return
                data = await resp.json()
                surah = data["data"]
                name = surah["name"]
                english_name = surah["englishName"]
                await update.message.reply_text(f"📖 سورة {name} ({english_name})\nعدد الآيات: {surah['numberOfAyahs']}\nالترتيب: {surah['revelationType']}")
    except:
        await update.message.reply_text("الرقم غير صالح.")

async def cmd_quran_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: قران [رقم الصفحة]\nمثال: قران 1")
        return
    try:
        page = int(context.args[0])
        if page < 1 or page > 604:
            await update.message.reply_text("رقم الصفحة بين 1 و 604")
            return
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.alquran.cloud/v1/page/{page}") as resp:
                if resp.status != 200:
                    await update.message.reply_text("❌ خطأ في جلب الصفحة")
                    return
                data = await resp.json()
                verses = data["data"]["verses"]
                lines = [f"{v['text']}" for v in verses[:5]]
                text = "\n".join(lines)
                await update.message.reply_text(f"📖 صفحة {page}\n\n{text}\n\n...")
    except Exception as e:
        logger.error(f"خطأ في قران: {e}")
        await update.message.reply_text("حدث خطأ، تأكد من الرقم.")

# ==================== SPEAK & VOICE ====================
async def cmd_speak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: انطقي [النص]")
        return
    text = " ".join(context.args)
    await update.message.reply_text(f"🔊 (محاكاة نطق): {text}")

async def cmd_voice_to_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not update.message.reply_to_message.voice:
        await update.message.reply_text("الرجاء الرد على رسالة صوتية (فويس).")
        return
    await update.message.reply_text("🎙️ خدمة تحويل الصوت لنص غير متاحة حالياً، سيتم تفعيلها لاحقاً.")

# ==================== KICKME ====================
async def cmd_kickme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.unban_chat_member(chat_id, user_id)
        await update.message.reply_text("✅ تم طردك بناءً على طلبك.")
    except:
        await update.message.reply_text("❌ لا أستطيع طردك.")

# ==================== WELCOME ====================
async def cmd_enable_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await db.set_setting(update.effective_chat.id, "welcome_enabled", "yes")
    await update.message.reply_text("✅ تم تفعيل الترحيب.")

async def cmd_disable_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await db.set_setting(update.effective_chat.id, "welcome_enabled", "no")
    await update.message.reply_text("✅ تم تعطيل الترحيب.")

# ==================== BIO ====================
async def cmd_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        full = await context.bot.get_chat(user.id)
        bio = full.bio if full.bio else "لا يوجد بايو."
        await update.message.reply_text(f"📝 بايو العضو {user.first_name}:\n{bio}")
    except:
        await update.message.reply_text("لا يمكن جلب البايو حالياً.")

# ==================== OWNER ====================
async def cmd_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👨‍💻 المطور: Me8dad", parse_mode="Markdown")

# ==================== ANONYMOUS ====================
async def cmd_create_anon_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link_id = await db.create_anonymous_link(user_id)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=anon_{link_id}"
    await update.message.reply_text(f"🔗 رابط صارحني:\n{link}\n\n• أرسل هذا الرابط لأي شخص.\n• من يفتح الرابط سيرسل رسالة مجهولة إليك.\n• الرابط صالح دائماً.\n• لعرض رسائلك: استخدم أمر رسائلي.")

async def cmd_my_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    messages = await db.get_anonymous_messages(user_id)
    if not messages:
        await update.message.reply_text("📭 لا توجد رسائل مستلمة.")
        return
    text = "📬 رسائلك المستلمة:\n\n"
    for i, msg in enumerate(messages[:10], 1):
        text += f"{i}. {msg['message']}\n   ({msg['created_at'][:16]})\n\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ==================== TRANSLATE ====================
async def cmd_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message or not msg.reply_to_message.text:
        await msg.reply_text("❌ قم بالرد على رسالة نصية لترجمتها.")
        return

    original_text = msg.reply_to_message.text
    target_lang = "ar"

    try:
        import aiohttp
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": target_lang,
            "dt": "t",
            "q": original_text
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    raise Exception("API error")
                data = await resp.json()
                translated_parts = [part[0] for part in data[0] if part[0]]
                translated = ''.join(translated_parts)
                
        await msg.reply_text(
            f"🌐 **الترجمة إلى العربية:**\n\n{translated}\n\n"
            f"_النص الأصلي:_ {original_text[:100]}...",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"خطأ في الترجمة: {e}")
        await msg.reply_text("❌ خدمة الترجمة غير متاحة حالياً، حاول لاحقاً.")

# ==================== HANDLE PRIVATE MESSAGES ====================
async def handle_private_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or update.effective_chat.type != "private":
        return

    # ---- معالجة استقبال الهمسة (النظام الجديد) ----
    target_id = context.user_data.get('whisper_target_id')
    if target_id:
        await handle_whisper_reply(update, context)
        return

    # ---- النظام القديم للهمسات والرسائل المجهولة ----
    if context.user_data.get("active_whisper_id"):
        await handle_whisper_message(update, context)
        return

    anon_target = context.user_data.get("anon_target")
    if anon_target:
        await db.save_anonymous_message("", msg.text, update.effective_user.id)
        try:
            await context.bot.send_message(
                anon_target,
                f"📨 **رسالة جديدة (صارحني):**\n\n{msg.text}\n\n"
                f"لعرض جميع رسائلك: استخدم أمر `رسائلي`.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"فشل إرسال إشعار الرسالة المجهولة: {e}")
        await msg.reply_text("✅ تم إرسال رسالتك المجهولة.")
        context.user_data.pop("anon_target", None)
        return

# ==================== REGISTER ====================
def register_user_handlers(app):
    from telegram.ext import MessageHandler, filters
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_private_messages))
    # تسجيل معالج استقبال الرد على ForceReply (للهمسات)
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT & filters.ChatType.GROUPS, handle_whisper_reply))