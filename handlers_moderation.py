import logging
import database as db
from telegram import Update
from telegram.ext import ContextTypes
from helpers import require_admin, is_admin, get_reply_user
from config import MAX_WARNINGS

# ================================================

logger = logging.getLogger(__name__)

CRISIS_KEYWORDS = [
    "انتحار", "انتحرت", "أنتحر", "بنتحر", "بينتحر", "سأنتحر", "راح انتحر",
    "اقتل نفسي", "أقتل نفسي", "بقتل نفسي", "يقتل نفسه", "يقتل نفسي", "سأقتل نفسي",
    "أذيت", "أذيت نفسي", "اذيت نفسي", "أضر نفسي", "اضر نفسي", "أضر بنفسي",
    "أموت", "بموت", "ابي اموت", "أبي أموت", "ابغى اموت", "أبغى أموت",
    "ودي أموت", "اتمنى الموت", "اخنق نفسي", "أخنق نفسي",
    "suicide", "kill myself", "end my life", "want to die", "self harm",
]

CRISIS_REPLY = """
يبدو أنك تمر بلحظة صعبة 🆘

أنت لست وحدك 🤍

📞 أرقام الدعم والمساعدة في السعودية:

- 937 - وزارة الصحة (استشارات ودعم صحي ونفسي)

- 920033360 - مركز الاستشارات والدعم النفسي

- 1919 - بلاغات العنف الأسري والحماية الاجتماعية

- 116111 - خط حماية الطفل

- 999 - الشرطة

- 997 - الهلال الأحمر (الإسعاف)

- 998 - الدفاع المدني

- 911 - الطوارئ العامة

أو تحدث مع أحد المشرفين أو الأعضاء، نحن معك. 💙
"""

# ================================================

async def cmd_add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: أضف كلمة <الكلمة>")
        return
    word = " ".join(context.args).lower().strip()
    chat_id = update.effective_chat.id
    added = await db.add_banned_word(chat_id, word)
    if added:
        await update.message.reply_text(f"✅ تمت إضافة الكلمة: {word}")
    else:
        await update.message.reply_text(f"الكلمة '{word}' موجودة مسبقاً.")

# ================================================

async def cmd_remove_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: احذف كلمة <الكلمة>")
        return
    word = " ".join(context.args).lower().strip()
    chat_id = update.effective_chat.id
    removed = await db.remove_banned_word(chat_id, word)
    if removed:
        await update.message.reply_text(f"✅ تمت إزالة الكلمة: {word}")
    else:
        await update.message.reply_text(f"الكلمة '{word}' غير موجودة.")

# ================================================

async def cmd_list_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    words = await db.get_banned_words(chat_id)
    if not words:
        await update.message.reply_text("لا توجد كلمات محظورة.")
        return
    await update.message.reply_text("🚫 الكلمات المحظورة:\n" + "\n".join(f"• {w}" for w in words))

# ================================================

async def filter_banned_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    from telegram import Chat as TGChat
    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return
    chat_id = update.effective_chat.id
    user = update.effective_user
    text = msg.text.lower()

    for keyword in CRISIS_KEYWORDS:
        if keyword.lower() in text:
            try:
                await msg.reply_text(CRISIS_REPLY)
            except Exception as e:
                logger.error("خطأ في إرسال رسالة الأزمة: %s", e)
            return

    if await is_admin(update, context):
        return

    words = await db.get_banned_words(chat_id)
    for word in words:
        if word in text:
            try:
                await msg.delete()
            except Exception:
                pass
            count = await db.add_warning(user.id, chat_id)
            if count >= MAX_WARNINGS:
                await db.add_ban(user.id, chat_id, f"حظر تلقائي بعد {MAX_WARNINGS} تحذيرات", 0)
                try:
                    await context.bot.ban_chat_member(chat_id, user.id)
                except Exception:
                    pass
                await db.clear_warnings(user.id, chat_id)
                await context.bot.send_message(
                    chat_id,
                    f"⛔ تم حظر {user.full_name} بعد {MAX_WARNINGS} تحذيرات."
                )
                await db.log_bot_action(chat_id, "auto_ban_word", user_id=user.id, detail=word)
            else:
                await context.bot.send_message(
                    chat_id,
                    f"⚠️ {user.full_name}، رسالتك تحتوي كلمات غير لائقة.\n"
                    f"التحذير {count}/{MAX_WARNINGS}"
                )
            return