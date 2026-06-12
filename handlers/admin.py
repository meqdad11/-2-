import logging
import asyncio
from datetime import datetime, timedelta, timezone

from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes

from utils import database as db
from config import MAX_WARNINGS
from utils.helpers import (
    is_admin, require_admin, get_reply_user,
    can_restrict, parse_ban_args, fmt_user, fmt_duration,
    extract_target  # ✅ إضافة الدالة الجديدة
)

logger = logging.getLogger(__name__)

# ==================== الحظر ====================
async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    reply_user = get_reply_user(update)
    args = context.args or []
    target_id, duration, reason, err = parse_ban_args(args, reply_user)
    if err:
        await update.message.reply_text(err)
        return
    if not target_id:
        await update.message.reply_text("❌ لم يتم تحديد المستخدم.")
        return

    if not await can_restrict(update, context, target_id):
        await update.message.reply_text("❌ لا أستطيع حظر هذا المستخدم.")
        return

    try:
        expires_at = None
        if duration:
            until = datetime.now(timezone.utc) + duration
            await context.bot.ban_chat_member(update.effective_chat.id, target_id, until_date=until)
            expires_at = until
        else:
            await context.bot.ban_chat_member(update.effective_chat.id, target_id)

        await db.add_ban(target_id, update.effective_chat.id, reason, update.effective_user.id, expires_at)
        await db.log_event(update.effective_chat.id, "ban", user_id=update.effective_user.id, target_id=target_id, detail=reason)

        target_name = fmt_user(update.message.reply_to_message.from_user) if update.message.reply_to_message else str(target_id)
        duration_str = fmt_duration(duration)
        reason_str = f" - السبب: {reason}" if reason else ""
        await update.message.reply_text(
            f"🚫 تم حظر {target_name}\n⏳ المدة: {duration_str}{reason_str}"
        )
    except Exception as e:
        logger.error(f"خطأ في الحظر: {e}")
        await update.message.reply_text("❌ فشل الحظر.")


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفع الحظر عن عضو وإرسال رابط المجموعة للمشرف"""
    if not await require_admin(update, context):
        return
    target_id, target_name, _ = await extract_target(update, context)
    if not target_id:
        await update.message.reply_text("❌ حدد مستخدم: بالرد، المعرف، أو اليوزر.")
        return

    chat = update.effective_chat

    # ✅ التحقق من وجود العضو في حالة حظر
    try:
        member = await context.bot.get_chat_member(chat.id, target_id)
        if member.status in ('member', 'administrator', 'creator'):
            await update.message.reply_text("⚠️ هذا العضو ليس محظوراً، بل هو موجود في المجموعة.")
            return
    except Exception:
        pass  # العضو غير موجود أصلاً (طبيعي للمحظورين)

    # ✅ رفع الحظر
    try:
        await context.bot.unban_chat_member(chat.id, target_id)
        await db.remove_ban(target_id, chat.id, update.effective_user.id)
    except Exception as e:
        logger.error(f"فشل رفع الحظر: {e}")
        await update.message.reply_text("❌ لا يمكن رفع الحظر عن هذا المستخدم.")
        return

    # ✅ تجهيز يوزر العضو
    try:
        member = await context.bot.get_chat_member(chat.id, target_id)
        target_username = f"@{member.user.username}" if member.user.username else "بدون يوزر"
    except:
        target_username = "بدون يوزر"

    # ✅ إنشاء رابط دعوة (إن أمكن)
    invite_link = None
    try:
        link_obj = await context.bot.create_chat_invite_link(
            chat.id,
            member_limit=1,
            creates_join_request=False
        )
        invite_link = link_obj.invite_link
    except Exception:
        pass

    # ✅ إرسال رابط المجموعة للعضو تلقائياً عبر اليوزربوت
    auto_sent = False
    try:
        from telegram import Bot
        import os as _os
        bot = Bot(token=_os.environ.get("TELEGRAM_BOT_TOKEN"))
        link_to_send = invite_link if invite_link else f"https://t.me/{chat.username}" if chat.username else ""
        if link_to_send:
            cmd = f"/send_invite {target_id} {link_to_send}"
            await bot.send_message(chat_id=729970974, text=cmd)  # 729970974 = حسابك
            auto_sent = True
    except Exception as e:
        logger.error(f"فشل إرسال أمر الدعوة التلقائي: {e}")

    # ✅ إرسال رسالة إلى الشخص الذي فك الحظر
    msg_parts = [
        f"✅ **تم رفع الحظر عن:** {target_name}",
        f"👤 **اليوزر:** {target_username}",
    ]
    if invite_link:
        msg_parts.append(f"🔗 **رابط المجموعة:** {invite_link}")
    else:
        msg_parts.append("\n⚠️ تعذر إنشاء رابط. يمكنك نسخ رابط المجموعة يدوياً وإرساله له.")

    if auto_sent:
        msg_parts.append("\n📩 تم إرسال رابط المجموعة للعضو تلقائياً عبر المساعد.")
    else:
        msg_parts.append("\n⚠️ تعذر إرسال رابط المجموعة للعضو تلقائياً.")

    await update.message.reply_text("\n".join(msg_parts), parse_mode="Markdown")

# ==================== الكتم ====================
async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    target_id, target_name, _ = await extract_target(update, context)
    if not target_id:
        await update.message.reply_text("❌ حدد مستخدم: بالرد، المعرف، أو اليوزر.")
        return

    duration = None
    if context.args and len(context.args) > 1:
        from utils.helpers import parse_duration
        duration = parse_duration(context.args[1])

    if not await can_restrict(update, context, target_id):
        await update.message.reply_text("❌ لا أستطيع كتم هذا العضو.")
        return

    try:
        perms = ChatPermissions(can_send_messages=False)
        until = None
        if duration:
            until = datetime.now(timezone.utc) + duration
        await context.bot.restrict_chat_member(update.effective_chat.id, target_id, perms, until_date=until)
        await db.log_event(update.effective_chat.id, "mute", user_id=update.effective_user.id, target_id=target_id)
        duration_str = fmt_duration(duration)
        await update.message.reply_text(f"🔇 تم كتم {target_name} - {duration_str}")
    except Exception as e:
        logger.error(f"فشل الكتم: {e}")
        await update.message.reply_text("❌ فشل الكتم.")


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    target_id, target_name, _ = await extract_target(update, context)
    if not target_id:
        await update.message.reply_text("❌ حدد مستخدم: بالرد، المعرف، أو اليوزر.")
        return

    try:
        perms = ChatPermissions(
            can_send_messages=True, can_send_polls=True,
            can_send_other_messages=True, can_add_web_page_previews=True
        )
        await context.bot.restrict_chat_member(update.effective_chat.id, target_id, perms)
        await db.log_event(update.effective_chat.id, "unmute", user_id=update.effective_user.id, target_id=target_id)
        await update.message.reply_text(f"🔊 تم رفع الكتم عن {target_name}")
    except Exception as e:
        logger.error(f"فشل رفع الكتم: {e}")
        await update.message.reply_text("❌ فشل رفع الكتم.")


# ==================== التحذيرات ====================
async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    target_id, target_name, _ = await extract_target(update, context)
    if not target_id:
        await update.message.reply_text("❌ حدد مستخدم: بالرد، المعرف، أو اليوزر.")
        return

    if not await can_restrict(update, context, target_id):
        await update.message.reply_text("❌ لا يمكن تحذير مشرف أو مالك المجموعة.")
        return

    count = await db.add_warning(target_id, update.effective_chat.id)
    await update.message.reply_text(f"⚠️ {target_name} تلقى تحذيراً ({count}/{MAX_WARNINGS})")

    if count >= MAX_WARNINGS:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, target_id)
            await db.add_ban(target_id, update.effective_chat.id, f"حظر تلقائي بعد {MAX_WARNINGS} تحذيرات", 0)
            await db.clear_warnings(target_id, update.effective_chat.id)
            await update.message.reply_text(f"🚫 تم حظر {target_name} تلقائياً.")
        except Exception as e:
            logger.error(f"فشل الحظر التلقائي: {e}")

async def cmd_clearwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    target_id, target_name, _ = await extract_target(update, context)
    if not target_id:
        await update.message.reply_text("❌ حدد مستخدم: بالرد، المعرف، أو اليوزر.")
        return
    await db.clear_warnings(target_id, update.effective_chat.id)
    await update.message.reply_text(f"✅ تم مسح تحذيرات {target_name}")


async def cmd_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_id, target_name, _ = await extract_target(update, context)
    if not target_id:
        await update.message.reply_text("❌ حدد مستخدم: بالرد، المعرف، أو اليوزر.")
        return
    count = await db.get_warnings(target_id, update.effective_chat.id)
    await update.message.reply_text(f"📊 {target_name} لديه {count}/{MAX_WARNINGS} تحذيرات.")


# ==================== القوائم ====================
async def cmd_banlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    bans = await db.get_ban_list(update.effective_chat.id)
    if not bans:
        await update.message.reply_text("✅ لا يوجد محظورون.")
        return
    lines = [f"• {b['user_id']} ({b.get('reason','') or 'بدون سبب'})" for b in bans[:20]]
    await update.message.reply_text("🚫 المحظورون:\n" + "\n".join(lines))


async def cmd_baninfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    target_id, target_name, _ = await extract_target(update, context)
    if not target_id:
        await update.message.reply_text("❌ حدد مستخدم: بالرد، المعرف، أو اليوزر.")
        return

    ban = await db.get_ban(target_id, update.effective_chat.id)
    if not ban:
        await update.message.reply_text("✅ هذا المستخدم غير محظور.")
        return
    expires = ban.get("expires_at", "دائم")
    reason = ban.get("reason", "بدون سبب")
    await update.message.reply_text(
        f"🚫 معلومات الحظر:\nالمعرف: {target_id}\nالسبب: {reason}\nينتهي: {expires}"
    )


async def cmd_checkban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    target_id, target_name, _ = await extract_target(update, context)
    if not target_id:
        await update.message.reply_text("❌ حدد مستخدم: بالرد، المعرف، أو اليوزر.")
        return
    ban = await db.get_ban(target_id, update.effective_chat.id)
    if ban:
        await update.message.reply_text(f"🚫 {target_name} محظور.")
    else:
        await update.message.reply_text(f"✅ {target_name} غير محظور.")


async def cmd_eventlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    events = await db.get_event_log(update.effective_chat.id, 15)
    if not events:
        await update.message.reply_text("📭 لا توجد أحداث.")
        return
    lines = [f"• {e['action']} | {e['created_at'][:19]} | user:{e['user_id']} target:{e['target_id']}" for e in events]
    await update.message.reply_text("📋 آخر الأحداث:\n" + "\n".join(lines))


# ==================== القواعد ====================
async def cmd_setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    text = " ".join(context.args).replace(". ", ".\n") if context.args else ""
    if not text:
        await update.message.reply_text("❌ استخدم: تعيين القواعد <القوانين>")
        return
    await db.set_setting(update.effective_chat.id, "rules", text)
    await update.message.reply_text("✅ تم تعيين القواعد.")


# ==================== القفل / الفتح ====================
async def cmd_lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    try:
        await update.message.chat.set_permissions(ChatPermissions(can_send_messages=False))
        await update.message.reply_text("🔒 تم إغلاق المجموعة.")
    except Exception as e:
        logger.error(f"فشل القفل: {e}")
        await update.message.reply_text("❌ لا يمكن الإغلاق.")


async def cmd_unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    try:
        await update.message.chat.set_permissions(ChatPermissions(
            can_send_messages=True, can_send_polls=True,
            can_send_other_messages=True, can_add_web_page_previews=True
        ))
        await update.message.reply_text("🔓 تم فتح المجموعة.")
    except Exception as e:
        logger.error(f"فشل الفتح: {e}")
        await update.message.reply_text("❌ لا يمكن الفتح.")


# ==================== رفع/تنزيل مشرف (حصري للمالك والمطور) ====================
async def cmd_promote_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    try:
        member = await chat.get_member(user.id)
        is_creator = (member.status == 'creator')
        is_dev = await db.is_developer(user.id)
        if not (is_creator or is_dev):
            await update.message.reply_text("⛔ هذا الأمر حصري لمالك المجموعة أو المطور فقط.")
            return
    except:
        await update.message.reply_text("❌ لا يمكن التحقق من صلاحياتك.")
        return

    target_id, target_name, _ = await extract_target(update, context)
    if not target_id:
        await update.message.reply_text("❌ حدد مستخدم: بالرد، المعرف، أو اليوزر.")
        return
    try:
        await context.bot.promote_chat_member(
            chat.id,
            target_id,
            can_change_info=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_invite_users=True,
            can_pin_messages=True,
        )
        await update.message.reply_text(f"✅ تم رفع {target_name} مشرفاً.")
    except Exception as e:
        logger.error(f"فشل الرفع: {e}")
        await update.message.reply_text("❌ تعذر الرفع. تأكد من صلاحيات البوت.")


async def cmd_demote_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    try:
        member = await chat.get_member(user.id)
        is_creator = (member.status == 'creator')
        is_dev = await db.is_developer(user.id)
        if not (is_creator or is_dev):
            await update.message.reply_text("⛔ هذا الأمر حصري لمالك المجموعة أو المطور فقط.")
            return
    except Exception as e:
        await update.message.reply_text(f"❌ لا يمكن التحقق من صلاحياتك: {e}")
        return

    target_id, target_name, _ = await extract_target(update, context)
    if not target_id:
        await update.message.reply_text("❌ حدد مستخدم: بالرد، المعرف، أو اليوزر.")
        return

    try:
        target_member = await chat.get_member(target_id)
        if target_member.status == 'creator':
            await update.message.reply_text("❌ لا يمكن تنزيل مالك المجموعة.")
            return
        if target_member.status != 'administrator':
            await update.message.reply_text(f"⚠️ {target_name} ليس مشرفاً.")
            return
    except Exception as e:
        await update.message.reply_text(f"❌ لا يمكن العثور على العضو: {e}")
        return

    try:
        await context.bot.promote_chat_member(
            chat.id,
            target_id,
            can_change_info=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_topics=False,
            is_anonymous=False,
            can_manage_chat=False,
            can_post_messages=False,
            can_edit_messages=False,
        )
        await update.message.reply_text(f"⬇️ تم تنزيل {target_name} من المشرفين.")
    except Exception as e:
        logger.error(f"فشل التنزيل: {e}")
        error_msg = str(e).lower()
        if "not enough rights" in error_msg or "rights" in error_msg:
            await update.message.reply_text(
                "❌ **البوت لا يملك صلاحية كافية!**\n\n"
                "تأكد من أن البوت مشرف ولديه صلاحية 'إضافة مشرفين جدد'.\n"
                "اذهب إلى: إعدادات المجموعة → المشرفين → بوت شفق → الصلاحيات.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"❌ تعذر التنزيل: {e}")

async def cmd_list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    try:
        admins = await update.message.chat.get_administrators()
        lines = [f"• {a.user.first_name} {'(المالك)' if a.status=='creator' else ''}" for a in admins]
        await update.message.reply_text("👮 المشرفون:\n" + "\n".join(lines))
    except Exception as e:
        logger.error(f"فشل عرض المشرفين: {e}")
        await update.message.reply_text("❌ لا يمكن جلب القائمة.")


async def cmd_demote_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    context.user_data['awaiting_demote_all'] = update.effective_chat.id
    await update.message.reply_text(
        "⚠️ هل أنت متأكد من تنزيل جميع المشرفين؟\nاكتب 'تأكيد' للمتابعة."
    )


async def confirm_demote_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.pop('awaiting_demote_all', None) != update.effective_chat.id:
        return
    try:
        admins = await update.message.chat.get_administrators()
        count = 0
        for admin in admins:
            if admin.status == 'administrator' and not admin.user.is_bot:
                try:
                    await context.bot.promote_chat_member(
                        update.effective_chat.id,
                        admin.user.id,
                        can_change_info=False,
                        can_delete_messages=False,
                        can_restrict_members=False,
                        can_invite_users=False,
                        can_pin_messages=False,
                    )
                    count += 1
                except:
                    pass
        await update.message.reply_text(f"✅ تم تنزيل {count} مشرف.")
    except Exception as e:
        logger.error(f"فشل تنزيل الكل: {e}")
        await update.message.reply_text("❌ فشلت العملية.")


# ==================== مسح المحظورين / المكتومين ====================
async def cmd_purge_bans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    try:
        await db.clear_all_bans(update.effective_chat.id)
        await update.message.reply_text("🧹 تم مسح جميع المحظورين من القاعدة.")
    except Exception as e:
        logger.error(f"فشل مسح المحظورين: {e}")
        await update.message.reply_text("❌ فشل المسح.")


async def cmd_purge_muted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    try:
        await db.clear_all_mutes(update.effective_chat.id)
        await update.message.reply_text("🧹 تم مسح جميع المكتومين من القاعدة.")
    except Exception as e:
        logger.error(f"فشل مسح المكتومين: {e}")
        await update.message.reply_text("❌ فشل المسح.")


# ==================== تاك للكل ====================
async def cmd_tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    await update.message.reply_text("📢 تاك للكل: هذا الأمر قيد التطوير.")


# ==================== رتبتي / رتبته ====================
async def get_full_rank(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> str:
    if await db.is_developer(user_id):
        return "👨‍💻 مطور"
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        status = member.status
        if status == 'creator':
            return "👑 المالك"
        elif status == 'administrator':
            return "👮 مشرف"
        elif status == 'restricted':
            return "🔇 مكتوم"
        elif status == 'left':
            return "🚪 غادر"
        elif status == 'kicked':
            return "🚫 محظور"
        elif status == 'member':
            return "👤 عضو"
    except:
        pass
    return "❓ غير معروف"

async def cmd_my_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rank = await get_full_rank(update.effective_user.id, update.effective_chat.id, context)
        await update.message.reply_text(f"🏅 رتبتك: {rank}")
    except:
        await update.message.reply_text("❌ لا يمكن تحديد الرتبة.")


async def cmd_his_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_id, target_name, _ = await extract_target(update, context)
    if not target_id:
        await update.message.reply_text("❌ حدد مستخدم: بالرد، المعرف، أو اليوزر.")
        return
    try:
        rank = await get_full_rank(target_id, update.effective_chat.id, context)
        await update.message.reply_text(f"🏅 رتبة {target_name}: {rank}")
    except:
        await update.message.reply_text("❌ لا يمكن تحديد الرتبة.")


# ==================== تثبيت / إلغاء تثبيت ====================
async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ استخدم الأمر بالرد على رسالة.")
        return
    try:
        await update.message.reply_to_message.pin()
        await update.message.reply_text("📌 تم التثبيت.")
    except Exception as e:
        logger.error(f"فشل التثبيت: {e}")
        await update.message.reply_text("❌ لا يمكن التثبيت.")


async def cmd_unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    try:
        await update.message.chat.unpin_all_messages()
        await update.message.reply_text("📌 تم إلغاء التثبيت.")
    except Exception as e:
        logger.error(f"فشل إلغاء التثبيت: {e}")
        await update.message.reply_text("❌ لا يمكن إلغاء التثبيت.")


async def cmd_warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر تنبيه - تحذير مع سبب"""
    await cmd_warn(update, context)

# ==================== ملف العضو (أمر ملف) ====================
async def cmd_userfile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = update.effective_chat
    user = update.effective_user

    target_id, target_name, _ = await extract_target(update, context)
    if not target_id:
        await update.message.reply_text("❌ حدد مستخدم: بالرد، المعرف، أو اليوزر.")
        return

    warnings = await db.get_warnings(target_id, chat.id)
    ban_info = await db.get_ban(target_id, chat.id)
    msg_count = await db.get_message_count(target_id, chat.id)
    first_seen = await db.get_user_first_seen(target_id, chat.id)

    is_banned = "✅ محظور" if ban_info else "❌ غير محظور"
    is_muted = "❓ غير معروف"
    try:
        member = await context.bot.get_chat_member(chat.id, target_id)
        if member.status == 'restricted' and not member.can_send_messages:
            is_muted = "✅ مكتوم"
        else:
            is_muted = "❌ غير مكتوم"
    except:
        pass

    username = f"@{member.user.username}" if member.user.username else "لا يوجد"
    text = (
        f"📁 **ملف العضو**\n\n"
        f"👤 الاسم: {member.user.full_name or member.user.first_name}\n"
        f"🆔 المعرف: {target_id}\n"
        f"📎 اليوزر: {username}\n"
        f"📅 أول ظهور: {first_seen or 'غير معروف'}\n"
        f"💬 عدد الرسائل: {msg_count}\n"
        f"⚠️ التحذيرات: {warnings}/3\n"
        f"🚫 الحظر: {is_banned}\n"
        f"🔇 الكتم: {is_muted}\n"
    )

    try:
        await msg.delete()
    except:
        pass

    try:
        await context.bot.send_message(chat_id=user.id, text=text, parse_mode="Markdown")
    except Exception:
        try:
            temp = await context.bot.send_message(
                chat_id=chat.id,
                text="❌ لم أستطع إرسال الملف إلى الخاص. تأكد من فتح محادثة خاصة مع البوت.",
            )
            await asyncio.sleep(5)
            await temp.delete()
        except:
            pass

