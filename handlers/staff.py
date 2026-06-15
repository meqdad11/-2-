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

async def _get_target_id(update: Update, context, identifier: str = None):
    """ترجع user_id للعضو المستهدف، أو None."""
    msg = update.message
    chat = update.effective_chat

    # الرد على رسالة
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target = msg.reply_to_message.from_user
        try:
            await chat.get_member(target.id)
            return target.id
        except:
            return None

    # لو تم تمرير معرف
    if identifier:
        identifier = identifier.lstrip("@")
        if identifier.isdigit():
            try:
                await chat.get_member(int(identifier))
                return int(identifier)
            except:
                pass
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
        return await update.message.reply_text("❌ للمجموعات فقط.")
    admin_rank = await get_rank(user.id, chat.id)
    if admin_rank < 4:
        return await update.message.reply_text("❌ محصور في المدير والمطور.")
    args = context.args
    target_id = None
    role_name = None
    if update.message.reply_to_message:
        target_id = await _get_target_id(update, context)
        role_name = " ".join(args) if args else None
        if not role_name:
            return await update.message.reply_text("❌ اكتب الرتبة بعد الأمر، مثال: ترقية مساعد")
    else:
        if len(args) < 2:
            return await update.message.reply_text("❌ استخدم: ترقية @المعرف الرتبة")
        target_id = await _get_target_id(update, context, args[0])
        role_name = " ".join(args[1:])
    if not target_id:
        return await update.message.reply_text("❌ العضو غير موجود.")
    if role_name not in STAFF_ROLES:
        return await update.message.reply_text("❌ رتبة غير معروفة.")
    target_rank_value = STAFF_ROLES[role_name]
    if admin_rank == 4 and target_rank_value >= 4:
        return await update.message.reply_text("❌ المدير لا يعيّن مدير.")
    if admin_rank != 5 and target_rank_value >= admin_rank:
        return await update.message.reply_text("❌ لا تعلو على رتبتك.")
    if await get_rank(target_id, chat.id) >= admin_rank:
        return await update.message.reply_text("❌ رتبته الحالية تمنع ذلك.")
    await set_staff_role(target_id, chat.id, role_name, user.id)
    await log_staff_action(chat.id, user.id, target_id, "تعيين", role_name)
    try:
        member = await chat.get_member(target_id)
        mention = member.user.mention_html()
    except:
        mention = f"<code>{target_id}</code>"
    await update.message.reply_text(
        f"✅ {mention} ← {role_name}\nبواسطة {user.mention_html()}", parse_mode="HTML")

async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if not chat or chat.type == "private":
        return await update.message.reply_text("❌ للمجموعات فقط.")
    admin_rank = await get_rank(user.id, chat.id)
    if admin_rank < 4:
        return await update.message.reply_text("❌ محصور في المدير والمطور.")
    args = context.args
    target_id = None
    if update.message.reply_to_message:
        target_id = await _get_target_id(update, context)
    elif args:
        target_id = await _get_target_id(update, context, args[0])
    else:
        return await update.message.reply_text("❌ استخدم: عزل @المعرف")
    if not target_id:
        return await update.message.reply_text("❌ العضو غير موجود.")
    target_rank = await get_rank(target_id, chat.id)
    if target_rank == 0:
        return await update.message.reply_text("❌ ليس لديه رتبة.")
    if target_rank >= admin_rank:
        return await update.message.reply_text("❌ لا يمكنك عزله.")
    old_role = await get_staff_role(target_id, chat.id)
    await remove_staff_role(target_id, chat.id)
    await log_staff_action(chat.id, user.id, target_id, "عزل", old_role)
    try:
        member = await chat.get_member(target_id)
        mention = member.user.mention_html()
    except:
        mention = f"<code>{target_id}</code>"
    await update.message.reply_text(
        f"✅ {mention} عُزل من {old_role}\nبواسطة {user.mention_html()}", parse_mode="HTML")

async def list_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("❌ هذا الأمر للمجموعات فقط.")
        return

    staff = await get_group_staff(chat.id)
    staff_dict = {row["user_id"]: row for row in staff}

    lines = ["👥 **طاقم المجموعة:**\n"]
    added_ids = set()

    # مشرفو تيليجرام أولاً
    try:
        admins = await chat.get_administrators()
        for admin in admins:
            uid = admin.user.id
            if uid == context.bot.id:
                continue
            added_ids.add(uid)
            mention = admin.user.mention_html()
            if admin.status == "creator":
                role_text = "👑 المالك"
            else:
                role_text = "👮 مشرف"
            # رتبة البوت إن وجدت
            if uid in staff_dict:
                bot_role = staff_dict[uid]["role"]
                role_text += f" • {bot_role}"
                date_str = str(staff_dict[uid].get("assigned_at", ""))[:10]
                lines.append(f"{role_text}: {mention} (منذ {date_str})")
            else:
                lines.append(f"{role_text}: {mention}")
    except Exception:
        pass

    # أعضاء لديهم رتب بوت فقط
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

async def my_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("المجموعات فقط.")
        return
    rank = await get_rank(user.id, chat.id)
    role_name = ROLE_NAMES.get(rank, "عضو")
    if rank == 5:
        role_name = "مطور البوت"
    await update.message.reply_text(f"🌟 رتبتك: {role_name}")

async def my_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("المجموعات فقط.")
        return
    rank = await get_rank(user.id, chat.id)
    role_name = ROLE_NAMES.get(rank, "عضو")
    if rank == 5:
        role_name = "مطور"
    permissions = {
        1: "🗑 حذف · ⚠️ تحذير",
        2: "🗑 حذف · ⚠️ تحذير · 🔇 كتم ورفعه",
        3: "🔓 كل الصلاحيات (عقوبات + إدارة المجموعة)",
        4: "👑 تعيين/عزل + صلاحيات مشرف أول",
        5: "⚜️ تحكم كامل"
    }
    msg = f"📋 صلاحيات {role_name}:\n{permissions.get(rank, '—')}"
    await update.message.reply_text(msg)

async def staff_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    cmd = text.split()[0]

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