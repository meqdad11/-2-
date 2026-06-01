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
# الأوامر القديمة (الكلمات المحظورة)
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

async def cmd_list_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    words = await db.get_banned_words(chat_id)
    if not words:
        await update.message.reply_text("لا توجد كلمات محظورة.")
        return
    await update.message.reply_text("🚫 الكلمات المحظورة:\n" + "\n".join(f"• {w}" for w in words))

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

# ================================================
# ========== الأوامر الجديدة (الردود والاختصارات) ==========
# ================================================

# هيكل تخزين الردود والاختصارات (مؤقت، يمكن نقلها إلى قاعدة البيانات لاحقاً)
_custom_replies = {}   # {chat_id: {keyword: reply}}
_custom_commands = {}  # {chat_id: {command_word: target_command}}

# 1. إضافة رد
async def cmd_add_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if len(context.args) < 2:
        await update.message.reply_text("الاستخدام: اضف رد <الكلمة> <الرد>")
        return
    keyword = context.args[0].lower()
    reply = " ".join(context.args[1:])
    chat_id = update.effective_chat.id
    if chat_id not in _custom_replies:
        _custom_replies[chat_id] = {}
    _custom_replies[chat_id][keyword] = reply
    await update.message.reply_text(f"✅ تم إضافة رد تلقائي للكلمة '{keyword}'.")

# 2. حذف رد
async def cmd_remove_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: حذف رد <الكلمة>")
        return
    keyword = context.args[0].lower()
    chat_id = update.effective_chat.id
    if chat_id in _custom_replies and keyword in _custom_replies[chat_id]:
        del _custom_replies[chat_id][keyword]
        await update.message.reply_text(f"✅ تم حذف الرد التلقائي للكلمة '{keyword}'.")
    else:
        await update.message.reply_text("الرد غير موجود.")

# 3. عرض الردود المضافه
async def cmd_list_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    replies = _custom_replies.get(chat_id, {})
    if not replies:
        await update.message.reply_text("لا توجد ردود مضافه.")
        return
    lines = [f"• {key} -> {value}" for key, value in replies.items()]
    await update.message.reply_text("📝 الردود المضافه:\n" + "\n".join(lines))

# 4. إضافة أمر اختصار
async def cmd_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if len(context.args) < 2:
        await update.message.reply_text("الاستخدام: اضف امر <الاختصار> <الأمر الأصلي>")
        return
    shortcut = context.args[0].lower()
    target = " ".join(context.args[1:]).lower()
    chat_id = update.effective_chat.id
    if chat_id not in _custom_commands:
        _custom_commands[chat_id] = {}
    _custom_commands[chat_id][shortcut] = target
    await update.message.reply_text(f"✅ تم إضافة اختصار '{shortcut}' للأمر '{target}'.")

# 5. حذف أمر اختصار
async def cmd_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: حذف امر <الاختصار>")
        return
    shortcut = context.args[0].lower()
    chat_id = update.effective_chat.id
    if chat_id in _custom_commands and shortcut in _custom_commands[chat_id]:
        del _custom_commands[chat_id][shortcut]
        await update.message.reply_text(f"✅ تم حذف الاختصار '{shortcut}'.")
    else:
        await update.message.reply_text("الاختصار غير موجود.")

# 6. عرض الأوامر المضافه
async def cmd_list_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    cmds = _custom_commands.get(chat_id, {})
    if not cmds:
        await update.message.reply_text("لا توجد أوامر مضافه.")
        return
    lines = [f"• {shortcut} -> {target}" for shortcut, target in cmds.items()]
    await update.message.reply_text("📌 الأوامر المضافه:\n" + "\n".join(lines))

# 7. معالج الردود التلقائية والاختصارات (يُستدعى من handle_text)
async def process_custom_replies_and_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    text = msg.text.strip().lower()
    chat_id = update.effective_chat.id

    # الردود التلقائية
    if chat_id in _custom_replies:
        for keyword, reply in _custom_replies[chat_id].items():
            if keyword in text:
                await msg.reply_text(reply)
                return

    # الاختصارات (تبدأ مثلاً بـ '!' أو بدون)
    if text.startswith('!'):  # مثلاً !سجل
        cmd = text[1:].split()[0] if ' ' in text else text[1:]
        if chat_id in _custom_commands and cmd in _custom_commands[chat_id]:
            target_cmd = _custom_commands[chat_id][cmd]
            # محاكاة تنفيذ الأمر المستهدف (يمكن تحسينها)
            context.args = target_cmd.split()[1:] if ' ' in target_cmd else []
            # نحتاج إلى إيجاد الدالة المناسبة في ARABIC_COMMANDS
            from commands import ARABIC_COMMANDS
            for arabic_cmd, handler in ARABIC_COMMANDS.items():
                if arabic_cmd == target_cmd.split()[0]:
                    await handler(update, context)
                    return
            await msg.reply_text(f"⚠️ الأمر المستهدف '{target_cmd}' غير موجود.")