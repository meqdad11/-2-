import logging
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.helpers import is_admin
from utils.database import supabase

logger = logging.getLogger(__name__)

# ========================================
# دوال قاعدة البيانات
# ========================================

async def save_support_setting(chat_id: int, field: str, value):
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

async def save_encouragement(chat_id: int, text: str) -> bool:
    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: supabase.table("encouragements").insert({
                "chat_id": chat_id,
                "text": text,
                "used": False,
            }).execute()
        )
        return True
    except Exception as e:
        logger.error(f"save_encouragement error: {e}")
        return False

async def get_random_encouragement(chat_id: int) -> dict | None:
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: supabase.table("encouragements")
                .select("*")
                .eq("chat_id", chat_id)
                .eq("used", False)
                .execute()
        )
        if not result.data:
            return None
        item = random.choice(result.data)
        # نحدد الرسالة كمستخدمة
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: supabase.table("encouragements")
                .update({"used": True})
                .eq("id", item["id"])
                .execute()
        )
        return item
    except Exception as e:
        logger.error(f"get_random_encouragement error: {e}")
        return None

# ========================================
# أوامر الضبط
# ========================================

async def cmd_setup_admin_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    chat_id = update.effective_chat.id
    success = await save_support_setting(chat_id, "admin_group_id", chat_id)
    if success:
        await update.message.reply_text(
            f"✅ تم ضبط هذه المجموعة كـ **غرفة المشرفين**.\n\n"
            f"🆔 معرف هذه المجموعة:\n`{chat_id}`\n\n"
            f"الآن اذهب لمجموعة الأعضاء واكتب:\n"
            f"`ضبط دعم الأعضاء {chat_id}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ فشل الحفظ، حاول مرة أخرى.")

async def cmd_setup_members_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    if not context.args:
        await update.message.reply_text(
            "⚠️ اكتب معرف مجموعة المشرفين بعد الأمر.\n\n"
            "مثال:\n`ضبط دعم الأعضاء -100123456789`",
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
            f"✅ تم الربط بنجاح!\n\n"
            f"الأعضاء الآن يمكنهم استخدام:\n"
            f"• `أحتاج أحد` — طلب مساعدة فورية\n"
            f"• `أرسل تشجيع` — إرسال كلمة دعم سرية\n"
            f"• `تشجيع` — استلام كلمة دعم عشوائية",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ فشل الحفظ، حاول مرة أخرى.")

# ========================================
# أحتاج أحد
# ========================================

async def cmd_need_someone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "مجموعة"

    admin_group_id = await get_admin_group(chat_id)

    await msg.reply_text(
        "💙 لست وحدك.\n\n"
        "تم إبلاغ المشرفين وسيتواصلون معك قريباً.\n\n"
        "إذا كنت في خطر فوري:\n"
        "📞 الطوارئ: **911**\n"
        "📞 الدعم النفسي: **920033360**",
        parse_mode="Markdown"
    )

    if not admin_group_id:
        return

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
# إرسال تشجيع — سري عبر DM
# ========================================

async def cmd_send_encouragement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ينشر زر يفتح محادثة خاصة مع البوت لكتابة التشجيع"""
    chat_id = update.effective_chat.id
    bot_username = context.bot.username

    # نحفظ chat_id في start payload عشان البوت يعرف أي مجموعة
    keyboard = [[InlineKeyboardButton(
        "💌 اكتب تشجيعك سراً",
        url=f"https://t.me/{bot_username}?start=enc_{chat_id}"
    )]]

    await update.message.reply_text(
        "💛 اضغط الزر أدناه لإرسال كلمة تشجيع سرية — لن يعرف أحد أنك أرسلتها.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_start_encouragement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعالج /start enc_CHATID في المحادثة الخاصة"""
    msg = update.message
    if not context.args:
        return False

    arg = context.args[0]
    if not arg.startswith("enc_"):
        return False

    try:
        chat_id = int(arg.replace("enc_", ""))
    except ValueError:
        return False

    context.user_data["enc_chat_id"] = chat_id
    await msg.reply_text(
        "💌 اكتب كلمة تشجيعك الآن:\n"
        "(ستُحفظ وتُرسل لشخص يحتاجها لاحقاً بدون اسمك)"
    )
    return True

async def handle_private_encouragement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """يستقبل نص التشجيع في المحادثة الخاصة"""
    msg = update.message
    chat_id = context.user_data.get("enc_chat_id")
    if not chat_id:
        return False

    text = msg.text.strip()
    if not text:
        return False

    context.user_data.pop("enc_chat_id")
    success = await save_encouragement(chat_id, text)

    if success:
        await msg.reply_text("✅ تم حفظ تشجيعك 💙\nسيصل لشخص يحتاجه في الوقت المناسب.")
    else:
        await msg.reply_text("❌ فشل الحفظ، حاول مرة أخرى.")
    return True

# ========================================
# طلب تشجيع — عام في المجموعة
# ========================================

async def cmd_get_encouragement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يسحب رسالة عشوائية من المخزون وينشرها"""
    chat_id = update.effective_chat.id
    item = await get_random_encouragement(chat_id)

    if not item:
        keyboard = [[InlineKeyboardButton(
            "💌 أرسل تشجيعاً",
            url=f"https://t.me/{context.bot.username}?start=enc_{chat_id}"
        )]]
        await update.message.reply_text(
            "💛 لا توجد رسائل تشجيع حالياً.\nكن أول من يكتب كلمة تُضيء يوم أحدهم!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await update.message.reply_text(
        f"💛 *رسالة تشجيع*\n\n_{item['text']}_\n\n— من أحد أعضاء المجموعة 🤍",
        parse_mode="Markdown"
    )
