import logging
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from config import MAX_WARNINGS, ADMIN_CHAT_ID
from helpers import (
    require_admin,
    get_reply_user,
    parse_ban_args,
    expires_at_from_duration,
    fmt_duration,
)

# ================================================

logger = logging.getLogger(__name__)
# ================================================

async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    banner_id = update.effective_user.id
    reply_user = get_reply_user(update)
    user_id, duration, reason, err = parse_ban_args(context.args or [], reply_user)
    if err:
        await update.message.reply_text(err)
        return
    expires_at = expires_at_from_duration(duration)
    await db.add_ban(user_id, chat_id, reason, banner_id, expires_at)
    until_date = expires_at if expires_at else None
    try:
        await context.bot.ban_chat_member(chat_id, user_id, until_date=until_date)
    except Exception as e:
        logger.warning("تعذّر الحظر: %s", e)
    reason_text = f"\nالسبب: {reason}" if reason else ""
    duration_text = f"\nالمدة: {fmt_duration(duration)}" if duration else "\nالمدة: دائم"
    await update.message.reply_text(f"🚫 تم حظر المستخدم {user_id}.{duration_text}{reason_text}")
    try:
        await context.bot.send_message(
            user_id,
            f"🚫 تم حظرك من المجموعة.\n"
            f"السبب: {reason or 'لم يُحدد سبب'}\n"
            f"المدة: {fmt_duration(duration) if duration else 'دائم'}"
        )
    except Exception:
        pass
    await db.log_event(chat_id, "ban", user_id=banner_id, target_id=user_id, detail=f"reason={reason}")
    await db.log_bot_action(chat_id, "ban", user_id=user_id, detail=reason)

# ================================================

async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    reply_user = get_reply_user(update)
    if reply_user:
        user_id = reply_user.id
    elif context.args:
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("الاستخدام: رفع الحظر <معرف>")
            return
    else:
        await update.message.reply_text("قم بالرد على رسالة المستخدم أو أرسل المعرف")
        return
    chat_id = update.effective_chat.id
    unbanner_id = update.effective_user.id
    removed = await db.remove_ban(user_id, chat_id, performed_by=unbanner_id)
    try:
        await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
    except Exception as e:
        logger.warning("تعذّر رفع الحظر: %s", e)
    if removed:
        await update.message.reply_text(f"✅ تم رفع الحظر عن المستخدم {user_id}.")
        try:
            await context.bot.send_message(
                user_id,
                "✅ تم رفع الحظر عنك.\n\n"
                "يمكنك الانضمام للمجموعة مجدداً عبر هذا الرابط:\n"
                "https://t.me/+Wzrqvy2x08w1NTFk"
            )
        except Exception:
            pass
        await db.log_event(chat_id, "unban", user_id=unbanner_id, target_id=user_id)
    else:
        await update.message.reply_text(f"المستخدم {user_id} غير موجود في قائمة الحظر.")

# ================================================

async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    warner_id = update.effective_user.id
    reply_user = get_reply_user(update)
    if reply_user:
        user_id = reply_user.id
        reason = " ".join(context.args) if context.args else None
    elif context.args:
        try:
            user_id = int(context.args[0])
            reason = " ".join(context.args[1:]) or None
        except ValueError:
            await update.message.reply_text("قم بالرد أو أرسل: تحذير <معرف> [سبب]")
            return
    else:
        await update.message.reply_text("قم بالرد على رسالة المستخدم")
        return
    count = await db.add_warning(user_id, chat_id)
    reason_text = f"\nالسبب: {reason}" if reason else ""
    await db.log_event(chat_id, "warn", user_id=warner_id, target_id=user_id)
    if count >= MAX_WARNINGS:
        await db.add_ban(user_id, chat_id, f"حظر تلقائي بعد {MAX_WARNINGS} تحذيرات", warner_id)
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
        except Exception as e:
            logger.warning("تعذّر الحظر التلقائي: %s", e)
        await db.clear_warnings(user_id, chat_id)
        await update.message.reply_text(
            f"⛔ تم حظر المستخدم {user_id} تلقائياً بعد {MAX_WARNINGS} تحذيرات.{reason_text}"
        )
        try:
            await context.bot.send_message(
                user_id,
                f"⛔ تم حظرك تلقائياً بعد {MAX_WARNINGS} تحذيرات.\n"
                f"السبب: {reason or 'تجاوز الحد المسموح من التحذيرات'}"
            )
        except Exception:
            pass
        await db.log_bot_action(chat_id, "auto_ban", user_id=user_id, detail=f"بعد {MAX_WARNINGS} تحذيرات")
    else:
        await update.message.reply_text(
            f"⚠️ تحذير {count}/{MAX_WARNINGS} للمستخدم {user_id}.{reason_text}"
        )

# ================================================

async def cmd_clearwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    reply_user = get_reply_user(update)
    if reply_user:
        user_id = reply_user.id
    elif context.args:
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("معرف غير صالح.")
            return
    else:
        await update.message.reply_text("قم بالرد أو أرسل المعرف.")
        return
    chat_id = update.effective_chat.id
    await db.clear_warnings(user_id, chat_id)
    await update.message.reply_text(f"✅ تم مسح تحذيرات المستخدم {user_id}.")

# ================================================

async def cmd_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    reply_user = get_reply_user(update)
    if reply_user:
        user_id = reply_user.id
    elif context.args:
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("معرف غير صالح.")
            return
    else:
        await update.message.reply_text("قم بالرد أو أرسل المعرف.")
        return
    chat_id = update.effective_chat.id
    count = await db.get_warnings(user_id, chat_id)
    await update.message.reply_text(f"عدد تحذيرات المستخدم {user_id}: {count}/{MAX_WARNINGS}")

# ================================================

async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    from telegram import ChatPermissions
    from helpers import parse_duration
    reply_user = get_reply_user(update)
    if not reply_user and not context.args:
        await update.message.reply_text("قم بالرد أو: كتم <معرف> [مدة مثل 1h أو 1d]")
        return
    if reply_user:
        user_id = reply_user.id
        duration = parse_duration(context.args[0]) if context.args else None
    else:
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("معرف غير صالح.")
            return
        duration = parse_duration(context.args[1]) if len(context.args) > 1 else None
    chat_id = update.effective_chat.id
    until = expires_at_from_duration(duration)
    try:
        await context.bot.restrict_chat_member(
            chat_id, user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        dur_text = f" لمدة {fmt_duration(duration)}" if duration else " بشكل دائم"
        await update.message.reply_text(f"🔇 تم كتم المستخدم {user_id}{dur_text}.")
        await db.log_event(chat_id, "mute", user_id=update.effective_user.id, target_id=user_id)
    except Exception as e:
        await update.message.reply_text(f"❌ تعذّر الكتم: {e}")

# ================================================

async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    from telegram import ChatPermissions
    reply_user = get_reply_user(update)
    if reply_user:
        user_id = reply_user.id
    elif context.args:
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("معرف غير صالح.")
            return
    else:
        await update.message.reply_text("قم بالرد أو أرسل المعرف.")
        return
    chat_id = update.effective_chat.id
    try:
        await context.bot.restrict_chat_member(
            chat_id, user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await update.message.reply_text(f"🔊 تم رفع الكتم عن {user_id}.")
        await db.log_event(chat_id, "unmute", user_id=update.effective_user.id, target_id=user_id)
    except Exception as e:
        await update.message.reply_text(f"❌ تعذّر رفع الكتم: {e}")

# ================================================

async def cmd_lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    from telegram import ChatPermissions
    chat_id = update.effective_chat.id
    try:
        await context.bot.set_chat_permissions(
            chat_id, permissions=ChatPermissions(can_send_messages=False),
        )
        await update.message.reply_text("🔒 تم إغلاق المجموعة.")
        await db.log_event(chat_id, "lock", user_id=update.effective_user.id)
    except Exception as e:
        await update.message.reply_text(f"❌ تعذّر الإغلاق: {e}")

# ================================================

async def cmd_unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    from telegram import ChatPermissions
    chat_id = update.effective_chat.id
    try:
        await context.bot.set_chat_permissions(
            chat_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await update.message.reply_text("🔓 تم فتح المجموعة.")
        await db.log_event(chat_id, "unlock", user_id=update.effective_user.id)
    except Exception as e:
        await update.message.reply_text(f"❌ تعذّر الفتح: {e}")

# ================================================

async def cmd_banlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    bans = await db.get_ban_list(chat_id)
    if not bans:
        await update.message.reply_text("لا يوجد محظورون حالياً.")
        return
    lines = []
    for b in bans[:20]:
        exp = f" (ينتهي {b['expires_at'][:10]})" if b.get('expires_at') else " (دائم)"
        lines.append(f"• {b['user_id']}{exp}")
    await update.message.reply_text("🚫 المحظورون:\n" + "\n".join(lines))

# ================================================

async def cmd_baninfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    reply_user = get_reply_user(update)
    if reply_user:
        user_id = reply_user.id
    elif context.args:
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("معرف غير صالح.")
            return
    else:
        await update.message.reply_text("قم بالرد أو أرسل المعرف.")
        return
    chat_id = update.effective_chat.id
    ban = await db.get_ban(user_id, chat_id)
    if not ban:
        await update.message.reply_text(f"المستخدم {user_id} غير محظور.")
        return
    exp = ban['expires_at'][:10] if ban.get('expires_at') else "دائم"
    await update.message.reply_text(
        f"معلومات الحظر:\n"
        f"المعرف: {user_id}\n"
        f"السبب: {ban.get('reason') or 'غير محدد'}\n"
        f"ينتهي: {exp}"
    )

# ================================================

async def cmd_checkban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    reply_user = get_reply_user(update)
    if reply_user:
        user_id = reply_user.id
    elif context.args:
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("معرف غير صالح.")
            return
    else:
        await update.message.reply_text("قم بالرد أو أرسل المعرف.")
        return
    chat_id = update.effective_chat.id
    ban = await db.get_ban(user_id, chat_id)
    if ban:
        await update.message.reply_text(f"✅ المستخدم {user_id} محظور.\nالسبب: {ban.get('reason') or 'غير محدد'}")
    else:
        await update.message.reply_text(f"❌ المستخدم {user_id} غير محظور.")

# ================================================

async def cmd_eventlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    limit = int(context.args[0]) if context.args and context.args[0].isdigit() else 10
    events = await db.get_event_log(chat_id, limit)
    if not events:
        await update.message.reply_text("لا توجد أحداث مسجلة.")
        return
    lines = [f"• {e['action']} — {e['created_at'][:16]}" for e in events]
    await update.message.reply_text("📋 سجل الأحداث:\n" + "\n".join(lines))

# ================================================

async def cmd_setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: /setrules <النص>")
        return
    rules = update.message.text.split(" ", 1)[1]
    chat_id = update.effective_chat.id
    await db.set_setting(chat_id, "rules", rules)
    await update.message.reply_text("✅ تم تعيين قواعد المجموعة.")

# ================================================
# ========== الأوامر الجديدة المضافة ==========
# ================================================

# 1. رفع مشرف (يتطلب صلاحيات عالية، فقط المطور أو مشرف آخر)
async def cmd_promote_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return
    reply_user = get_reply_user(update)
    if not reply_user and not context.args:
        await update.message.reply_text("قم بالرد على العضو أو أرسل معرفه: رفع مشرف @username")
        return
    if reply_user:
        user_id = reply_user.id
    else:
        try:
            user_id = int(context.args[0]) if context.args[0].isdigit() else (await context.bot.get_chat(context.args[0])).id
        except:
            await update.message.reply_text("معرف غير صالح.")
            return
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, user_id,
            can_change_info=True, can_delete_messages=True, can_restrict_members=True,
            can_invite_users=True, can_pin_messages=True, can_promote_members=False
        )
        await update.message.reply_text(f"✅ تم رفع المستخدم {user_id} إلى مشرف.")
        await db.log_event(update.effective_chat.id, "promote", user_id=update.effective_user.id, target_id=user_id)
    except Exception as e:
        await update.message.reply_text(f"❌ تعذّرت الترقية: {e}")

# 2. تنزيل مشرف
async def cmd_demote_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    reply_user = get_reply_user(update)
    if not reply_user and not context.args:
        await update.message.reply_text("قم بالرد أو أرسل المعرف.")
        return
    if reply_user:
        user_id = reply_user.id
    else:
        try:
            user_id = int(context.args[0])
        except:
            await update.message.reply_text("معرف غير صالح.")
            return
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, user_id,
            can_change_info=False, can_delete_messages=False, can_restrict_members=False,
            can_invite_users=False, can_pin_messages=False, can_promote_members=False
        )
        await update.message.reply_text(f"✅ تم تنزيل المستخدم {user_id} من الإدارة.")
        await db.log_event(update.effective_chat.id, "demote", user_id=update.effective_user.id, target_id=user_id)
    except Exception as e:
        await update.message.reply_text(f"❌ تعذّر التنزيل: {e}")

# 3. عرض قائمة المشرفين
async def cmd_list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        text = "👮 قائمة المشرفين:\n"
        for admin in admins:
            user = admin.user
            text += f"• {user.first_name} (@{user.username if user.username else 'لا يوجد'})\n"
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"❌ لا يمكن جلب القائمة: {e}")

# 4. تنزيل الكل (إزالة صلاحيات المشرفين عن الجميع)
async def cmd_demote_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    await update.message.reply_text("⚠️ هذه العملية ستجرد جميع المشرفين من صلاحياتهم ما عدا المالك.\nأكتب 'تأكيد' لتأكيد.")
    context.user_data['awaiting_demote_all'] = update.effective_chat.id

# معالج تأكيد تنزيل الكل (يمكن إضافته في handle_text)
# لكننا نضيف هنا دالة بسيطة للاستجابة لـ "تأكيد"
# سيتم استدعاؤها من handle_text
async def confirm_demote_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_demote_all') != update.effective_chat.id:
        return
    del context.user_data['awaiting_demote_all']
    if not await require_admin(update, context):
        return
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        owner_id = update.effective_chat.id  # المالك هو منشئ المجموعة
        # نبحث عن المالك
        for admin in admins:
            if admin.status == 'creator':
                owner_id = admin.user.id
                break
        for admin in admins:
            if admin.user.id != owner_id:
                await context.bot.promote_chat_member(
                    update.effective_chat.id, admin.user.id,
                    can_change_info=False, can_delete_messages=False, can_restrict_members=False,
                    can_invite_users=False, can_pin_messages=False, can_promote_members=False
                )
        await update.message.reply_text("✅ تم تنزيل جميع المشرفين (ما عدا المالك).")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل: {e}")

# 5. مسح المحظورين (إزالة جميع الحظر)
async def cmd_purge_bans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    chat_id = update.effective_chat.id
    bans = await db.get_ban_list(chat_id)
    count = 0
    for ban in bans:
        user_id = ban['user_id']
        if await db.remove_ban(user_id, chat_id):
            try:
                await context.bot.unban_chat_member(chat_id, user_id)
                count += 1
            except:
                pass
    await update.message.reply_text(f"✅ تم مسح {count} حظر من القائمة.")

# 6. مسح المكتومين
async def cmd_purge_muted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    # المكتمون ليس لديهم قائمة خاصة، نحتاج إلى معرفة المكتمين عبر قاعدة بيانات أو مسح كل القيود
    # نكتفي بإعادة تعيين الصلاحيات للجميع (فتح المجموعة)
    await update.message.reply_text("⚠️ سيتم فتح المجموعة ورفع الكتم عن الجميع.")
    from telegram import ChatPermissions
    try:
        await context.bot.set_chat_permissions(
            update.effective_chat.id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_polls=True, can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        await update.message.reply_text("✅ تم رفع الكتم عن جميع الأعضاء.")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل: {e}")

# 7. تاك للكل (منشن جميع الأعضاء)
async def cmd_tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    try:
        # الحصول على أول 200 عضو (حد تيليجرام)
        members = []
        async for member in context.bot.get_chat_members(update.effective_chat.id):
            if not member.user.is_bot:
                members.append(f"@{member.user.username}" if member.user.username else f"[{member.user.first_name}](tg://user?id={member.user.id})")
            if len(members) >= 50:  # تجنب الإزعاج
                break
        mentions = " ".join(members)
        await update.message.reply_text(f"📢 تنبيه: {mentions}\n{update.message.text.split(' ', 1)[1] if len(context.args) > 0 else ''}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل التاك: {e}")

# 8. رتبتي (عرض رتبة العضو)
async def cmd_my_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    try:
        member = await context.bot.get_chat_member(chat_id, user.id)
        rank = member.status
        rank_map = {'creator': '👑 المالك', 'administrator': '👮 مشرف', 'member': '👤 عضو', 'restricted': '🔇 مكتوم', 'left': '🚪 خارج', 'kicked': '🚫 محظور'}
        await update.message.reply_text(f"رتبتك: {rank_map.get(rank, rank)}")
    except Exception as e:
        await update.message.reply_text(f"❌ لا يمكن جلب الرتبة: {e}")

# 9. رتبته (عرض رتبة عضو آخر)
async def cmd_his_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        await update.message.reply_text("⛔ للمشرفين فقط.")
        return
    reply_user = get_reply_user(update)
    if not reply_user and not context.args:
        await update.message.reply_text("قم بالرد على العضو أو أرسل معرفه/يوزر.")
        return
    if reply_user:
        target_id = reply_user.id
    else:
        try:
            target_id = int(context.args[0]) if context.args[0].isdigit() else (await context.bot.get_chat(context.args[0])).id
        except:
            await update.message.reply_text("معرف غير صالح.")
            return
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, target_id)
        rank = member.status
        rank_map = {'creator': '👑 المالك', 'administrator': '👮 مشرف', 'member': '👤 عضو', 'restricted': '🔇 مكتوم', 'left': '🚪 خارج', 'kicked': '🚫 محظور'}
        await update.message.reply_text(f"رتبة العضو: {rank_map.get(rank, rank)}")
    except Exception as e:
        await update.message.reply_text(f"❌ لا يمكن جلب الرتبة: {e}")