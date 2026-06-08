# handlers/emergency.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode

from utils import database as db
from utils.helpers import is_admin
from config import ADMIN_CHAT_ID

# حالات المحادثة
ASK_NAME, ASK_PHONE, ASK_CITY = range(3)

# ========== أمر العضو: بدء تسجيل بيانات الطوارئ ==========
async def cmd_my_safety_net(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يبدأ محادثة خاصة لتسجيل بيانات الطوارئ"""
    user = update.effective_user
    msg = update.message

    # حذف الأمر من المجموعة مباشرة إذا كان في مجموعة
    if msg.chat.type != "private":
        try:
            await msg.delete()
        except:
            pass

    # إرسال رسالة خاصة
    try:
        await context.bot.send_message(
            chat_id=user.id,
            text="🛡️ **شبكة أماني**\n\n"
                 "لحفظ بيانات الطوارئ الخاصة بك (سرية تماماً).\n"
                 "يمكنك إلغاء العملية في أي وقت بكتابة /cancel\n\n"
                 "ما هو **اسمك الأول** فقط؟",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        await msg.reply_text("⚠️ الرجاء بدء محادثة خاصة مع البوت أولاً.")
        return ConversationHandler.END

    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['emergency_name'] = update.message.text.strip()
    await update.message.reply_text("📞 ما هو **رقم هاتفك**؟", parse_mode=ParseMode.MARKDOWN)
    return ASK_PHONE

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['emergency_phone'] = update.message.text.strip()
    await update.message.reply_text("📍 ما هي **مدينتك**؟", parse_mode=ParseMode.MARKDOWN)
    return ASK_CITY

async def ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    city = update.message.text.strip()
    name = context.user_data.get('emergency_name')
    phone = context.user_data.get('emergency_phone')

    success = await db.save_emergency_contact(
        user_id=user.id,
        first_name=name,
        phone_number=phone,
        city=city
    )

    if success:
        await update.message.reply_text("✅ تم حفظ بيانات الطوارئ الخاصة بك بنجاح.\n"
                                       "هذه البيانات سرية ولا تستخدم إلا في حالات الطوارئ القصوى.")
    else:
        await update.message.reply_text("❌ حدث خطأ، الرجاء المحاولة لاحقاً.")

    # حذف البيانات المؤقتة
    context.user_data.pop('emergency_name', None)
    context.user_data.pop('emergency_phone', None)

    return ConversationHandler.END

async def cancel_emergency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم إلغاء تسجيل بيانات الطوارئ.")
    context.user_data.pop('emergency_name', None)
    context.user_data.pop('emergency_phone', None)
    return ConversationHandler.END


# ========== أمر المشرف: جلب بيانات طوارئ لعضو محدد ==========
async def cmd_get_emergency_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    is_global_admin = user.id == ADMIN_CHAT_ID or await is_admin(update, context) is True
    is_emergency_admin = await db.is_admin_user(user.id)

    if not (is_global_admin or is_emergency_admin):
        await msg.reply_text("⛔ هذا الأمر خاص بالمشرفين المخولين فقط.")
        return

    if not context.args:
        await msg.reply_text("⚠️ يرجى كتابة الأمر متبوعاً بمعرف المستخدم:\n`/بيانات_طارئة 123456789`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await msg.reply_text("⚠️ معرف المستخدم غير صالح.")
        return

    contact = await db.get_emergency_contact(target_id)
    if not contact:
        await msg.reply_text(f"ℹ️ لا توجد بيانات طوارئ مسجلة للمستخدم `{target_id}`.", parse_mode=ParseMode.MARKDOWN)
        return

    alert_text = (
        f"🚨 **بيانات طوارئ** 🚨\n\n"
        f"👤 الاسم: {contact['first_name']}\n"
        f"📞 الهاتف: {contact['phone_number']}\n"
        f"📍 المدينة: {contact['city']}\n"
        f"🆔 معرف المستخدم: {target_id}\n\n"
        f"⚠️ هذه بيانات سرية. استخدمها فقط في حالة الطوارئ القصوى."
    )
    await msg.reply_text(alert_text, parse_mode=ParseMode.MARKDOWN)


# ========== أمر حذف بيانات الطوارئ ==========
async def cmd_delete_safety_net(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    success = await db.delete_emergency_contact(user.id)
    if success:
        await update.message.reply_text("🗑️ تم حذف بيانات الطوارئ الخاصة بك بنجاح.")
    else:
        await update.message.reply_text("ℹ️ لا توجد بيانات مسجلة لك.")


# ========== محادثة التسجيل ==========
def get_emergency_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("my_safety_net", cmd_my_safety_net)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_city)],
        },
        fallbacks=[CommandHandler("cancel", cancel_emergency)],
        per_chat=False,
        per_user=True,
    )