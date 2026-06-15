from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from config import STAFF_ROLES, ROLE_NAMES
from utils.database import (
    set_staff_role, remove_staff_role, get_staff_role,
    get_group_staff, log_staff_action
)

DEVELOPER_ID = 729970974

async def get_rank(user_id: int, group_id: int) -> int:
    if user_id == DEVELOPER_ID:
        return 5
    role = await get_staff_role(user_id, group_id)
    return STAFF_ROLES.get(role, 0)

async def assign_role(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    user = update.effective_user
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("❌ هذا الأمر للمجموعات فقط.")
        return

    admin_rank = await get_rank(user.id, chat.id)
    if admin_rank < 4:
        await update.message.reply_text("❌ صلاحية تعيين الرتب محصورة في المدير والمطور.")
        return

    if len(args) < 2:
        await update.message.reply_text("❌ استخدم: تعيين @المعرف الرتبة\nالرتب: مساعد، مشرف، مشرف أول، مدير")
        return

    target_username = args[0].lstrip("@")
    role_name = " ".join(args[1:])

    try:
        member = await chat.get_member(f"@{target_username}")
    except:
        await update.message.reply_text("❌ لم أجد العضو في المجموعة.")
        return

    if role_name not in STAFF_ROLES:
        await update.message.reply_text("❌ رتبة غير معروفة. الرتب المتاحة: مساعد، مشرف، مشرف أول، مدير")
        return

    target_rank_value = STAFF_ROLES[role_name]

    if admin_rank == 4 and target_rank_value >= 4:
        await update.message.reply_text("❌ المدير لا يمكنه تعيين مدير آخر.")
        return

    if admin_rank == 5:
        pass
    elif target_rank_value >= admin_rank:
        await update.message.reply_text("❌ لا يمكنك تعيين عضو برتبة تساوي أو تعلو رتبتك.")
        return

    current_target_rank = await get_rank(member.user.id, chat.id)
    if current_target_rank >= admin_rank:
        await update.message.reply_text("❌ لا يمكنك تعيين عضو رتبته الحالية تساوي أو تعلو رتبتك.")
        return

    await set_staff_role(member.user.id, chat.id, role_name, user.id)
    await log_staff_action(chat.id, user.id, member.user.id, "تعيين", f"إلى {role_name}")

    await update.message.reply_text(
        f"✅ تم تعيين {member.user.mention_html()} كـ {role_name}.\n"
        f"بواسطة: {user.mention_html()}",
        parse_mode="HTML"
    )

async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    user = update.effective_user
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("❌ هذا الأمر للمجموعات فقط.")
        return

    admin_rank = await get_rank(user.id, chat.id)
    if admin_rank < 4:
        await update.message.reply_text("❌ العزل محصور في المدير والمطور.")
        return

    if len(args) < 1:
        await update.message.reply_text("❌ استخدم: عزل @المعرف")
        return

    target_username = args[0].lstrip("@")

    try:
        member = await chat.get_member(f"@{target_username}")
    except:
        await update.message.reply_text("❌ لم أجد العضو في المجموعة.")
        return

    target_rank = await get_rank(member.user.id, chat.id)
    if target_rank == 0:
        await update.message.reply_text("❌ العضو ليس لديه أي رتبة.")
        return

    if target_rank >= admin_rank:
        await update.message.reply_text("❌ لا يمكنك عزل عضو برتبة تساوي أو تعلو رتبتك.")
        return

    old_role = await get_staff_role(member.user.id, chat.id)
    await remove_staff_role(member.user.id, chat.id)
    await log_staff_action(chat.id, user.id, member.user.id, "عزل", f"من {old_role}")

    await update.message.reply_text(
        f"✅ تم عزل {member.user.mention_html()} من رتبة {old_role}.\n"
        f"بواسطة: {user.mention_html()}",
        parse_mode="HTML"
    )

async def list_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("❌ هذا الأمر للمجموعات فقط.")
        return

    staff = await get_group_staff(chat.id)
    if not staff:
        await update.message.reply_text("👥 لا يوجد طاقم معيّن في هذه المجموعة.")
        return

    lines = ["👥 **طاقم المجموعة:**\n"]
    for row in staff:
        try:
            member = await chat.get_member(row["user_id"])
            name = member.user.mention_html()
        except:
            name = f"<code>{row['user_id']}</code>"
        lines.append(f"{row['role']}: {name} (منذ {row['assigned_at'].strftime('%Y-%m-%d')})")
    
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def my_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("هذا الأمر للمجموعات فقط.")
        return

    rank = await get_rank(user.id, chat.id)
    role_name = ROLE_NAMES.get(rank, "عضو")
    if rank == 5:
        role_name = "مطور البوت"
    await update.message.reply_text(f"🌟 رتبتك الحالية: {role_name}")

async def my_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("هذا الأمر للمجموعات فقط.")
        return

    rank = await get_rank(user.id, chat.id)
    role_name = ROLE_NAMES.get(rank, "عضو")
    if rank == 5:
        role_name = "مطور"

    permissions = {
        1: "🗑 حذف رسائل · ⚠️ تحذير (من هم أدنى)",
        2: "🗑 حذف · ⚠️ تحذير · 🔇 كتم مؤقت ورفعه (مساعدين وأعضاء)",
        3: "🔓 كل الصلاحيات على من هم أدنى (مساعدين، مشرفين، أعضاء) - عقوبات + إدارة المجموعة (أقفال، أزمات، دعم، تذكيرات)",
        4: "👑 جميع صلاحيات المشرف الأول + تعيين وعزل المساعدين والمشرفين والمشرفين الأوائل",
        5: "⚜️ تحكم كامل (مطور)"
    }

    msg = f"📋 صلاحيات رتبة **{role_name}**:\n{permissions.get(rank, 'لا توجد صلاحيات خاصة')}"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def staff_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    args = text.split()
    cmd = args[0]

    if cmd in ["تعيين", "ترقية"]:
        await assign_role(update, context, args[1:])
    elif cmd in ["عزل", "تنزيل"]:
        await demote(update, context, args[1:])
    elif cmd == "الرتب":
        await list_roles(update, context)
    elif cmd == "رتبتي":
        await my_role(update, context)
    elif cmd == "صلاحياتي":
        await my_permissions(update, context)

staff_handler = MessageHandler(
    filters.TEXT & filters.Regex(r'^(تعيين|ترقية|عزل|تنزيل|الرتب|رتبتي|صلاحياتي)'),
    staff_dispatcher
)