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

# ========== قائمة المطورين ==========
DEVELOPERS = [729970974]  # ضع معرفك هنا

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
    """إذاعة لكل المجموعات (للمطور فقط)"""
    user = update.effective_user
    
    # تحقق إذا كان المرسل هو المطور
    if user.id not in DEVELOPERS:
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
            await asyncio.sleep(0.05)  # تأخير بسيط عشان لا يصير تجاوز للحد
        except Exception as e:
            logger.error(f"فشل الإرسال للمجموعة {chat_id}: {e}")
    
    await update.message.reply_text(f"✅ تم الإرسال إلى {success} من {len(chats)} مجموعة.")
# ========== إحصائيات البوت ==========
async def cmd_bot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return
    chats = len(await db.get_all_active_chats())
    await update.message.reply_text(
        f"📊 **إحصائيات البوت:**\n"
        f"• المجموعات النشطة: {chats}\n"
    )

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
    
    # قائمة الجداول المراد نسخها
    tables = [
        "bans", "warnings", "settings", "user_stats", "group_locks",
        "anon_links", "anon_messages", "user_activity", "crisis_words",
        "crisis_settings", "custom_replies", "custom_commands", "ban_log"
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
    
    # إضافة معلومات النسخة
    backup_data["_metadata"] = {
        "backup_date": datetime.now().isoformat(),
        "bot_version": "شفق 1.0",
        "tables_count": len(tables)
    }
    
    # إنشاء ملف JSON مؤقت
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
        temp_path = f.name
    
    # إرسال الملف للمطور
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
    
    # حذف الملف المؤقت
    os.unlink(temp_path)
    
    await status_msg.edit_text("✅ تم إنشاء وإرسال النسخة الاحتياطية بنجاح.")