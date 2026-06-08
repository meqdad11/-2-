# handlers/emergency.py
import secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils import database as db
from utils.helpers import is_admin
from config import ADMIN_CHAT_ID

# قواميس مؤقتة (للجلسة فقط)
_pending_admins = {}   # admin_user_id -> {"user_id": target_user_id, "expires": timestamp}
_web_tokens = {}       # user_id -> token (يُستخدم لربط صفحة الويب بالعضو)


# ========== أمر العضو: تسجيل / عرض بياناته ==========
async def cmd_my_safety_net(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    يسمح للعضو بالاطلاع على بياناته المسجلة، أو حذفها، أو تسجيل بيانات جديدة.
    يستخدم رابطاً آمناً مؤقتاً لصفحة الويب.
    """
    user = update.effective_user
    msg = update.message

    # توليد رمز فريد مؤقت لصفحة الويب
    token = secrets.token_urlsafe(16)
    _web_tokens[user.id] = token

    # رابط صفحة الويب (سنضبطه لاحقاً بعد نشر الخادم)
    web_base = context.bot_data.get("web_base_url", "https://your-railway-app.up.railway.app")
    web_link = f"{web_base}/emergency?user_id={user.id}&token={token}"

    keyboard = [
        [InlineKeyboardButton("📝 تسجيل / تعديل بياناتي", url=web_link)],
        [InlineKeyboardButton("🗑️ حذف بياناتي", callback_data="delete_emergency_data")],
    ]

    # جلب البيانات الحالية إن وجدت
    contact = await db.get_emergency_contact(user.id)
    if contact:
        info_text = (
            f"🛡️ **بياناتك الحالية:**\n"
            f"الاسم: {contact['first_name']}\n"
            f"الهاتف: {contact['phone_number']}\n"
            f"المدينة: {contact['city']}\n\n"
            f"هذه البيانات سرية ولا تُستخدم إلا في حالات الطوارئ القصوى."
        )
    else:
        info_text = (
            "🛡️ **لم تسجل بيانات طوارئ بعد.**\n\n"
            "بتسجيلك لهذه البيانات، تمنحنا القدرة على مساعدتك بسرعة إذا شعرت يوماً أنك في خطر."
        )

    await msg.reply_text(
        info_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


# ========== أمر المشرف: جلب بيانات طوارئ لعضو محدد ==========
async def cmd_get_emergency_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    للمشرفين المخولين فقط: جلب بيانات الطوارئ لعضو معين.
    الاستخدام: /بيانات_طارئة <user_id>
    """
    user = update.effective_user
    msg = update.message

    # التحقق من كون المستخدم مشرفاً عاماً أو مشرف طوارئ
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


# ========== معالج الحذف (عبر الـ callback) ==========
async def callback_delete_emergency_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    success = await db.delete_emergency_contact(user.id)
    if success:
        await query.answer("تم حذف بياناتك بنجاح.", show_alert=True)
        await query.edit_message_text("🛡️ تم حذف بيانات الطوارئ الخاصة بك. يمكنك إعادة تسجيلها متى شئت.")
    else:
        await query.answer("لم نتمكن من الحذف. ربما بياناتك غير موجودة.", show_alert=True)