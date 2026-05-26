import logging
from datetime import datetime, timezone

from telegram import Update, ChatMemberUpdated
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus

import database as db
from helpers import (
    require_admin,
    is_admin,
    get_reply_user,
    parse_ban_args,
    expires_at_from_duration,
    fmt_duration,
    fmt_user,
    notify_admins,
    get_admin_ids,
    estimate_telegram_registration,
)

logger = logging.getLogger(__name__)

MAX_WARNINGS = 3


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "بوت حارس المجموعة نشط.\n\n"
        "أوامر المشرفين:\n"
        "/ban — حظر\n/unban — رفع الحظر\n/warn — تحذير\n"
        "/banlist — قائمة المحظورين\n/mute — كتم\n"
        "/lock — إغلاق المجموعة\n/unlock — فتح المجموعة\n\n"
        "للجميع:\n/id أو ايدي — معلوماتك"
    )
async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    reply_user = get_reply_user(update)

    from telegram import Chat as TGChat
    in_group = chat.type in (TGChat.GROUP, TGChat.SUPERGROUP)

    if reply_user and reply_user.id != user.id:
        if not in_group or not await is_admin(update, context):
            await update.message.reply_text("لا يمكنك عرض بيانات عضو آخر.")
            return
        count      = await db.get_message_count(reply_user.id, chat.id) if in_group else 0
        first_seen = await db.get_user_first_seen(reply_user.id, chat.id) if in_group else None
        username   = f"@{reply_user.username}" if reply_user.username else "غير محدد"
        reg_date   = estimate_telegram_registration(reply_user.id)
        seen_line  = f"\nأول رسالة: {first_seen[:10]}" if first_seen else ""
        await update.message.reply_text(
            f"معلومات العضو:\nالاسم: {reply_user.first_name}\n"
            f"اليوزر: {username}\nالمعرف: {reply_user.id}\n"
            f"تاريخ التسجيل: {reg_date}\n"
            f"عدد الرسائل: {count}{seen_line}"
        )
    else:
        count      = await db.get_message_count(user.id, chat.id) if in_group else 0
        first_seen = await db.get_user_first_seen(user.id, chat.id) if in_group else None
        username   = f"@{user.username}" if user.username else "غير محدد"
        reg_date   = estimate_telegram_registration(user.id)
        seen_line  = f"\nأول رسالة: {first_seen[:10]}" if first_seen else ""
        await update.message.reply_text(
            f"معلوماتك:\nالاسم: {user.first_name}\n"
            f"اليوزر: {username}\nالمعرف: {user.id}\n"
            f"تاريخ التسجيل: {reg_date}\n"
            f"عدد الرسائل: {count}{seen_line}"
        )
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
    await update.message.reply_text(f"تم حظر المستخدم {user_id}.{duration_text}{reason_text}")
    await db.log_event(chat_id, "ban", user_id=banner_id, target_id=user_id)


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
        await update.message.reply_text(f"تم رفع الحظر عن المستخدم {user_id}.")
        await db.log_event(chat_id, "unban", user_id=unbanner_id, target_id=user_id)
    else:
        await update.message.reply_text(f"المستخدم {user_id} غير موجود في قائمة الحظر.")
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
    else:
        await update.message.reply_text(
            f"⚠️ تحذير {count}/{MAX_WARNINGS} للمستخدم {user_id}.{reason_text}"
        )


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
    await update.message.reply_text("المحظورون:\n" + "\n".join(lines))


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
        f"معلومات الحظر:\nالمعرف: {user_id}\n"
        f"السبب: {ban.get('reason') or 'غير محدد'}\n"
        f"ينتهي: {exp}"
    )


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
        await update.message.reply_text(f"✅ المستخدم {user_id} محظور.")
    else:
        await update.message.reply_text(f"❌ المستخدم {user_id} غير محظور.")


async def cmd_eventlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    limit = int(context.args[0]) if context.args and context.args[0].isdigit() else 10
    events = await db.get_event_log(chat_id, limit)
    if not events:
        await update.message.reply_text("لا توجد أحداث مسجلة.")
        return
    lines = [f"• {e['event_type']} — {e['created_at'][:16]}" for e in events]
    await update.message.reply_text("سجل الأحداث:\n" + "\n".join(lines))
async def cmd_setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: /setrules <النص>")
        return
    rules = " ".join(context.args)
    chat_id = update.effective_chat.id
    await db.set_setting(chat_id, "rules", rules)
    await update.message.reply_text("✅ تم تعيين قواعد المجموعة.")


async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    rules = await db.get_setting(chat_id, "rules")
    if rules:
        await update.message.reply_text(f"قواعد المجموعة:\n{rules}")
    else:
        await update.message.reply_text("لم يتم تعيين قواعد بعد.")


async def cmd_add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: أضف كلمة <الكلمة>")
        return
    word = " ".join(context.args).lower().strip()
    chat_id = update.effective_chat.id
    added = await db.add_banned_word(chat_id, word)
    if added:
        await update.message.reply_text(f"✅ تمت إضافة الكلمة: {word}")
    else:
        await update.message.reply_text(f"الكلمة '{word}' موجودة مسبقاً.")


async def cmd_remove_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: احذف كلمة <الكلمة>")
        return
    word = " ".join(context.args).lower().strip()
    chat_id = update.effective_chat.id
    removed = await db.remove_banned_word(chat_id, word)
    if removed:
        await update.message.reply_text(f"✅ تمت إزالة الكلمة: {word}")
    else:
        await update.message.reply_text(f"الكلمة '{word}' غير موجودة.")


async def cmd_list_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    words = await db.get_banned_words(chat_id)
    if not words:
        await update.message.reply_text("لا توجد كلمات محظورة.")
        return
    await update.message.reply_text("الكلمات المحظورة:\n" + "\n".join(f"• {w}" for w in words))
async def filter_banned_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    from telegram import Chat as TGChat
    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return
    if await is_admin(update, context):
        return
    chat_id = update.effective_chat.id
    user = update.effective_user
    text = msg.text.lower()
    words = await db.get_banned_words(chat_id)
    for word in words:
        if word in text:
            try:
                await msg.delete()
            except Exception:
                pass
            count = await db.add_warning(user.id, chat_id)
            if count >= MAX_WARNINGS:
                await db.add_ban(user.id, chat_id, f"حظر تلقائي بعد {MAX_WARNINGS} تحذيرات", 0)
                try:
                    await context.bot.ban_chat_member(chat_id, user.id)
                except Exception:
                    pass
                await db.clear_warnings(user.id, chat_id)
                await context.bot.send_message(
                    chat_id,
                    f"⛔ تم حظر {user.full_name} بعد {MAX_WARNINGS} تحذيرات."
                )
            else:
                await context.bot.send_message(
                    chat_id,
                    f"⚠️ {user.full_name}، رسالتك تحتوي كلمات غير لائقة.\n"
                    f"التحذير {count}/{MAX_WARNINGS}"
                )
            return


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
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await update.message.reply_text(f"🔊 تم رفع الكتم عن {user_id}.")
        await db.log_event(chat_id, "unmute", user_id=update.effective_user.id, target_id=user_id)
    except Exception as e:
        await update.message.reply_text(f"❌ تعذّر رفع الكتم: {e}")


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


async def on_chat_member_updated(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return
    new_member = result.new_chat_member
    old_member = result.old_chat_member
    chat_id = result.chat.id
    user = new_member.user
    if new_member.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED):
        if old_member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
            ban = await db.get_ban(user.id, chat_id)
            if ban:
                try:
                    await context.bot.ban_chat_member(chat_id, user.id)
                    await context.bot.send_message(
                        chat_id,
                        f"⚠️ محاولة دخول! تم طرد عضو محظور تلقائياً."
                    )
                    admin_ids = await get_admin_ids(context.bot, chat_id)
                    for admin_id in admin_ids:
                        try:
                            await context.bot.send_message(
                                admin_id,
                                f"⚠️ المستخدم {user.id} ({user.full_name}) حاول الدخول وهو محظور."
                            )
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning("تعذّر طرد المستخدم المحظور: %s", e)
            else:
                welcome = (
                    f"👋 أهلاً وسهلاً {user.first_name}!\n"
                    f"نرحب بك في مجموعتنا. يرجى الالتزام بالقواعد واحترام الجميع. 😊"
                )
                try:
                    await context.bot.send_message(chat_id, welcome)
                except Exception:
                    pass


async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    from telegram import Chat as TGChat
    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return
    await db.increment_message_count(update.effective_user.id, update.effective_chat.id)


async def job_expire_bans(context: ContextTypes.DEFAULT_TYPE):
    expired = await db.get_expired_bans()
    for ban in expired:
        user_id = ban["user_id"]
        chat_id = ban["chat_id"]
        await db.remove_ban(user_id, chat_id)
        try:
            await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
            await context.bot.send_message(
                chat_id,
                f"انتهت مدة حظر المستخدم {user_id}. يمكنه الانضمام مجدداً."
            )
        except Exception as e:
            logger.warning("خطأ في رفع حظر المستخدم %s: %s", user_id, e)