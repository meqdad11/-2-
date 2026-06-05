import logging
import json
import tempfile
import asyncio
import os
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from utils import database as db
from utils.database import supabase

logger = logging.getLogger(__name__)

# ========== المطور الأساسي (لا يمكن إزالته) ==========
MAIN_DEVELOPER = 729970974

async def is_owner(update: Update) -> bool:
    """التحقق من أن المستخدم مطور (من قاعدة البيانات)"""
    return await db.is_developer(update.effective_user.id)

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
        success = await db.add_developer(user_id)
        if success:
            await update.message.reply_text(f"✅ تم رفع {user_id} كمطور.")
        else:
            await update.message.reply_text("المطور موجود مسبقاً أو حدث خطأ.")
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
        # لا يمكن إزالة المطور الأساسي
        if user_id == MAIN_DEVELOPER:
            await update.message.reply_text("❌ لا يمكن إزالة المطور الأساسي.")
            return
        success = await db.remove_developer(user_id)
        if success:
            await update.message.reply_text(f"✅ تم تنزيل {user_id} من المطورين.")
        else:
            await update.message.reply_text("المعرف غير موجود أو حدث خطأ.")
    except:
        await update.message.reply_text("المعرف غير صالح.")

# ========== إذاعة لكل المجموعات ==========
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إذاعة لكل المجموعات (للمطور فقط)"""
    user = update.effective_user
    
    if not await is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return
    
    if not context.args:
        await update.message.reply_text("📢 **الاستخدام:**\nاذاعه <النص>\n\nمثال: اذاعه مرحباً جميعاً", parse_mode="Markdown")
        return
    
    text = " ".join(context.args)
    chats = await db.get_all_active_chats()
    success = 0
    
    await update.message.reply_text(f"⏳ جاري الإرسال إلى {len(chats)} مجموعة...")
    
    for chat_id in chats:
        try:
            await context.bot.send_message(chat_id, f"📢 **إذاعة من المطور:**\n\n{text}", parse_mode="Markdown")
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"فشل الإرسال للمجموعة {chat_id}: {e}")
    
    await update.message.reply_text(f"✅ تم الإرسال إلى {success} من {len(chats)} مجموعة.")

# ========== إحصائيات البوت (التفصيلية الجديدة) ==========
async def cmd_bot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات شاملة لكل مجموعة (للمطور فقط)"""
    if not await is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return

    status_msg = await update.message.reply_text("⏳ جاري تجميع الإحصائيات...")

    chats = await db.get_all_active_chats()
    total_chats = len(chats)

    if total_chats == 0:
        await status_msg.edit_text("📭 لا توجد مجموعات نشطة.")
        return

    report_lines = []
    report_lines.append(f"📊 **إحصائيات البوت الشاملة**\n")
    report_lines.append(f"📌 عدد المجموعات النشطة: {total_chats}\n")

    for chat_id in chats:
        chat_name = await db.get_chat_name(chat_id)
        members = await db.get_top_members(chat_id, limit=10000)

        if not members:
            continue

        total_members = len(members)
        report_lines.append(f"\n🟢 **{chat_name}** (`{chat_id}`)")
        report_lines.append(f"👥 عدد الأعضاء المسجلين: {total_members}")

        for i, member in enumerate(members, 1):
            user_id = member['user_id']
            full_name = member.get('full_name', 'بدون اسم')
            msg_count = member.get('message_count', 0)
            report_lines.append(f"   {i}. {full_name} — {msg_count} رسالة")

    full_report = "\n".join(report_lines)

    max_len = 4000
    if len(full_report) > max_len:
        chunks = [full_report[i:i+max_len] for i in range(0, len(full_report), max_len)]
    else:
        chunks = [full_report]

    await status_msg.edit_text("📤 جاري إرسال التقرير...")
    for chunk in chunks:
        await update.message.reply_text(chunk, parse_mode="Markdown")

    await status_msg.delete()

# ========== عدد المستخدمين النشطين ==========
async def cmd_active_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عدد المستخدمين النشطين هذا الشهر"""
    if not await is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return
    count = await db.count_active_users()
    await update.message.reply_text(f"📊 **المستخدمون النشطون هذا الشهر:** {count}")

# ========== نسخ احتياطي للمطور ==========
async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نسخ احتياطي لجميع جداول قاعدة البيانات (للمطور فقط)"""
    if not await is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return
    
    status_msg = await update.message.reply_text("⏳ جاري إنشاء النسخة الاحتياطية...")
    
    tables = [
        "bans", "warnings", "settings", "user_stats", "group_locks",
        "anon_links", "anon_messages", "user_activity", "crisis_words",
        "crisis_settings", "custom_replies", "custom_commands", "ban_log",
        "reminders", "assistants", "developers"
    ]
    
    backup_data = {}
    
    for table in tables:
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda t=table: supabase.table(t).select("*").execute()
            )
            backup_data[table] = result.data
        except Exception as e:
            backup_data[table] = {"error": str(e)}
    
    backup_data["_metadata"] = {
        "backup_date": datetime.now().isoformat(),
        "bot_version": "شفق 1.0",
        "tables_count": len(tables)
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
        temp_path = f.name
    
    await status_msg.edit_text("📤 جاري إرسال الملف...")
    
    with open(temp_path, 'rb') as f:
        await context.bot.send_document(
            chat_id=update.effective_user.id,
            document=f,
            filename=f"shafaq_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            caption="📦 **نسخة احتياطية لقاعدة البيانات**\n"
                    f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"📊 عدد الجداول: {len(tables)}\n\n"
                    "⚠️ احتفظ بهذا الملف في مكان آمن.",
            parse_mode="Markdown"
        )
    
    os.unlink(temp_path)
    
    await status_msg.edit_text("✅ تم إنشاء وإرسال النسخة الاحتياطية بنجاح.")