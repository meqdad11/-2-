"""
ملف المستخدم - نسخة محسنة (يشمل نظام الهمسات بشكل كامل يعمل فعلياً)
"""

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

# ==================== START ====================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    # ===== الهمسة =====
    if context.args and context.args[0].startswith("whisper_"):
        whisper_id = context.args[0].replace("whisper_", "")

        data = await db.get_whisper(whisper_id)
        if not data:
            await msg.reply_text("❌ انتهت صلاحية الهمسة.")
            return

        context.user_data["whisper_id"] = whisper_id
        await msg.reply_text("✍️ اكتب الهمسة الآن:")
        return

    # ===== صارحني (anonymous) =====
    if context.args and context.args[0].startswith("anon_"):
        link_id = context.args[0].replace("anon_", "")
        target_user_id = await db.get_user_by_link(link_id)

        if not target_user_id:
            await msg.reply_text("❌ هذا الرابط غير صالح.")
            return

        context.user_data["anon_target"] = target_user_id
        await msg.reply_text("📝 أرسل رسالتك المجهولة الآن.")
        return

    await msg.reply_text(
        "بوت شفق 🌅\n\n"
        "👮 أوامر المشرفين + أوامر المستخدمين مفعلة"
    )


# ==================== ID ====================

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
    except:
        pass

    await update.message.reply_text(caption)


# ==================== WHISPER SYSTEM (FULL FIX) ====================

async def cmd_whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if update.effective_chat.type == "private":
        await msg.reply_text("❌ هذا الأمر للمجموعات فقط.")
        return

    if not msg.reply_to_message:
        await msg.reply_text("❗️ رد على الشخص ثم اكتب: اهمس")
        return

    target = msg.reply_to_message.from_user

    if target.is_bot:
        await msg.reply_text("❌ لا يمكن إرسال همسة لبوت.")
        return

    whisper_id = str(uuid.uuid4())[:8]

    await db.save_whisper(
        whisper_id=whisper_id,
        sender_id=msg.from_user.id,
        target_id=target.id,
        chat_id=update.effective_chat.id
    )

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=whisper_{whisper_id}"

    await msg.reply_text(
        f"🔒 همسة لـ {target.first_name}\n\n"
        f"اضغط الرابط وأرسل الرسالة:\n{link}"
    )


# ==================== START HANDLER COMPLETION ====================

async def handle_private_whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg or update.effective_chat.type != "private":
        return

    whisper_id = context.user_data.get("whisper_id")
    if not whisper_id:
        return

    data = await db.get_whisper(whisper_id)
    if not data:
        await msg.reply_text("❌ انتهت صلاحية الهمسة.")
        return

    await context.bot.send_message(
        chat_id=data["target_id"],
        text=f"🔒 همسة جديدة:\n\n{msg.text}"
    )

    await msg.reply_text("✅ تم إرسال الهمسة.")

    context.user_data.pop("whisper_id", None)


# ==================== AUTO REPLY ====================

async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    from telegram import Chat as TGChat
    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return

    text = msg.text.strip()

    for k, replies in AUTO_REPLIES.items():
        if k in text:
            await msg.reply_text(random.choice(replies))
            return

    if context.bot.username and f"@{context.bot.username.lower()}" in text.lower():
        await msg.reply_text("هلا! كيف أقدر أساعدك؟")


# ==================== MESSAGE TRACKING ====================

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


# ==================== SIMPLE COMMANDS ====================

async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    rules = await db.get_setting(chat_id, "rules")

    if rules:
        await update.message.reply_text(f"📋 القواعد:\n{rules}")
    else:
        await update.message.reply_text("لا توجد قواعد.")


async def cmd_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👨‍💻 المطور: Me8dad")


# ==================== TRANSLATE COMMAND ====================

async def cmd_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ترجمة النص باستخدام Google Translate API (بدون مفتاح API)
    الاستخدام: /translate <النص>  أو /tr <النص>
    """
    msg = update.message
    if not msg.reply_to_message and not context.args:
        await msg.reply_text("❌ استخدم: /translate <النص> أو رد على رسالة")
        return

    # تحديد النص المراد ترجمته
    if msg.reply_to_message and msg.reply_to_message.text:
        text_to_translate = msg.reply_to_message.text
    else:
        text_to_translate = " ".join(context.args)

    if not text_to_translate:
        await msg.reply_text("❌ لا يوجد نص للترجمة.")
        return

    # تحديد اللغة المصدر والهدف (افتراضي: إنكليزي <-> عربي)
    target_lang = "ar"
    source_lang = "en"

    parts = text_to_translate.split(" ", 1)
    if len(parts) == 2 and ":" in parts[0]:
        lang_pair = parts[0].split(":")
        if len(lang_pair) == 2:
            source_lang = lang_pair[0].strip()
            target_lang = lang_pair[1].strip()
            text_to_translate = parts[1]

    # طلب الترجمة
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": source_lang,
            "tl": target_lang,
            "dt": "t",
            "q": text_to_translate
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    await msg.reply_text("❌ فشل الاتصال بخدمة الترجمة.")
                    return
                data = await resp.json()

        translated_text = ""
        for part in data[0]:
            if part[0]:
                translated_text += part[0]

        if not translated_text:
            await msg.reply_text("❌ لم يتم الحصول على ترجمة.")
            return

        await msg.reply_text(
            f"🌐 الترجمة:\n\n{translated_text}\n\n"
            f"({source_lang.upper()} → {target_lang.upper()})"
        )

    except Exception as e:
        logger.error(f"Translation error: {e}")
        await msg.reply_text("❌ حدث خطأ أثناء الترجمة.")


# ==================== GET INVITE COMMAND (ADDED) ====================

async def cmd_get_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    الحصول على رابط دعوة للمجموعة (للمشرفين فقط)
    الاستخدام: /get_invite
    """
    chat = update.effective_chat
    user = update.effective_user

    # التأكد من أن الأمر في مجموعة
    from telegram import Chat as TGChat
    if chat.type == "private":
        await update.message.reply_text(
            "⚠️ هذا الأمر للمجموعات فقط.\n\n"
            "استخدمه في المجموعة التي تريد الحصول على رابطها."
        )
        return

    # التحقق من صلاحيات المشرف
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return

    try:
        invite_link = await chat.export_invite_link()
        await update.message.reply_text(
            f"🔗 رابط دعوة المجموعة:\n\n{invite_link}\n\n"
            f"⏳ الصلاحية: غير محدودة (حتى يتم تغييره)"
        )
    except Exception as e:
        logger.error(f"Failed to get invite link: {e}")
        await update.message.reply_text(
            "❌ فشل في الحصول على رابط الدعوة.\n\n"
            "تأكد من أن البوت لديه الصلاحيات التالية:\n"
            "• دعوة المستخدمين عبر الرابط (Invite Users)"
        )


# ==================== REGISTER ====================

def register_user_handlers(app):
    from telegram.ext import MessageHandler, filters

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_private_whisper))