import logging
from telegram import Update
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# ========== قائمة المطورين (استبدل الرقم بمعرفك) ==========
DEVELOPERS = [729970974]  # <--- ضع معرف حسابك هنا

async def is_owner(update: Update) -> bool:
    return update.effective_user.id in DEVELOPERS

# ========== رفع مطور ==========
async def cmd_add_dev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر للمطور الأساسي فقط.")
        return
    if not context.args:
        await update.message.reply_text("استخدام: رفع مطور <المعرف>")
        return
    try:
        user_id = int(context.args[0])
        if user_id not in DEVELOPERS:
            DEVELOPERS.append(user_id)
            await update.message.reply_text(f"✅ تم رفع {user_id} كمطور.")
        else:
            await update.message.reply_text("المطور موجود مسبقاً.")
    except:
        await update.message.reply_text("المعرف غير صالح.")

# ========== تنزيل مطور ==========
async def cmd_remove_dev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر للمطور الأساسي فقط.")
        return
    if not context.args:
        await update.message.reply_text("استخدام: تنزيل مطور <المعرف>")
        return
    try:
        user_id = int(context.args[0])
        if user_id in DEVELOPERS and user_id != DEVELOPERS[0]:
            DEVELOPERS.remove(user_id)
            await update.message.reply_text(f"✅ تم تنزيل {user_id} من المطورين.")
        else:
            await update.message.reply_text("لا يمكن إزالة المطور الأساسي أو المعرف غير موجود.")
    except:
        await update.message.reply_text("المعرف غير صالح.")

# ========== إذاعة لكل المجموعات ==========
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return
    if not context.args:
        await update.message.reply_text("استخدام: اذاعه <النص>")
        return
    text = " ".join(context.args)
    chats = await db.get_all_active_chats()
    success = 0
    for chat_id in chats:
        try:
            await context.bot.send_message(chat_id, f"📢 **إذاعة من المطور:**\n{text}", parse_mode="Markdown")
            success += 1
        except:
            pass
    await update.message.reply_text(f"✅ تم الإرسال إلى {success} من {len(chats)} مجموعة.")

# ========== إحصائيات البوت (كاملة) ==========
async def cmd_bot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return
    chats = len(await db.get_all_active_chats())
    users = sum(1 for s in db._cache.get("user_stats", {}).values())
    locks = sum(1 for l in db._cache.get("group_locks", {}).values() if l.get("is_locked"))
    bans = len(db._cache.get("bans", {}))
    await update.message.reply_text(
        f"📊 **إحصائيات البوت:**\n"
        f"• المجموعات النشطة: {chats}\n"
        f"• المستخدمين المسجلين: {users}\n"
        f"• عدد الحظر: {bans}\n"
        f"• الأقفال المفعلة: {locks}"
    )

# ========== إحصائيات سريعة (للاستخدام العادي) ==========
async def cmd_simple_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات سريعة للمطور"""
    if not await is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return
    chats = len(await db.get_all_active_chats())
    users = sum(1 for s in db._cache.get("user_stats", {}).values())
    bans = len(db._cache.get("bans", {}))
    locks = sum(1 for l in db._cache.get("group_locks", {}).values() if l.get("is_locked"))
    await update.message.reply_text(
        f"📈 **إحصائيات البوت:**\n"
        f"• المجموعات: {chats}\n"
        f"• المستخدمين: {users}\n"
        f"• المحظورين: {bans}\n"
        f"• الأقفال النشطة: {locks}"
    )