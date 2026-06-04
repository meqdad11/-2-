import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import Update, ChatMember, ChatPermissions
from telegram.ext import ContextTypes

import database as db
from config import TIMEZONE
from helpers import is_admin, get_reply_user, parse_time, can_restrict

logger = logging.getLogger(__name__)

# ==================== حظر ====================

async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حظر عضو - استخدم: /ban @user سبب"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❗️ رد على العضو أو اكتب يوزره.")
        return
    
    if reply_user.id == update.effective_user.id:
        await update.message.reply_text("❌ لا يمكنك حظر نفسك.")
        return
    
    # التحقق من الصلاحيات
    if not await can_restrict(update, context, reply_user.id):
        await update.message.reply_text("❌ لا يمكنني حظر هذا العضو (صلاحياتي أقل أو هو مشرف).")
        return
    
    # تحليل الوقت والسبب
    args = context.args
    duration = None
    reason = "بدون سبب"
    
    if args:
        # محاولة استخراج الوقت (مثل 1d, 2h, 30m)
        for i, arg in enumerate(args):
            if parse_time(arg):
                duration = parse_time(arg)
                # باقي الكلام هو السبب
                if len(args) > i + 1:
                    reason = " ".join(args[i+1:])
                break
        else:
            reason = " ".join(args)
    
    try:
        if duration:
            expires_at = datetime.now(TIMEZONE) + timedelta(seconds=duration)
            await update.message.chat.ban_member(reply_user.id, until_date=expires_at)
            await db.add_ban(reply_user.id, update.effective_chat.id, reason, update.effective_user.id, expires_at)
            
            # تسجيل في سجل العضو
            await db.log_user_action(
                user_id=reply_user.id,
                chat_id=update.effective_chat.id,
                action_type="ban",
                action_by=update.effective_user.id,
                reason=reason,
                duration=expires_at.isoformat()
            )
            
            await update.message.reply_text(
                f"✅ تم حظر {reply_user.first_name} لمدة {duration//60} دقيقة.\n"
                f"📝 السبب: {reason}"
            )
        else:
            await update.message.chat.ban_member(reply_user.id)
            await db.add_ban(reply_user.id, update.effective_chat.id, reason, update.effective_user.id)
            
            await db.log_user_action(
                user_id=reply_user.id,
                chat_id=update.effective_chat.id,
                action_type="ban",
                action_by=update.effective_user.id,
                reason=reason
            )
            
            await update.message.reply_text(
                f"✅ تم حظر {reply_user.first_name} بشكل دائم.\n"
                f"📝 السبب: {reason}"
            )
    except Exception as e:
        logger.error(f"خطأ في الحظر: {e}")
        await update.message.reply_text("❌ فشل الحظر.")


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفع الحظر عن عضو"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❗️ رد على العضو أو اكتب يوزره.")
        return
    
    try:
        await update.message.chat.unban_member(reply_user.id)
        await db.remove_ban(reply_user.id, update.effective_chat.id, update.effective_user.id)
        
        await db.log_user_action(
            user_id=reply_user.id,
            chat_id=update.effective_chat.id,
            action_type="unban",
            action_by=update.effective_user.id,
            reason="رفع الحظر"
        )
        
        await update.message.reply_text(f"✅ تم رفع الحظر عن {reply_user.first_name}.")
    except Exception as e:
        logger.error(f"خطأ في رفع الحظر: {e}")
        await update.message.reply_text("❌ فشل رفع الحظر.")


async def cmd_banlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة المحظورين"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    bans = await db.get_ban_list(update.effective_chat.id)
    if not bans:
        await update.message.reply_text("📭 لا يوجد محظورون.")
        return
    
    text = "🚫 **قائمة المحظورين:**\n\n"
    for ban in bans[:20]:
        user_id = ban["user_id"]
        reason = ban.get("reason", "بدون سبب")
        expires = ban.get("expires_at")
        if expires:
            text += f"• {user_id}: {reason}\n  (ينتهي: {expires[:16]})\n"
        else:
            text += f"• {user_id}: {reason}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_baninfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معلومات حظر عضو"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❗️ رد على العضو.")
        return
    
    ban = await db.get_ban(reply_user.id, update.effective_chat.id)
    if not ban:
        await update.message.reply_text(f"✅ {reply_user.first_name} غير محظور.")
        return
    
    reason = ban.get("reason", "بدون سبب")
    expires = ban.get("expires_at")
    if expires:
        await update.message.reply_text(
            f"🚫 **{reply_user.first_name} محظور**\n"
            f"📝 السبب: {reason}\n"
            f"⏳ ينتهي: {expires[:16]}"
        )
    else:
        await update.message.reply_text(
            f"🚫 **{reply_user.first_name} محظور**\n"
            f"📝 السبب: {reason}\n"
            f"⏳ دائم"
        )


async def cmd_checkban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق من حظر عضو (اختصار baninfo)"""
    await cmd_baninfo(update, context)


# ==================== تحذيرات ====================

async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحذير عضو - 3 تحذيرات = حظر"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❗️ رد على العضو.")
        return
    
    reason = " ".join(context.args) if context.args else "بدون سبب"
    
    warnings = await db.add_warning(reply_user.id, update.effective_chat.id)
    
    await db.log_user_action(
        user_id=reply_user.id,
        chat_id=update.effective_chat.id,
        action_type="warn",
        action_by=update.effective_user.id,
        reason=reason
    )
    
    if warnings >= 3:
        try:
            await update.message.chat.ban_member(reply_user.id)
            await db.add_ban(reply_user.id, update.effective_chat.id, f"3 تحذيرات: {reason}", update.effective_user.id)
            await update.message.reply_text(
                f"⚠️ {reply_user.first_name} حصل على {warnings} تحذيرات.\n"
                f"🚫 تم حظره تلقائياً.\n"
                f"📝 السبب: {reason}"
            )
        except Exception as e:
            logger.error(f"خطأ في الحظر التلقائي: {e}")
    else:
        await update.message.reply_text(
            f"⚠️ تم تحذير {reply_user.first_name}.\n"
            f"📊 عدد التحذيرات: {warnings}/3\n"
            f"📝 السبب: {reason}"
        )


async def cmd_clearwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مسح تحذيرات عضو"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❗️ رد على العضو.")
        return
    
    await db.clear_warnings(reply_user.id, update.effective_chat.id)
    
    await db.log_user_action(
        user_id=reply_user.id,
        chat_id=update.effective_chat.id,
        action_type="clear_warns",
        action_by=update.effective_user.id,
        reason="مسح التحذيرات"
    )
    
    await update.message.reply_text(f"✅ تم مسح تحذيرات {reply_user.first_name}.")


async def cmd_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض عدد تحذيرات عضو"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❗️ رد على العضو.")
        return
    
    warnings = await db.get_warnings(reply_user.id, update.effective_chat.id)
    await update.message.reply_text(f"⚠️ {reply_user.first_name} لديه {warnings}/3 تحذيرات.")


# ==================== كتم ====================

async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """كتم عضو"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❗️ رد على العضو.")
        return
    
    duration = None
    reason = "بدون سبب"
    
    if context.args:
        for i, arg in enumerate(context.args):
            if parse_time(arg):
                duration = parse_time(arg)
                if len(context.args) > i + 1:
                    reason = " ".join(context.args[i+1:])
                break
        else:
            reason = " ".join(context.args)
    
    permissions = ChatPermissions(can_send_messages=False)
    
    try:
        if duration:
            until_date = datetime.now(TIMEZONE) + timedelta(seconds=duration)
            await update.message.chat.restrict_member(reply_user.id, permissions, until_date=until_date)
            
            await db.log_user_action(
                user_id=reply_user.id,
                chat_id=update.effective_chat.id,
                action_type="mute",
                action_by=update.effective_user.id,
                reason=reason,
                duration=until_date.isoformat()
            )
            
            await update.message.reply_text(
                f"🔇 تم كتم {reply_user.first_name} لمدة {duration//60} دقيقة.\n"
                f"📝 السبب: {reason}"
            )
        else:
            await update.message.chat.restrict_member(reply_user.id, permissions)
            
            await db.log_user_action(
                user_id=reply_user.id,
                chat_id=update.effective_chat.id,
                action_type="mute",
                action_by=update.effective_user.id,
                reason=reason
            )
            
            await update.message.reply_text(
                f"🔇 تم كتم {reply_user.first_name} بشكل دائم.\n"
                f"📝 السبب: {reason}"
            )
    except Exception as e:
        logger.error(f"خطأ في الكتم: {e}")
        await update.message.reply_text("❌ فشل الكتم.")


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفع الكتم عن عضو"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❗️ رد على العضو.")
        return
    
    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True
    )
    
    try:
        await update.message.chat.restrict_member(reply_user.id, permissions)
        
        await db.log_user_action(
            user_id=reply_user.id,
            chat_id=update.effective_chat.id,
            action_type="unmute",
            action_by=update.effective_user.id,
            reason="رفع الكتم"
        )
        
        await update.message.reply_text(f"✅ تم رفع الكتم عن {reply_user.first_name}.")
    except Exception as e:
        logger.error(f"خطأ في رفع الكتم: {e}")
        await update.message.reply_text("❌ فشل رفع الكتم.")


# ==================== قفل المجموعة ====================

async def cmd_lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قفل المجموعة (منع الجميع من الكتابة)"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    permissions = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False
    )
    
    try:
        await update.message.chat.set_permissions(permissions)
        await db.set_lock(update.effective_chat.id, "all", True)
        await update.message.reply_text("🔒 تم قفل المجموعة. الأعضاء لا يستطيعون الكتابة.")
    except Exception as e:
        logger.error(f"خطأ في قفل المجموعة: {e}")
        await update.message.reply_text("❌ فشل قفل المجموعة.")


async def cmd_unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فتح المجموعة"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True
    )
    
    try:
        await update.message.chat.set_permissions(permissions)
        await db.set_lock(update.effective_chat.id, "all", False)
        await update.message.reply_text("🔓 تم فتح المجموعة. الأعضاء يستطيعون الكتابة.")
    except Exception as e:
        logger.error(f"خطأ في فتح المجموعة: {e}")
        await update.message.reply_text("❌ فشل فتح المجموعة.")


# ==================== سجل الأحداث ====================

async def cmd_eventlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض آخر الأحداث"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    logs = await db.get_event_log(update.effective_chat.id, 15)
    if not logs:
        await update.message.reply_text("📭 لا توجد أحداث.")
        return
    
    text = "📋 **آخر الأحداث:**\n\n"
    for log in logs:
        action = log.get("action", "غير معروف")
        time = log.get("created_at", "")[:16]
        user_id = log.get("user_id", 0)
        detail = log.get("detail", "")
        text += f"• {time} | {action} | {user_id}\n"
        if detail:
            text += f"  {detail[:50]}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


# ==================== القواعد ====================

async def cmd_setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعيين قواعد المجموعة"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    if not context.args:
        await update.message.reply_text("📝 استخدم: /setrules النص")
        return
    
    rules = " ".join(context.args)
    await db.set_setting(update.effective_chat.id, "rules", rules)
    await update.message.reply_text("✅ تم تعيين القواعد.")


# ==================== تقرير عن عضو ====================

async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال تقرير عن عضو للمشرفين"""
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❗️ رد على العضو الذي تريد الإبلاغ عنه.")
        return
    
    reason = " ".join(context.args) if context.args else "بدون سبب محدد"
    
    # تسجيل التقرير في قاعدة البيانات
    await db.log_user_action(
        user_id=reply_user.id,
        chat_id=update.effective_chat.id,
        action_type="report",
        action_by=update.effective_user.id,
        reason=reason
    )
    
    # إرسال إشعار للمشرفين
    admins = await update.message.chat.get_administrators()
    for admin in admins:
        try:
            await context.bot.send_message(
                chat_id=admin.user.id,
                text=f"📢 **تقرير جديد**\n\n"
                     f"👤 العضو: {reply_user.first_name} (`{reply_user.id}`)\n"
                     f"📝 السبب: {reason}\n"
                     f"👮 أرسله: {update.effective_user.first_name}\n"
                     f"📍 المجموعة: {update.effective_chat.title}",
                parse_mode="Markdown"
            )
        except:
            pass
    
    await update.message.reply_text("✅ تم إرسال التقرير للمشرفين.")


# ==================== ملف العضو (سجل كامل) ====================

async def cmd_userfile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض ملف كامل عن العضو (تحذيرات، حظر، كتم، تقارير)"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❗️ رد على العضو لعرض ملفه.")
        return
    
    user_id = reply_user.id
    chat_id = update.effective_chat.id
    
    # جلب جميع الإجراءات من قاعدة البيانات
    actions = await db.get_user_actions(user_id, chat_id)
    
    if not actions:
        await update.message.reply_text(f"📋 **ملف {reply_user.first_name}**\n\nلا توجد إجراءات مسجلة ضد هذا العضو.", parse_mode="Markdown")
        return
    
    # تصنيف الإجراءات
    warns = []
    bans = []
    mutes = []
    reports = []
    others = []
    
    for action in actions:
        action_type = action.get("action_type", "")
        if action_type == "warn":
            warns.append(action)
        elif action_type == "ban":
            bans.append(action)
        elif action_type == "mute":
            mutes.append(action)
        elif action_type == "report":
            reports.append(action)
        else:
            others.append(action)
    
    # بناء الرسالة
    text = f"📋 **ملف العضو: {reply_user.first_name}**\n"
    text += f"🆔 المعرف: `{user_id}`\n"
    if reply_user.username:
        text += f"📱 اليوزر: @{reply_user.username}\n"
    text += f"━━━━━━━━━━━━━━━━━━\n\n"
    
    # التحذيرات
    if warns:
        text += f"⚠️ **التحذيرات ({len(warns)}):**\n"
        for w in warns[-5:]:  # آخر 5 تحذيرات
            time = w.get("created_at", "")[:16]
            reason = w.get("reason", "بدون سبب")
            by = w.get("action_by", 0)
            text += f"   • {time}: {reason} (بواسطة {by})\n"
        text += "\n"
    else:
        text += f"⚠️ **التحذيرات:** 0\n\n"
    
    # الحظر
    if bans:
        text += f"🚫 **الحظر ({len(bans)}):**\n"
        for b in bans[-3:]:
            time = b.get("created_at", "")[:16]
            reason = b.get("reason", "بدون سبب")
            by = b.get("action_by", 0)
            duration = b.get("duration", "")
            if duration:
                text += f"   • {time}: {reason} (بواسطة {by}, حتى {duration[:16]})\n"
            else:
                text += f"   • {time}: {reason} (بواسطة {by}, دائم)\n"
        text += "\n"
    
    # الكتم
    if mutes:
        text += f"🔇 **الكتم ({len(mutes)}):**\n"
        for m in mutes[-3:]:
            time = m.get("created_at", "")[:16]
            reason = m.get("reason", "بدون سبب")
            by = m.get("action_by", 0)
            duration = m.get("duration", "")
            if duration:
                text += f"   • {time}: {reason} (بواسطة {by}, حتى {duration[:16]})\n"
            else:
                text += f"   • {time}: {reason} (بواسطة {by}, دائم)\n"
        text += "\n"
    
    # التقارير ضده
    if reports:
        text += f"📝 **التقارير ضده ({len(reports)}):**\n"
        for r in reports[-5:]:
            time = r.get("created_at", "")[:16]
            reason = r.get("reason", "بدون سبب")
            by = r.get("action_by", 0)
            text += f"   • {time}: {reason} (بواسطة {by})\n"
        text += "\n"
    
    # الحالة النهائية
    current_ban = await db.get_ban(user_id, chat_id)
    current_warns = await db.get_warnings(user_id, chat_id)
    
    text += f"━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 **الملخص:**\n"
    text += f"   • التحذيرات الحالية: {current_warns}/3\n"
    if current_ban:
        text += f"   • الحالي: محظور 🚫\n"
    else:
        text += f"   • الحالي: غير محظور ✅\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


# ==================== تثبيت الرسائل ====================

async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تثبيت رسالة (للمشرفين فقط)"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❗️ رد على الرسالة التي تريد تثبيتها.")
        return
    
    try:
        await update.message.reply_to_message.pin()
        await update.message.reply_text("📌 تم تثبيت الرسالة.")
    except Exception as e:
        logger.error(f"خطأ في التثبيت: {e}")
        await update.message.reply_text("❌ فشل تثبيت الرسالة.")


async def cmd_unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء تثبيت الرسالة (للمشرفين فقط)"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    try:
        await update.message.chat.unpin_message()
        await update.message.reply_text("📌 تم إلغاء تثبيت الرسالة.")
    except Exception as e:
        logger.error(f"خطأ في إلغاء التثبيت: {e}")
        await update.message.reply_text("❌ فشل إلغاء التثبيت.")


# ==================== تنبيه عضو ====================

async def cmd_warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال تنبيه لعضو عبر الخاص (للمشرفين)"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❗️ رد على العضو.")
        return
    
    reason = " ".join(context.args) if context.args else "بدون سبب محدد"
    
    try:
        await context.bot.send_message(
            chat_id=reply_user.id,
            text=f"⚠️ **تنبيه من مشرف**\n\n"
                 f"📍 المجموعة: {update.effective_chat.title}\n"
                 f"📝 السبب: {reason}\n\n"
                 f"يرجى الالتزام بقواعد المجموعة."
        )
        await update.message.reply_text(f"✅ تم إرسال التنبيه إلى {reply_user.first_name}.")
    except Exception as e:
        logger.error(f"خطأ في إرسال التنبيه: {e}")
        await update.message.reply_text("❌ لا يمكن إرسال تنبيه لهذا العضو (قد يكون حظر البوت).")


# ==================== إدارة المشرفين ====================

async def cmd_promote_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفع عضو إلى مشرف (يتطلب أن يكون البوت مشرفاً)"""
    if update.effective_user.id not in [5462027396]:  # ID المطور
        await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return
    
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❗️ رد على العضو.")
        return
    
    try:
        await update.message.chat.promote_member(
            reply_user.id,
            can_change_info=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_manage_topics=True
        )
        await update.message.reply_text(f"✅ تم رفع {reply_user.first_name} إلى مشرف.")
    except Exception as e:
        logger.error(f"خطأ في رفع مشرف: {e}")
        await update.message.reply_text("❌ فشل الرفع.")


async def cmd_demote_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنزيل مشرف"""
    if update.effective_user.id not in [5462027396]:
        await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return
    
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❗️ رد على العضو.")
        return
    
    try:
        await update.message.chat.promote_member(
            reply_user.id,
            can_change_info=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_topics=False
        )
        await update.message.reply_text(f"✅ تم تنزيل {reply_user.first_name} من المشرفين.")
    except Exception as e:
        logger.error(f"خطأ في تنزيل مشرف: {e}")
        await update.message.reply_text("❌ فشل التنزيل.")


async def cmd_list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة المشرفين"""
    try:
        admins = await update.message.chat.get_administrators()
        text = "👮 **قائمة المشرفين:**\n\n"
        for admin in admins:
            user = admin.user
            role = "المطور" if user.id == 5462027396 else "مشرف"
            text += f"• {user.first_name} (@{user.username}) - {role}\n"
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"خطأ في عرض المشرفين: {e}")
        await update.message.reply_text("❌ فشل جلب القائمة.")


async def cmd_demote_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنزيل جميع المشرفين (للمطور فقط)"""
    if update.effective_user.id not in [5462027396]:
        await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return
    
    context.user_data['awaiting_demote_all'] = update.effective_chat.id
    await update.message.reply_text(
        "⚠️ **تحذير!** هذا الأمر سينزل جميع المشرفين ما عدا المطور.\n"
        "اكتب `تأكيد` خلال 30 ثانية للمتابعة.",
        parse_mode="Markdown"
    )


async def confirm_demote_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأكيد تنزيل جميع المشرفين"""
    if context.user_data.get('awaiting_demote_all') != update.effective_chat.id:
        return
    
    context.user_data.pop('awaiting_demote_all', None)
    
    try:
        admins = await update.message.chat.get_administrators()
        count = 0
        for admin in admins:
            user = admin.user
            if user.id != 5462027396 and not user.is_bot:
                try:
                    await update.message.chat.promote_member(
                        user.id,
                        can_change_info=False,
                        can_delete_messages=False,
                        can_restrict_members=False,
                        can_invite_users=False,
                        can_pin_messages=False,
                        can_manage_topics=False
                    )
                    count += 1
                except:
                    pass
        
        await update.message.reply_text(f"✅ تم تنزيل {count} مشرف.")
    except Exception as e:
        logger.error(f"خطأ في تنزيل الكل: {e}")
        await update.message.reply_text("❌ فشل التنزيل.")


async def cmd_purge_bans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مسح جميع الحظر (للمطور)"""
    if update.effective_user.id not in [5462027396]:
        await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return
    
    try:
        await db.clear_all_bans(update.effective_chat.id)
        await update.message.reply_text("✅ تم مسح جميع الحظر.")
    except Exception as e:
        logger.error(f"خطأ في مسح الحظر: {e}")
        await update.message.reply_text("❌ فشل المسح.")


async def cmd_purge_muted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مسح جميع المكتومين (للمطور)"""
    if update.effective_user.id not in [5462027396]:
        await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return
    
    try:
        await db.clear_all_mutes(update.effective_chat.id)
        await update.message.reply_text("✅ تم مسح جميع المكتومين.")
    except Exception as e:
        logger.error(f"خطأ في مسح المكتومين: {e}")
        await update.message.reply_text("❌ فشل المسح.")


async def cmd_tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منشن جميع الأعضاء (للمشرفين)"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    reason = " ".join(context.args) if context.args else "تنبيه"
    
    # جلب آخر 50 عضو نشط
    members = await db.get_top_members(update.effective_chat.id, 50)
    if not members:
        await update.message.reply_text("❌ لا يوجد أعضاء نشطين.")
        return
    
    mentions = []
    for member in members:
        user_id = member.get("user_id")
        if user_id:
            mentions.append(f"[{member.get('full_name', user_id)}](tg://user?id={user_id})")
    
    if not mentions:
        await update.message.reply_text("❌ لا يمكن منشن الأعضاء.")
        return
    
    # تقسيم إلى مجموعات
    chunk_size = 20
    for i in range(0, len(mentions), chunk_size):
        chunk = mentions[i:i+chunk_size]
        text = f"🔔 {reason}\n\n" + " ".join(chunk)
        await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_my_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رتبتي"""
    user = update.effective_user
    
    if user.id == 5462027396:
        rank = "👑 المطور الأساسي"
    elif await is_admin(update, context):
        rank = "👮 مشرف"
    else:
        rank = "👤 عضو"
    
    await update.message.reply_text(f"📊 **رتبتك:** {rank}", parse_mode="Markdown")


async def cmd_his_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رتبة عضو آخر"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    
    reply_user = get_reply_user(update)
    if not reply_user:
        await update.message.reply_text("❗️ رد على العضو.")
        return
    
    if reply_user.id == 5462027396:
        rank = "👑 المطور الأساسي"
    elif reply_user.id == update.effective_user.id:
        rank = "أنت"
    else:
        try:
            member = await update.message.chat.get_member(reply_user.id)
            if member.status in ["administrator", "creator"]:
                rank = "👮 مشرف"
            else:
                rank = "👤 عضو"
        except:
            rank = "👤 عضو"
    
    await update.message.reply_text(f"📊 **رتبة {reply_user.first_name}:** {rank}", parse_mode="Markdown")