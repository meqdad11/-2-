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


async def _get_target_id(update: Update, context, args: list):
    """
    ترجع user_id للعضو المستهدف، أو None.
    الطرق: 1) الرد على رسالته 2) @username 3) ID رقمي
    """
    msg = update.message
    chat = update.effective_chat

    # 1. الرد
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target = msg.reply_to_message.from_user
        try:
            await chat.get_member(target.id)
            return target.id
        except:
            return None

    # 2. آيدي أو يوزر من أول وسيط
    if args and len(args) > 0:
        identifier = args[0].lstrip("@")
        # آيدي رقمي
        if identifier.isdigit():
            try:
                await chat.get_member(int(identifier))
                return int(identifier)
            except:
                pass
        # يوزر
        try:
            member = await chat.get_member(f"@{identifier}")
            return member.user.id
        except:
            pass

    return None


async def assign_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("❌ هذا الأمر للمجموعات فقط.")
        return

    admin_rank = await get_rank(user.id, chat.id)
    if admin_rank < 4:
        await update.message.reply_text("❌ صلاحية تعيين الرتب محصورة في المدير والمطور.")
        return

    # إعداد args
    if not context.args:
        text = update.message.text.strip()
        args = text.split()[1:] if len(text.split()) > 1 else []
    else:
        args = list(context.args)

    target_id = None
    role_name = None

    if update.message.reply_to_message:
        # الرد موجود ← كل الكلام بعد الأمر هو اسم الرتبة
        role_name = " ".join(args) if args else None
        target_id = await _get_target_id(update, context, [])
        if not role_name:
            await update.message.reply_text("❌ حدد الرتبة، مثال: ترقية مشرف أول")
            return
    else:
        # بدون رد ← أول كلمة معرّف، الباقي رتبة
        if len(args) < 2:
            await update.message.reply_text(
                "❌ استخدم:\n"
                "• `تعيين @المعرف الرتبة`\n"
                "• `تعيين id الرتبة`\n"
                "• بالرد على رسالته: `تعيين الرتبة`",
                parse_mode="Markdown"
            )
            return
        target_id = await _get_target_id(update, context, [args[0]])
        role_name = " ".join(args[1:])

    if not target_id:
        await update.message.reply_text("❌ لم أستطع العثور على العضو. تأكد من اليوزر أو الآيدي أو قم بالرد على رسالته.")
        return

    if role_name not in STAFF_ROLES:
        await update.message.reply_text("❌ رتبة غير معروفة. الرتب المتاحة: مساعد، مشرف، مشرف أول، مدير")
        return

    target_rank_value = STAFF_ROLES[role_name]

    if admin_rank == 4 and target_rank_value >= 4:
        await update.message.reply_text("❌ المدير لا يمكنه تعيين مدير آخر.")
        return

    if admin_rank != 5 and target_rank_value >= admin_rank:
        await update.message.reply_text("❌ لا يمكنك تعيين عضو برتبة تساوي أو تعلو رتبتك.")
        return

    current_target_rank = await get_rank(target_id, chat.id)
    if current_target_rank >= admin_rank:
        await update.message.reply_text("❌ لا يمكنك تعيين عضو رتبته الحالية تساوي أو تعلو رتبتك.")
        return

    await set_staff_role(target_id, chat.id, role_name, user.id)
    await log_staff_action(chat.id, user.id, target_id, "تعيين", f"إلى {role_name}")

    try:
        member = await chat.get_member(target_id)
        mention = member.user.mention_html()
    except:
        mention = f"<code>{target_id}</code>"

    await update.message.reply_text(
        f"✅ تم تعيين {mention} كـ {role_name}.\n"
        f"بواسطة: {user.mention_html()}",
        parse_mode="HTML"
    )


async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("❌ هذا الأمر للمجموعات فقط.")
        return

    admin_rank = await get_rank(user.id, chat.id)
    if admin_rank < 4:
        await update.message.reply_text("❌ العزل محصور في المدير والمطور.")
        return

    # إعداد args
    if not context.args:
        text = update.message.text.strip()
        args = text.split()[1:] if len(text.split()) > 1 else []
    else:
        args = list(context.args)

    target_id = None

    if update.message.reply_to_message:
        # الرد موجود ← الهدف هو الشخص المردود عليه
        target_id = await _get_target_id(update, context, [])
    else:
        # بدون رد ← أول كلمة معرّف
        if len(args) < 1:
            await update.message.reply_text(
                "❌ استخدم:\n"
                "• `عزل @المعرف`\n"
                "• `عزل id`\n"
                "• بالرد على رسالته: `عزل`",
                parse_mode="Markdown"
            )
            return
        target_id = await _get_target_id(update, context, [args[0]])

    if not target_id:
        await update.message.reply_text("❌ لم أستطع العثور على العضو.")
        return

    target_rank = await get_rank(target_id, chat.id)
    if target_rank == 0:
        await update.message.reply_text("❌ العضو ليس لديه أي رتبة.")
        return

    if target_rank >= admin_rank:
        await update.message.reply_text("❌ لا يمكنك عزل عضو برتبة تساوي أو تعلو رتبتك.")
        return

    old_role = await get_staff_role(target_id, chat.id)
    await remove_staff_role(target_id, chat.id)
    await log_staff_action(chat.id, user.id, target_id, "عزل", f"من {old_role}")

    try:
        member = await chat.get_member(target_id)
        mention = member.user.mention_html()
    except:
        mention = f"<code>{target_id}</code>"

    await update.message.reply_text(
        f"✅ تم عزل {mention} من رتبة {old_role}.\n"
        f"بواسطة: {user.mention_html()}",
        parse_mode="HTML"
    )


async def list_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("❌ هذا الأمر للمجموعات فقط.")
        return

    # جلب طاقم البوت
    staff = await get_group_staff(chat.id)
    staff_dict = {}
    for row in staff:
        staff_dict[row["user_id"]] = row

    lines = ["👥 **طاقم المجموعة:**\n"]
    added_ids = set()

    # إضافة مشرفي تيليجرام أولاً (مالك ومشرفين)
    try:
        admins = await chat.get_administrators()
        for admin in admins:
            uid = admin.user.id
            if uid == context.bot.id:  # تجاهل البوت نفسه
                continue
            added_ids.add(uid)
            mention = admin.user.mention_html()
            if admin.status == "creator":
                role_text = "👑 المالك"
            else:
                role_text = "👮 مشرف"
            
            # إذا كان لديه رتبة بوت، نضيفها
            if uid in staff_dict:
                bot_role = staff_dict[uid]["role"]
                role_text += f" • {bot_role}"
                date_str = str(staff_dict[uid].get("assigned_at", ""))[:10]
                lines.append(f"{role_text}: {mention} (منذ {date_str})")
            else:
                lines.append(f"{role_text}: {mention}")
    except Exception:
        pass

    # إضافة طاقم البوت الذين ليسوا مشرفين تيليجرام
    for row in staff:
        uid = row["user_id"]
        if uid not in added_ids:
            added_ids.add(uid)
            try:
                member = await chat.get_member(uid)
                name = member.user.mention_html()
            except:
                name = f"<code>{uid}</code>"
            date_str = str(row.get("assigned_at", ""))[:10]
            lines.append(f"{row['role']}: {name} (منذ {date_str})")

    if len(lines) == 1:
        await update.message.reply_text("👥 لا يوجد طاقم معيّن في هذه المجموعة.")
        return

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


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
        await assign_role(update, context)
    elif cmd in ["عزل", "تنزيل"]:
        await demote(update, context)
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