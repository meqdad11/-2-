import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import database as db
from utils.helpers import is_admin

logger = logging.getLogger(__name__)

# ========================================
# دوال قاعدة البيانات
# ========================================

async def get_support_settings(chat_id: int) -> dict:
    try:
        result = await db.supabase_fetch(
            "support_settings", filters={"chat_id": chat_id}
        )
        return result[0] if result else {}
    except Exception as e:
        logger.error(f"get_support_settings error: {e}")
        return {}

async def save_support_setting(chat_id: int, field: str, value):
    import asyncio
    from utils.database import supabase
    try:
        existing = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: supabase.table("support_settings").select("*").eq("chat_id", chat_id).execute()
        )
        if existing.data:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: supabase.table("support_settings").update({field: value}).eq("chat_id", chat_id).execute()
            )
        else:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: supabase.table("support_settings").insert({"chat_id": chat_id, field: value}).execute()
            )
        return True
    except Exception as e:
        logger.error(f"save_support_setting error: {e}")
        return False

async def get_admin_group(members_chat_id: int) -> int | None:
    import asyncio
    from utils.database import supabase
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: supabase.table("support_settings").select("admin_group_id").eq("chat_id", members_chat_id).execute()
        )
        if result.data:
            return result.data[0].get("admin_group_id")
    except Exception as e:
        logger.error(f"get_admin_group error: {e}")
    return None

async def get_members_group(admin_group_id: int) -> int | None:
    import asyncio
    from utils.database import supabase
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: supabase.table("support_settings").select("chat_id").eq("admin_group_id", admin_group_id).execute()
        )
        if result.data:
            return result.data[0].get("chat_id")
    except Exception as e:
        logger.error(f"get_members_group error: {e}")
    return None

# ========================================
# أوامر الضبط
# ========================================

async def cmd_setup_admin_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ضبط دعم المشرفين — يُنفَّذ في مجموعة المشرفين"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    chat_id = update.effective_chat.id
    success = await save_support_setting(chat_id, "admin_group_id", chat_id)
    if success:
        await update.message.reply_text(
            "✅ تم ضبط هذه المجموعة كـ **غرفة المشرفين** لنظام الدعم.\n\n"
            "الآن اذهب لمجموعة الأعضاء واكتب: `ضبط دعم الأعضاء`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ فشل الحفظ، حاول مرة أخرى.")

async def cmd_setup_members_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ضبط دعم الأعضاء — يُنفَّذ في مجموعة الأعضاء"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ اكتب معرف مجموعة المشرفين بعد الأمر.\n"
            "مثال: `ضبط دعم الأعضاء -100123456789`\n\n"
            "تجد المعرف بكتابة `ضبط دعم المشرفين` في غرفة المشرفين أولاً.",
            parse_mode="Markdown"
        )
        return

    try:
        admin_group_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ معرف غير صحيح.")
        return

    chat_id = update.effective_chat.id
    success = await save_support_setting(chat_id, "admin_group_id", admin_group_id)
    if success:
        await update.message.reply_text(
            f"✅ تم ربط هذه المجموعة بغرفة المشرفين.\n"
            f"الآن الأعضاء يمكنهم استخدام:\n"
            f"• `أحتاج أحد` — طلب مساعدة فورية\n"
            f"• `أرسل تشجيع` — إرسال كلمة دعم مجهولة",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ فشل الحفظ، حاول مرة أخرى.")

# ========================================
# أحتاج أحد
# ========================================

async def cmd_need_someone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عضو يطلب مساعدة فورية"""
    msg = update.message
    user = update.effective_user
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "مجموعة"

    admin_group_id = await get_admin_group(chat_id)

    # رد فوري على العضو
    await msg.reply_text(
        "💙 لست وحدك.\n\n"
        "تم إبلاغ المشرفين الآن وسيتواصلون معك قريباً.\n"
        "إذا كنت في خطر فوري، اتصل بالطوارئ 911 أو خط الدعم النفسي 920033360.",
        parse_mode="Markdown"
    )

    if not admin_group_id:
        logger.warning(f"No admin group configured for chat {chat_id}")
        return

    # إبلاغ مجموعة المشرفين
    user_mention = f"[{user.full_name}](tg://user?id={user.id})"
    alert_text = (
        f"🆘 **طلب مساعدة فورية**\n\n"
        f"👤 العضو: {user_mention}\n"
        f"🆔 المعرف: `{user.id}`\n"
        f"💬 المجموعة: {chat_title}\n\n"
        f"يرجى التواصل معه في أقرب وقت."
    )

    keyboard = [[InlineKeyboardButton(
        f"💬 راسل {user.first_name}",
        url=f"tg://user?id={user.id}"
    )]]

    try:
        await context.bot.send_message(
            admin_group_id,
            alert_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Failed to notify admin group: {e}")

# ========================================
# إرسال تشجيع مجهول
# ========================================

async def cmd_send_encouragement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عضو يرسل تشجيعاً مجهولاً لعضو آخر"""
    msg = update.message
    chat_id = update.effective_chat.id

    if not context.args:
        context.user_data["waiting_encouragement"] = chat_id
        await msg.reply_text(
            "💌 اكتب كلمة التشجيع التي تريد إرسالها:\n"
            "(ستصل بدون اسمك لعضو عشوائي في المجموعة)"
        )
        return

    text = " ".join(context.args)
    await _send_encouragement_message(update, context, text)

async def handle_encouragement_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """معالجة نص التشجيع بعد الطلب"""
    msg = update.message
    if context.user_data.get("waiting_encouragement") != update.effective_chat.id:
        return False

    context.user_data.pop("waiting_encouragement")
    await _send_encouragement_message(update, context, msg.text)
    return True

async def _send_encouragement_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    chat_id = update.effective_chat.id

    # نرسل التشجيع للمجموعة بشكل مجهول
    encouragement_text = (
        f"💛 **رسالة تشجيع مجهولة**\n\n"
        f"_{text}_\n\n"
        f"— من أحد أعضاء المجموعة 🤍"
    )

    try:
        await context.bot.send_message(
            chat_id,
            encouragement_text,
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ تم إرسال تشجيعك بنجاح 💙")
    except Exception as e:
        logger.error(f"Failed to send encouragement: {e}")
        await update.message.reply_text("❌ فشل الإرسال.")
