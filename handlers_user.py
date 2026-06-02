import logging
import random
import uuid
import aiohttp
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from config import TIMEZONE
from helpers import is_admin, get_reply_user

logger = logging.getLogger(__name__)

AUTO_REPLIES = {
    "صباح الخير": ["صباح النور ☀️"],
    "صباح النور": ["صباح الورد 🌹"],
    "صباح الورد": ["صباح السعادة ☀️"],
    "مساء الخير": ["مساء النور 🌙"],
    "مساء النور": ["مساء الورد 🌹"],
    "مساء الورد": ["مساء السعادة 🌙"],
}

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0].startswith("anon_"):
        link_id = context.args[0].replace("anon_", "")
        target_user_id = await db.get_user_by_link(link_id)
        if not target_user_id:
            await update.message.reply_text("❌ هذا الرابط غير صالح.")
            return
        context.user_data["anon_target"] = target_user_id
        await update.message.reply_text("📝 **أرسل رسالتك المجهولة الآن.**")
        return
    await update.message.reply_text(
        "بوت شفق 🌅\n\n"
        "👮 أوامر المشرفين\n"
        "━━━━━━━━━━━━━━━\n"
        "🚫 الحظر:\n• حظر — حظر عضو\n• حظر 123 7d سبب — حظر مؤقت\n• رفع الحظر — رفع الحظر\n• قائمة — المحظورون\n• معلومات — تفاصيل الحظر\n• تحقق — هل هو محظور؟\n\n"
        "⚠️ التحذيرات:\n• تحذير — تحذير (3 = حظر تلقائي)\n• مسح التحذير — مسح التحذيرات\n• التحذيرات — عدد التحذيرات\n\n"
        "🔇 الكتم:\n• كتم — كتم عضو\n• كتم 123 1h — كتم مؤقت\n• رفع الكتم — رفع الكتم\n\n"
        "⚙️ الإدارة:\n• أغلق المجموعة / افتح المجموعة\n• أضف كلمة / احذف كلمة\n• الكلمات المحظورة\n• سجل — آخر الأحداث\n• تقرير — تقرير فوري\n• /setrules — تعيين القواعد\n• أضف مورد العنوان | المحتوى\n• احذف مورد <رقم>\n\n"
        "👥 للجميع\n"
        "━━━━━━━━━━━━━━━\n"
        "• ايدي — معلوماتك\n• القواعد — قواعد المجموعة\n• الموارد — قائمة الموارد\n• الموارد <كلمة> — بحث في الموارد\n• شفق <سؤال> — اسأل الذكاء الاصطناعي\n• تذكير 20:00 نص — تذكير\n• تذكير يومي 20:00 نص — تذكير يومي\n\n"
        "🎵 الميديا\n"
        "━━━━━━━━━━━━━━━\n"
        "• أرسل رابط مباشرة — تحميل\n• يوتيوب <اسم> — بحث\n"
    )

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

async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    rules = await db.get_setting(chat_id, "rules")
    if rules:
        await update.message.reply_text(f"📋 قواعد المجموعة:\n{rules}")
    else:
        await update.message.reply_text("لم يتم تعيين قواعد بعد.")

async def cmd_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import Chat as TGChat
    if update.effective_chat.type != TGChat.PRIVATE:
        await update.message.reply_text("أمر التذكير يعمل في الخاص فقط.")
        return
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("الاستخدام:\nتذكير 20:00 نص الرسالة\nتذكير يومي 20:00 نص الرسالة")
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
    except:
        await update.message.reply_text("صيغة الوقت خاطئة. استخدم 20:00")
        return
    user_id = update.effective_user.id
    now_local = datetime.now(TIMEZONE)
    if daily:
        from datetime import time as dtime
        target_time = dtime(hour=hour, minute=minute, second=0, tzinfo=TIMEZONE)
        context.job_queue.run_daily(_send_reminder, time=target_time, chat_id=user_id, name=f"daily_{user_id}", data=text)
        await update.message.reply_text(f"✅ تم ضبط تذكير يومي الساعة {time_str}:\n{text}")
    else:
        target = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now_local:
            target += datetime.timedelta(days=1)
        delay = (target - now_local).total_seconds()
        context.job_queue.run_once(_send_reminder, when=delay, chat_id=user_id, name=f"reminder_{user_id}", data=text)
        await update.message.reply_text(f"✅ تم ضبط تذكير الساعة {time_str}:\n{text}")

async def _send_reminder(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=context.job.chat_id, text=f"🔔 تذكير:\n{context.job.data}")

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

async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    from telegram import Chat as TGChat
    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return
    user = update.effective_user
    chat = update.effective_chat
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
await db.update_user_activity(user.id, chat.id)
    await db.increment_message_count(user.id, chat.id, full_name)
    await db.save_chat_name(chat.id, chat.title or str(chat.id))

# ========== الأوامر الجديدة ==========
async def cmd_whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ هذا الأمر للمجموعات فقط.")
        return
    if not context.args:
        await update.message.reply_text("❗️ الاستخدام: اهمس @username الرسالة")
        return
    target_username = context.args[0].replace('@', '')
    whisper_text = " ".join(context.args[1:])
    if not whisper_text:
        await update.message.reply_text("❌ لا يمكن إرسال همسة فارغة.")
        return
    try:
        target_user = await context.bot.get_chat(target_username)
        await context.bot.send_message(target_user.id, f"🔊 لديك همسة من {update.effective_user.mention_html()}:\n\n{whisper_text}", parse_mode="HTML")
        await update.message.reply_text(f"✅ تم الإرسال إلى {target_user.mention_html()}!", parse_mode="HTML")
    except:
        await update.message.reply_text("❌ لم أستطع الإرسال.")

async def cmd_get_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    try:
        link = await context.bot.create_chat_invite_link(update.effective_chat.id, member_limit=1)
        await update.message.reply_text(f"🔗 رابط المجموعة:\n{link.invite_link}")
    except:
        await update.message.reply_text("❌ لا يمكن إنشاء رابط.")

# ========== أوامر القرآن (API مجاني) ==========
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
                await update.message.reply_text(f"📖 **سورة {name} ({english_name})**\nعدد الآيات: {surah['numberOfAyahs']}\nالترتيب: {surah['revelationType']}")
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
                # عرض أول 3 آيات فقط (لأن الآيات كثيرة)
                lines = [f"{v['text']}" for v in verses[:5]]
                text = "\n".join(lines)
                await update.message.reply_text(f"📖 **صفحة {page}**\n\n{text}\n\n...")
    except Exception as e:
        logger.error(f"خطأ في قران: {e}")
        await update.message.reply_text("حدث خطأ، تأكد من الرقم.")
# ========== أمر انطقي (محاكاة) ==========
async def cmd_speak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: انطقي [النص]")
        return
    text = " ".join(context.args)
    await update.message.reply_text(f"🔊 (محاكاة نطق): {text}")

# ========== أمر وش يقول (تحويل الصوت لنص تجريبي) ==========
async def cmd_voice_to_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not update.message.reply_to_message.voice:
        await update.message.reply_text("الرجاء الرد على رسالة صوتية (فويس).")
        return
    await update.message.reply_text("🎙️ خدمة تحويل الصوت لنص غير متاحة حالياً، سيتم تفعيلها لاحقاً.")

async def cmd_kickme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.unban_chat_member(chat_id, user_id)
        await update.message.reply_text("✅ تم طردك بناءً على طلبك.")
    except:
        await update.message.reply_text("❌ لا أستطيع طردك.")

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

async def cmd_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        full = await context.bot.get_chat(user.id)
        bio = full.bio if full.bio else "لا يوجد بايو."
        await update.message.reply_text(f"📝 بايو العضو {user.first_name}:\n{bio}")
    except:
        await update.message.reply_text("لا يمكن جلب البايو حالياً.")

async def cmd_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👨‍💻 **المطور:** [Me8dad](https://t.me/Me8dad)", parse_mode="Markdown")

# ========== نظام صارحني ==========
async def cmd_create_anon_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link_id = await db.create_anonymous_link(user_id)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=anon_{link_id}"
    await update.message.reply_text(f"🔗 **رابط صارحني:**\n{link}\n\n• أرسل هذا الرابط لأي شخص.\n• من يفتح الرابط سيرسل رسالة مجهولة إليك.\n• الرابط صالح دائماً.\n• لعرض رسائلك: استخدم أمر `رسائلي`.")

async def cmd_my_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    messages = await db.get_anonymous_messages(user_id)
    if not messages:
        await update.message.reply_text("📭 لا توجد رسائل مستلمة.")
        return
    text = "📬 **رسائلك المستلمة:**\n\n"
    for i, msg in enumerate(messages[:10], 1):
        text += f"{i}. {msg['message']}\n   _({msg['created_at'][:16]})_\n\n"
    await update.message.reply_text(text, parse_mode="Markdown")
