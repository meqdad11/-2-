"""
نظام كلمات الأزمات - لكل مجموعة كلماتها وردها الخاص (نسخة محسنة)
"""

import logging
import re
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from helpers import is_admin

logger = logging.getLogger(__name__)

# ==================== أوامر المشرفين ====================

async def cmd_add_crisis_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return

    if not context.args:
        await update.message.reply_text(
            "📌 الاستخدام:\n"
            "• فردي: اضف كلمة ازمة انتحار\n"
            "• جماعي: اضف كلمات ازمة انتحار, أذى النفس, اموت\n",
        )
        return

    full_text = " ".join(context.args)

    if "," in full_text:
        words = [w.strip().lower() for w in full_text.split(",") if w.strip()]
    else:
        words = [full_text.lower()]

    added, existing = [], []

    for word in words:
        success = await db.add_crisis_word(chat_id, word)
        if success:
            added.append(word)
        else:
            existing.append(word)

    reply = ""

    if added:
        reply += "✅ تم إضافة الكلمات:\n" + "\n".join(f"• {w}" for w in added)

    if existing:
        reply += "\n\n⚠️ كلمات موجودة مسبقاً:\n" + "\n".join(f"• {w}" for w in existing)

    await update.message.reply_text(reply)


async def cmd_remove_crisis_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return

    if not context.args:
        await update.message.reply_text("📌 الاستخدام: حذف كلمة ازمة انتحار")
        return

    word = " ".join(context.args).lower()
    success = await db.remove_crisis_word(chat_id, word)

    if success:
        await update.message.reply_text(f"✅ تم حذف: {word}")
    else:
        await update.message.reply_text(f"⚠️ غير موجودة: {word}")


async def cmd_list_crisis_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    words = await db.get_crisis_words(chat_id)

    if not words:
        await update.message.reply_text("📭 لا توجد كلمات أزمة.")
        return

    all_words = [w["word"] for w in words]
    chunks = [all_words[i:i+30] for i in range(0, len(all_words), 30)]

    for i, chunk in enumerate(chunks, 1):
        text = (
            f"🚨 كلمات الأزمات ({i}/{len(chunks)}):\n\n"
            + "\n".join(f"• {w}" for w in chunk)
        )
        await update.message.reply_text(text)


async def cmd_set_crisis_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return

    if not context.args:
        await update.message.reply_text(
            "📌 الاستخدام:\nرد الازمة نص الرسالة"
        )
        return

    # 🔴 الحل الأساسي: حفظ النص كامل مع الأسطر بدون context.args
    full_text = update.message.text
    reply_text = full_text.split(" ", 2)[2] if len(full_text.split(" ", 2)) > 2 else ""

    await db.set_crisis_reply(chat_id, reply_text)

    await update.message.reply_text("✅ تم حفظ رسالة الرد التلقائي.")


async def cmd_enable_crisis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return

    await db.set_crisis_enabled(chat_id, True)

    await update.message.reply_text("✅ تم تفعيل نظام كلمات الأزمات.")


async def cmd_disable_crisis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return

    await db.set_crisis_enabled(chat_id, False)

    await update.message.reply_text("❌ تم تعطيل نظام كلمات الأزمات.")


async def cmd_crisis_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    enabled = await db.get_crisis_enabled(chat_id)
    words_count = await db.get_crisis_words_count(chat_id)
    reply_text = await db.get_crisis_reply(chat_id)

    status = "🟢 مفعل" if enabled else "🔴 معطل"

    text = (
        f"🚨 حالة النظام\n\n"
        f"📊 الحالة: {status}\n"
        f"📝 عدد الكلمات: {words_count}\n\n"
    )

    if reply_text:
        text += f"💬 رسالة الرد:\n{reply_text[:200]}"
        if len(reply_text) > 200:
            text += "..."
    else:
        text += "⚠️ لا يوجد رد مخصص."

    await update.message.reply_text(text)


# ==================== معالج الرسائل التلقائي ====================

async def check_crisis_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if not message or not message.text:
        return

    chat_id = message.chat_id

    if message.from_user and message.from_user.is_bot:
        return

    enabled = await db.get_crisis_enabled(chat_id)
    if not enabled:
        return

    crisis_words = await db.get_crisis_words(chat_id)
    if not crisis_words:
        return

    reply_text = await db.get_crisis_reply(chat_id)
    if not reply_text:
        return

    text_lower = message.text.lower()

    for item in crisis_words:
        word = item["word"].lower()
        pattern = r"\b" + re.escape(word) + r"\b"

        if re.search(pattern, text_lower):
            # إرسال مباشر مع الحفاظ على التنسيق
            await message.reply_text(reply_text)
            await db.log_crisis_alert(
                chat_id,
                word,
                message.from_user.id if message.from_user else 0
            )
            logger.info(f"Crisis word detected: {word} in {chat_id}")
            break


def register_crisis_handlers(app):
    pass