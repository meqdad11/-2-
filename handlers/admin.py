import logging
import asyncio
from datetime import datetime, timedelta, timezone

from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes

from utils import database as db
from config import MAX_WARNINGS
from utils.helpers import (
    is_admin, require_admin, get_reply_user,
    can_restrict, parse_ban_args, fmt_user, fmt_duration
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
    if not await require_admin(update, context):
        return
    reply_user = get_reply_user(update)
    target_id = None
    if reply_user:
        target_id = reply_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ معرف المستخدم غير صالح.")
            return
    if not target_id:
        await update.message.reply_text("❌ استخدم: رفع الحظر <معرف>")
        return

    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target_id)
        await db.remove_ban(target_id, update.effective_chat.id, update.effective_user.id)
        await update.message.reply_text(f"✅ تم رفع الحظر عن {target_id}")
    except Exception as e:
        logger.error(f"فشل رفع الحظر: {e}")
        await update.message.reply_text("❌ لا يمكن رفع الحظر.")


# ==================== الكتم ====================
async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    reply_user = get_reply_user(update)
    target_id = None
    if reply_user:
        target_id = reply_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ معرف غير صالح.")
            return
    if not target_id:
        await update.message.reply_text("❌ استخدم: كتم <معرف> [مدة]")
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
        target_name = fmt_user(reply_user) if reply_user else str(target_id)
        duration_str = fmt_duration(duration)
        await update.message.reply_text(f"🔇 تم كتم {target_name} - {duration_str}")
    except Exception as e:
        logger.error(f"فشل الكتم: {e}")
        await update.message.reply_text("❌ فشل الكتم.")


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    reply_user = get_reply_user(update)
    target_id = None
    if reply_user:
        target_id = reply_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ معرف غير صالح.")
            return
    if not target_id:
        await update.message.reply_text("❌ استخدم: رفع الكتم <معرف>")
        return

    try:
        perms = ChatPermissions(
            can_send_messages=True, can_send_polls=True,
            can_send_other_messages=True, can_add_web_page_previews=True
        )
        await context.bot.restrict_chat_member(update.effective_chat.id, target_id, perms)
        await db.log_event(update.effective_chat.id, "unmute", user_id=update.effective_user.id, target_id=target_id)
        target_name = fmt_user(reply_user) if reply_user else str(target_id)
        await update.message.reply_text(f"🔊 تم رفع الكتم عن {target_name}")
    except Exception as e:
        logger.error(f"فشل رفع الكتم: {e}")
        await update.message.reply_text("❌ فشل رفع الكتم.")


# ==================== التحذيرات ====================
async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❌ استخدم الأمر بالرد على العضو.")
        return

    if await is_admin(update, context, reply_user.id):
        await update.message.reply_text("❌ لا يمكن تحذير مشرف.")
        return

    count = await db.add_warning(reply_user.id, update.effective_chat.id)
    await update.message.reply_text(
        f"⚠️ {fmt_user(reply_user)} تلقى تحذيراً ({count}/{MAX_WARNINGS})"
    )

    if count >= MAX_WARNINGS:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, reply_user.id)
            await db.add_ban(reply_user.id, update.effective_chat.id, f"حظر تلقائي بعد {MAX_WARNINGS} تحذيرات", 0)
            await db.clear_warnings(reply_user.id, update.effective_chat.id)
            await update.message.reply_text(f"🚫 تم حظر {fmt_user(reply_user)} تلقائياً.")
        except Exception as e:
            logger.error(f"فشل الحظر التلقائي: {e}")


async def cmd_clearwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❌ استخدم الأمر بالرد على العضو.")
        return
    await db.clear_warnings(reply_user.id, update.effective_chat.id)
    await update.message.reply_text(f"✅ تم مسح تحذيرات {fmt_user(reply_user)}")


async def cmd_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❌ استخدم الأمر بالرد على العضو.")
        return
    count = await db.get_warnings(reply_user.id, update.effective_chat.id)
    await update.message.reply_text(f"📊 {fmt_user(reply_user)} لديه {count}/{MAX_WARNINGS} تحذيرات.")


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
    reply_user = get_reply_user(update)
    target_id = None
    if reply_user:
        target_id = reply_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ معرف غير صالح.")
            return
    if not target_id:
        await update.message.reply_text("❌ استخدم: معلومات <معرف>")
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
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❌ استخدم الأمر بالرد على العضو.")
        return
    ban = await db.get_ban(reply_user.id, update.effective_chat.id)
    if ban:
        await update.message.reply_text(f"🚫 {fmt_user(reply_user)} محظور.")
    else:
        await update.message.reply_text(f"✅ {fmt_user(reply_user)} غير محظور.")


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
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text("❌ استخدم: تعيين القوانين <القوانين>")
        return
    await db.set_setting(update.effective_chat.id, "rules", text)
    await update.message.reply_text("✅ تم تعيين القوانين.")


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


# ==================== رفع/تنزيل مشرف ====================
async def cmd_promote_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❌ استخدم الأمر بالرد على العضو.")
        return
    try:
        await update.message.chat.promote_member(
            reply_user.id,
            can_change_info=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_invite_users=True,
            can_pin_messages=True,
        )
        await update.message.reply_text(f"✅ تم رفع {fmt_user(reply_user)} مشرفاً.")
    except Exception as e:
        logger.error(f"فشل الرفع: {e}")
        await update.message.reply_text("❌ تعذر الرفع.")


async def cmd_demote_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❌ استخدم الأمر بالرد على العضو.")
        return
    try:
        await update.message.chat.demote_member(reply_user.id)
        await update.message.reply_text(f"⬇️ تم تنزيل {fmt_user(reply_user)}.")
    except Exception as e:
        logger.error(f"فشل التنزيل: {e}")
        await update.message.reply_text("❌ تعذر التنزيل.")


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
                    await update.message.chat.demote_member(admin.user.id)
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
async def cmd_my_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await update.message.chat.get_member(update.effective_user.id)
        status_map = {
            'creator': '👑 المالك',
            'administrator': '👮 مشرف',
            'member': '👤 عضو',
            'restricted': '🔇 مكتوم',
            'left': '🚪 غادر',
            'kicked': '🚫 محظور',
        }
        rank = status_map.get(member.status, member.status)
        await update.message.reply_text(f"🏅 رتبتك: {rank}")
    except:
        await update.message.reply_text("❌ لا يمكن تحديد الرتبة.")


async def cmd_his_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❌ استخدم الأمر بالرد على العضو.")
        return
    try:
        member = await update.message.chat.get_member(reply_user.id)
        status_map = {
            'creator': '👑 المالك',
            'administrator': '👮 مشرف',
            'member': '👤 عضو',
            'restricted': '🔇 مكتوم',
            'left': '🚪 غادر',
            'kicked': '🚫 محظور',
        }
        rank = status_map.get(member.status, member.status)
        await update.message.reply_text(f"🏅 رتبة {fmt_user(reply_user)}: {rank}")
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
    """عرض ملف شامل للعضو (للمشرفين فقط لعرض الآخرين)"""
    msg = update.message
    chat = update.effective_chat
    user = update.effective_user

    # تحديد الهدف: إذا كان هناك رد على شخص فالمشرف يرى ملفه، وإلا ملف نفسه
    target = user
    if msg.reply_to_message:
        if await is_admin(update, context):
            target = msg.reply_to_message.from_user
        else:
            await msg.reply_text("⛔ فقط المشرفون يمكنهم عرض ملف عضو آخر.")
            return

    # جمع المعلومات من قاعدة البيانات
    warnings = await db.get_warnings(target.id, chat.id)
    ban_info = await db.get_ban(target.id, chat.id)
    msg_count = await db.get_message_count(target.id, chat.id)
    first_seen = await db.get_user_first_seen(target.id, chat.id)
    
    # الحالة الحالية
    is_banned = "✅ محظور" if ban_info else "❌ غير محظور"
    is_muted = "❓ غير معروف"
    try:
        member = await context.bot.get_chat_member(chat.id, target.id)
        if member.status == 'restricted' and not member.can_send_messages:
            is_muted = "✅ مكتوم"
        else:
            is_muted = "❌ غير مكتوم"
    except:
        pass

    # بناء الرسالة
    username = f"@{target.username}" if target.username else "لا يوجد"
    text = (
        f"📁 **ملف العضو**\n\n"
        f"👤 الاسم: {target.full_name or target.first_name}\n"
        f"🆔 المعرف: `{target.id}`\n"
        f"📎 اليوزر: {username}\n"
        f"📅 أول ظهور: {first_seen or 'غير معروف'}\n"
        f"💬 عدد الرسائل: {msg_count}\n"
        f"⚠️ التحذيرات: {warnings}/3\n"
        f"🚫 الحظر: {is_banned}\n"
        f"🔇 الكتم: {is_muted}\n"
    )
    await msg.reply_text(text, parse_mode="Markdown")