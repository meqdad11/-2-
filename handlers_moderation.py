import logging
import database as db
from telegram import Update
from telegram.ext import ContextTypes
from helpers import require_admin, is_admin, get_reply_user
from config import MAX_WARNINGS

# ================================================

logger = logging.getLogger(__name__)

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

# 1. إضافة رد (مخزن في قاعدة البيانات)
async def cmd_add_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if len(context.args) < 2:
        await update.message.reply_text("الاستخدام: اضف رد <الكلمة> <الرد>")
        return
    keyword = context.args[0].lower()
    reply = " ".join(context.args[1:])
    chat_id = update.effective_chat.id
    
    added = await db.add_custom_reply(chat_id, keyword, reply)
    if added:
        await update.message.reply_text(f"✅ تم إضافة رد تلقائي للكلمة '{keyword}'.")
    else:
        await update.message.reply_text(f"⚠️ الرد للكلمة '{keyword}' موجود مسبقاً.")

# 2. حذف رد
async def cmd_remove_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: حذف رد <الكلمة>")
        return
    keyword = context.args[0].lower()
    chat_id = update.effective_chat.id
    
    removed = await db.remove_custom_reply(chat_id, keyword)
    if removed:
        await update.message.reply_text(f"✅ تم حذف الرد التلقائي للكلمة '{keyword}'.")
    else:
        await update.message.reply_text("⚠️ الرد غير موجود.")

# 3. عرض الردود المضافه
async def cmd_list_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    replies = await db.get_custom_replies(chat_id)
    
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
    
    added = await db.add_custom_command(chat_id, shortcut, target)
    if added:
        await update.message.reply_text(f"✅ تم إضافة اختصار '{shortcut}' للأمر '{target}'.")
    else:
        await update.message.reply_text(f"⚠️ الاختصار '{shortcut}' موجود مسبقاً.")

# 5. حذف أمر اختصار
async def cmd_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: حذف امر <الاختصار>")
        return
    shortcut = context.args[0].lower()
    chat_id = update.effective_chat.id
    
    removed = await db.remove_custom_command(chat_id, shortcut)
    if removed:
        await update.message.reply_text(f"✅ تم حذف الاختصار '{shortcut}'.")
    else:
        await update.message.reply_text("⚠️ الاختصار غير موجود.")

# 6. عرض الأوامر المضافه
async def cmd_list_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    cmds = await db.get_custom_commands(chat_id)
    
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

    # الردود التلقائية من قاعدة البيانات
    replies = await db.get_custom_replies(chat_id)
    for keyword, reply in replies.items():
        if keyword in text:
            await msg.reply_text(reply)
            return

    # الاختصارات (تبدأ بـ '!')
    if text.startswith('!'):
        cmd = text[1:].split()[0] if ' ' in text else text[1:]
        commands = await db.get_custom_commands(chat_id)
        if cmd in commands:
            target_cmd = commands[cmd]
            context.args = target_cmd.split()[1:] if ' ' in target_cmd else []
            from commands import ARABIC_COMMANDS
            for arabic_cmd, handler in ARABIC_COMMANDS.items():
                if arabic_cmd == target_cmd.split()[0]:
                    await handler(update, context)
                    return
            await msg.reply_text(f"⚠️ الأمر المستهدف '{target_cmd}' غير موجود.")
