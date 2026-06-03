import logging
import random
import uuid
import aiohttp
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
        "• ايدي — معلوماتك\n• القواعد — قواعد المجموعة\n• الموارد — قائمة الموارد\n• الموارد <كلمة> — بحث في الموارد\n• شفق <سؤال> — اسأل الذكاء الاصطناعي\n• تذكير 5 نص — تذكير بعد دقائق\n• تذكير يومي 14:30 نص — تذكير يومي\n\n"
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

# ========== أوامر التذكير (المرة الواحدة واليومي) ==========
async def _send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """إرسال التذكير عند انتهاء الوقت"""
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=f"🔔 **تذكير:**\n{context.job.data}",
        parse_mode="Markdown"
    )

async def cmd_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تذكير لمرة واحدة بعد دقائق"""
    msg = update.message
    if not msg:
        return
    if not context.args or len(context.args) < 2:
        await msg.reply_text(
            "📌 **تذكير لمرة واحدة:**\n"
            "`تذكر 5 نص التذكير`\n\n"
            "• الرقم = عدد الدقائق (1-1440)\n"
            "• مثال: `تذكر 10 شرب الماء`",
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
        await msg.reply_text(f"✅ **تم ضبط التذكير:**\n⏰ بعد {minutes} دقيقة\n📝 {reminder_text}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"خطأ في التذكير: {e}")
        await msg.reply_text("❌ حدث خطأ.")

async def cmd_daily_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تذكير يومي في وقت محدد"""
    msg = update.message
    if not msg:
        return
    if not context.args or len(context.args) < 2:
        await msg.reply_text(
            "📌 **تذكير يومي:**\n"
            "`تذكير يومي 14:30 نص التذكير`\n\n"
            "• الوقت بصيغة HH:MM (24 ساعة)\n"
            "• مثال: `تذكير يومي 09:00 اجتماع العمل`",
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
    chat_id = msg.chat.id
    for job in context.job_queue.jobs():
        if job.name == f"daily_{chat_id}":
            job.schedule_removal()
    try:
        from datetime import time as dtime
        target_time = dtime(hour=hour, minute=minute, second=0, tzinfo=TIMEZONE)
        context.job_queue.run_daily(
            _send_reminder,
            time=target_time,
            chat_id=chat_id,
            name=f"daily_{chat_id}",
            data=reminder_text
        )
        await msg.reply_text(f"✅ **تم ضبط التذكير اليومي:**\n⏰ الساعة {time_str}\n📝 {reminder_text}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"خطأ في التذكير اليومي: {e}")
        await msg.reply_text("❌ حدث خطأ.")

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

# ========== الهمسة السرية (طريقة الزر) ==========
async def cmd_whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء همسة سرية لشخص معين"""
    msg = update.message
    
    # فقط في المجموعات
    if update.effective_chat.type == "private":
        await msg.reply_text("❌ هذا الأمر للمجموعات فقط.")
        return
    
    if not msg.reply_to_message:
        await msg.reply_text("❗️ قم بالرد على رسالة الشخص ثم اكتب: اهمس")
        return
    
    target = msg.reply_to_message.from_user
    if target.is_bot:
        await msg.reply_text("❌ لا يمكن إرسال همسة لبوت.")
        return
    
    # تخزين معلومات مؤقتة
    context.user_data['whisper_target'] = target.id
    context.user_data['whisper_target_name'] = target.first_name
    context.user_data['whisper_group'] = update.effective_chat.id
    context.user_data['waiting_whisper'] = True
    
    await msg.reply_text(
        f"🔒 **همسة لـ {target.first_name}**\n\n"
        f"✍️ أرسل نص الهمسة الآن في الخاص.",
        parse_mode="Markdown"
    )

# ========== الأوامر الأخرى ==========
async def cmd_get_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    try:
        link = await context.bot.create_chat_invite_link(update.effective_chat.id, member_limit=1)
        await update.message.reply_text(f"🔗 رابط المجموعة:\n{link.invite_link}")
    except:
        await update.message.reply_text("❌ لا يمكن إنشاء رابط.")

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
                lines = [f"{v['text']}" for v in verses[:5]]
                text = "\n".join(lines)
                await update.message.reply_text(f"📖 **صفحة {page}**\n\n{text}\n\n...")
    except Exception as e:
        logger.error(f"خطأ في قران: {e}")
        await update.message.reply_text("حدث خطأ، تأكد من الرقم.")

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

async def cmd_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message or not msg.reply_to_message.text:
        await msg.reply_text("❌ قم بالرد على رسالة نصية لترجمتها.")
        return
    
    original_text = msg.reply_to_message.text
    target_lang = "ar"
    
    try:
        from googletrans import Translator
        translator = Translator()
        result = await translator.translate(original_text, dest=target_lang)
        translated = result.text
        await msg.reply_text(
            f"🌐 **الترجمة إلى العربية:**\n\n{translated}\n\n"
            f"_الرسالة الأصلية:_ {original_text[:100]}...",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"خطأ في الترجمة: {e}")
        await msg.reply_text("❌ خدمة الترجمة غير متاحة حالياً، حاول لاحقاً.")