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


# ── /start /help ───────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "بوت حارس المجموعة نشط.\n\n"
        "أوامر المشرفين:\n"
        "/ban أو /حظر [رد|معرف] [مدة] [سبب] — حظر مستخدم (مثال: /ban 7d مزعج)\n"
        "/unban أو /رفع_الحظر [رد|معرف] — إلغاء الحظر\n"
        "/warn أو /تحذير [رد|معرف] [سبب] — إصدار تحذير (التحذير الثاني = حظر تلقائي)\n"
        "/clearwarn [رد|معرف] — مسح تحذيرات مستخدم\n"
        "/warnings [رد|معرف] — عرض عدد التحذيرات\n"
        "/banlist أو /قائمة — قائمة المحظورين\n"
        "/baninfo أو /معلومات [رد|معرف] — تفاصيل الحظر\n"
        "/checkban أو /تحقق [رد|معرف] — التحقق من الحظر\n"
        "/eventlog أو /سجل [عدد] — سجل الأحداث الكامل\n"
        "/setrules <النص> — تعيين قواعد المجموعة\n\n"
        "للجميع:\n"
        "/rules — عرض قواعد المجموعة\n"
        "/id أو /ايدي — معلوماتك الشخصية\n"
        "/id أو /ايدي [رد] — معلومات عضو آخر (للمشرفين فقط)"
    )


# ── /id / /ايدي ───────────────────────────────────────────────────────────────

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    reply_user = get_reply_user(update)

    # Private chat — always show own info
    from telegram import Chat as TGChat
    in_group = chat.type in (TGChat.GROUP, TGChat.SUPERGROUP)

    if reply_user and reply_user.id != user.id:
        # Someone is replying to another member
        if not in_group or not await is_admin(update, context):
            await update.message.reply_text("لا يمكنك عرض بيانات عضو آخر.")
            return
        # Admin looking up another member
        count      = await db.get_message_count(reply_user.id, chat.id) if in_group else 0
        first_seen = await db.get_user_first_seen(reply_user.id, chat.id) if in_group else None
        username   = f"@{reply_user.username}" if reply_user.username else "غير محدد"
        reg_date   = estimate_telegram_registration(reply_user.id)
        seen_line  = f"\nأول رسالة في المجموعة: {first_seen[:10]}" if first_seen else ""
        await update.message.reply_text(
            f"معلومات العضو:\n"
            f"الاسم الأول: {reply_user.first_name}\n"
            f"اسم المستخدم: {username}\n"
            f"المعرف: {reply_user.id}\n"
            f"تاريخ تسجيل الحساب بتيليغرام: {reg_date}\n"
            f"عدد الرسائل في المجموعة: {count}"
            f"{seen_line}"
        )
    else:
        # Showing own info — available to everyone
        count      = await db.get_message_count(user.id, chat.id) if in_group else 0
        first_seen = await db.get_user_first_seen(user.id, chat.id) if in_group else None
        username   = f"@{user.username}" if user.username else "غير محدد"
        reg_date   = estimate_telegram_registration(user.id)
        seen_line  = f"\nأول رسالة في المجموعة: {first_seen[:10]}" if first_seen else ""
        await update.message.reply_text(
            f"معلوماتك:\n"
            f"الاسم الأول: {user.first_name}\n"
            f"اسم المستخدم: {username}\n"
            f"المعرف: {user.id}\n"
            f"تاريخ تسجيل الحساب بتيليغرام: {reg_date}\n"
            f"عدد الرسائل في المجموعة: {count}"
            f"{seen_line}"
        )


# ── /ban ──────────────────────────────────────────────────────────────────────

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
        logger.warning("تعذّر حظر المستخدم %s في المجموعة %s: %s", user_id, chat_id, e)

    reason_text = f"\nالسبب: {reason}" if reason else ""
    if duration:
        duration_text = f"\nالمدة: {fmt_duration(duration)} (ينتهي {expires_at.strftime('%Y-%m-%d %H:%M UTC')})"
    else:
        duration_text = "\nالمدة: دائم"

    await update.message.reply_text(
        f"تم حظر المستخدم {user_id}.{duration_text}{reason_text}"
    )

    await db.log_event(
        chat_id, "ban", user_id=banner_id, target_id=user_id,
        detail=f"duration={fmt_duration(duration) if duration else 'دائم'} reason={reason}"
    )


# ── /unban ────────────────────────────────────────────────────────────────────

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
            await update.message.reply_text("الاستخدام: /unban <معرف المستخدم>")
            return
    else:
        await update.message.reply_text("قم بالرد على رسالة المستخدم أو أرسل /unban <معرف>")
        return

    chat_id = update.effective_chat.id
    unbanner_id = update.effective_user.id

    removed = await db.remove_ban(user_id, chat_id, performed_by=unbanner_id)
    try:
        await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
    except Exception as e:
        logger.warning("تعذّر رفع الحظر عن المستخدم %s في المجموعة %s: %s", user_id, chat_id, e)

    if removed:
        await update.message.reply_text(f"تم رفع الحظر عن المستخدم {user_id} وإزالته من القائمة.")
        await db.log_event(chat_id, "unban", user_id=unbanner_id, target_id=user_id)
    else:
        await update.message.reply_text(f"المستخدم {user_id} غير موجود في قائمة الحظر.")


# ── /warn ─────────────────────────────────────────────────────────────────────

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
            await update.message.reply_text("قم بالرد على رسالة المستخدم أو أرسل /warn <معرف> [سبب]")
            return
    else:
        await update.message.reply_text("قم بالرد على رسالة المستخدم أو أرسل /warn <معرف> [سبب]")
        return

    count = await db.add_warning(user_id, chat_id)
    reason_text = f"\nالسبب: {reason}" if reason else ""

    await db.log_event(
        chat_id, "warn", user_id=warner_id, target_id=user_id,
        detail=f"count={count} reason={reason}"
    )

    if count >= MAX_WARNINGS:
        await db.add_ban(user_id, chat_id, f"حظر تلقائي بعد {MAX_WARNINGS} تحذيرات", warner_id)
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
        except Exception as e:
            logger.warning("تعذّر الحظر التلقائي للمستخدم %s في المجموعة %s: %s", user_id, chat_id, e)
        await db.clear_warnings(user_id, chat_id)
        await update.message.reply_text(
            f"تم إصدار تحذير {count}/{MAX_WARNINGS} للمستخدم {user_id}.{reason_text}\n"
            f"وصل المستخدم إلى الحد الأقصى للتحذيرات وتم حظره تلقائيًا."
        )
        await db.log_event(
            chat_id, "auto_ban", user_id=warner_id, target_id=user_id,
            detail=f"حظر تلقائي بعد {MAX_WARNINGS} تحذيرات"
        )
    else:
        remaining = MAX_WARNINGS - count
        await update.message.reply_text(
            f"تحذير {count}/{MAX_WARNINGS} للمستخدم {user_id}.{reason_text}\n"
            f"تحذير {remaining} آخر سيؤدي إلى الحظر التلقائي."
        )


# ── /clearwarn ────────────────────────────────────────────────────────────────

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
            await update.message.reply_text("الاستخدام: /clearwarn <معرف المستخدم>")
            return
    else:
        await update.message.reply_text("قم بالرد على رسالة المستخدم أو أرسل /clearwarn <معرف>")
        return

    chat_id = update.effective_chat.id
    cleared = await db.clear_warnings(user_id, chat_id)
    if cleared:
        await update.message.reply_text(f"تم مسح تحذيرات المستخدم {user_id}.")
        await db.log_event(chat_id, "clearwarn", user_id=update.effective_user.id, target_id=user_id)
    else:
        await update.message.reply_text(f"لا توجد تحذيرات للمستخدم {user_id}.")


# ── /warnings ─────────────────────────────────────────────────────────────────

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
            await update.message.reply_text("الاستخدام: /warnings <معرف المستخدم>")
            return
    else:
        await update.message.reply_text("قم بالرد على رسالة المستخدم أو أرسل /warnings <معرف>")
        return

    chat_id = update.effective_chat.id
    count = await db.get_warning_count(user_id, chat_id)
    await update.message.reply_text(
        f"المستخدم {user_id} لديه {count}/{MAX_WARNINGS} تحذير(ات)."
    )


# ── /banlist ──────────────────────────────────────────────────────────────────

async def cmd_banlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return

    chat_id = update.effective_chat.id
    bans = await db.list_bans(chat_id)

    if not bans:
        await update.message.reply_text("لا يوجد مستخدمون محظورون في هذه المجموعة.")
        return

    lines = [f"المستخدمون المحظورون ({len(bans)} إجمالًا):\n"]
    for ban in bans:
        reason_part = f" — {ban['reason']}" if ban.get("reason") else ""
        if ban.get("expires_at"):
            expires_part = f" [ينتهي {ban['expires_at'][:10]}]"
        else:
            expires_part = " [دائم]"
        lines.append(f"• {ban['user_id']}{expires_part}{reason_part}")

    await update.message.reply_text("\n".join(lines))


# ── /baninfo ──────────────────────────────────────────────────────────────────

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
            await update.message.reply_text("الاستخدام: /baninfo <معرف المستخدم>")
            return
    else:
        await update.message.reply_text("قم بالرد على رسالة المستخدم أو أرسل /baninfo <معرف>")
        return

    chat_id = update.effective_chat.id
    info = await db.get_ban_info(user_id, chat_id)
    if not info:
        await update.message.reply_text(f"المستخدم {user_id} غير موجود في قائمة الحظر.")
        return

    expires = info.get("expires_at") or "لا ينتهي (دائم)"
    reason = info.get("reason") or "لم يُذكر سبب"
    await update.message.reply_text(
        f"تفاصيل حظر المستخدم {user_id}:\n"
        f"السبب: {reason}\n"
        f"حُظر بواسطة: {info['banned_by']}\n"
        f"تاريخ الحظر: {info['banned_at']}\n"
        f"ينتهي: {expires}"
    )


# ── /checkban ─────────────────────────────────────────────────────────────────

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
            await update.message.reply_text("الاستخدام: /checkban <معرف المستخدم>")
            return
    else:
        await update.message.reply_text("قم بالرد على رسالة المستخدم أو أرسل /checkban <معرف>")
        return

    chat_id = update.effective_chat.id
    info = await db.get_ban_info(user_id, chat_id)

    if info:
        reason = info.get("reason") or "لم يُذكر سبب"
        expires = info.get("expires_at") or "لا ينتهي"
        await update.message.reply_text(
            f"المستخدم {user_id} محظور.\n"
            f"السبب: {reason}\n"
            f"ينتهي: {expires}"
        )
    else:
        await update.message.reply_text(f"المستخدم {user_id} غير محظور.")


# ── /eventlog ─────────────────────────────────────────────────────────────────

_EVENT_LABELS = {
    "ban":            "حظر",
    "unban":          "رفع حظر",
    "warn":           "تحذير",
    "auto_ban":       "حظر تلقائي",
    "clearwarn":      "مسح تحذيرات",
    "joined":         "انضم",
    "left":           "غادر",
    "rejoin_blocked": "محاولة إعادة انضمام",
    "ban_expired":    "انتهاء مدة الحظر",
    "setrules":       "تعيين قواعد",
}


async def cmd_eventlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return

    chat_id = update.effective_chat.id
    limit = 30
    if context.args:
        try:
            limit = min(int(context.args[0]), 100)
        except ValueError:
            pass

    events = await db.get_event_log(chat_id, limit=limit)
    if not events:
        await update.message.reply_text("لا توجد أحداث مسجّلة بعد.")
        return

    lines = [f"سجل الأحداث (آخر {len(events)}):\n"]
    for e in events:
        ts = e["created_at"][:16]
        label = _EVENT_LABELS.get(e["event_type"], e["event_type"])
        actor = f" بواسطة {e['user_id']}" if e.get("user_id") else ""
        target = f" ← {e['target_id']}" if e.get("target_id") else ""
        detail = f" ({e['detail']})" if e.get("detail") else ""
        lines.append(f"[{ts}] {label}{actor}{target}{detail}")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "\n...(مقتطع)"
    await update.message.reply_text(text)


# ── /setrules & /rules ────────────────────────────────────────────────────────

async def cmd_setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return

    if not context.args:
        await update.message.reply_text("الاستخدام: /setrules <نص القواعد>")
        return

    rules = " ".join(context.args)
    chat_id = update.effective_chat.id
    await db.set_setting(chat_id, "rules", rules)
    await update.message.reply_text("تم تحديث قواعد المجموعة.")
    await db.log_event(chat_id, "setrules", user_id=update.effective_user.id, detail=rules[:100])


async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    rules = await db.get_setting(chat_id, "rules")
    if rules:
        await update.message.reply_text(f"قواعد المجموعة:\n\n{rules}")
    else:
        await update.message.reply_text(
            "لم يتم تعيين قواعد بعد. يمكن للمشرفين استخدام /setrules لإضافتها."
        )


# ── Chat member events ────────────────────────────────────────────────────────

async def on_chat_member_updated(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result: ChatMemberUpdated = update.chat_member
    if not result:
        return

    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    user = result.new_chat_member.user
    chat_id = result.chat.id

    joined = new_status in (
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER,
    ) and old_status not in (
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER,
    )

    left = new_status in (
        ChatMemberStatus.LEFT,
        ChatMemberStatus.BANNED,
    ) and old_status in (
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER,
    )

    if left:
        await db.log_event(chat_id, "left", user_id=user.id, detail=user.full_name)
        return

    if not joined:
        return

    await db.log_event(chat_id, "joined", user_id=user.id, detail=user.full_name)

    # Check if this user is banned
    banned = await db.is_banned(user.id, chat_id)
    if banned:
        logger.info("مستخدم محظور %s حاول الانضمام إلى المجموعة %s — جارٍ الحظر", user.id, chat_id)
        info = await db.get_ban_info(user.id, chat_id)
        reason = info.get("reason") or "لم يُذكر سبب"

        try:
            await context.bot.ban_chat_member(chat_id, user.id)
        except Exception as e:
            logger.error("فشل إعادة حظر المستخدم %s في المجموعة %s: %s", user.id, chat_id, e)

        await db.log_event(chat_id, "rejoin_blocked", user_id=user.id,
                           detail=f"أعيد حظره: {reason}")

        # Public group notice
        await context.bot.send_message(
            chat_id,
            f"المستخدم {user.full_name} (المعرف: {user.id}) حاول الانضمام للمجموعة لكنه محظور.\n"
            f"سبب الحظر: {reason}\n"
            f"تم إزالته مجددًا."
        )

        # Private DM to all admins
        admin_msg = (
            f"تنبيه: مستخدم محظور حاول الانضمام!\n\n"
            f"المجموعة: {result.chat.title} (المعرف: {chat_id})\n"
            f"المستخدم: {fmt_user(user)} (المعرف: {user.id})\n"
            f"سبب الحظر: {reason}"
        )
        await notify_admins(context.bot, chat_id, admin_msg)
        return

    # New member — send welcome message
    rules = await db.get_setting(chat_id, "rules")
    name = user.full_name
    if rules:
        welcome = (
            f"أهلًا وسهلًا بك يا {name}!\n\n"
            f"يرجى قراءة قواعد المجموعة:\n\n"
            f"{rules}\n\n"
            f"نتمنى لك وقتًا ممتعًا!"
        )
    else:
        welcome = f"أهلًا وسهلًا بك يا {name} في المجموعة! يرجى احترام الجميع."

    try:
        await context.bot.send_message(chat_id, welcome)
    except Exception as e:
        logger.warning("تعذّر إرسال رسالة الترحيب: %s", e)


# ── Message count tracker ─────────────────────────────────────────────────────

async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silently count every group message per user."""
    if not update.message or not update.effective_user:
        return
    from telegram import Chat as TGChat
    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return
    await db.increment_message_count(update.effective_user.id, update.effective_chat.id)


# ── Banned words ─────────────────────────────────────────────────────────────

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
        await update.message.reply_text(f"✅ تمت إضافة الكلمة المحظورة: {word}")
    else:
        await update.message.reply_text(f"الكلمة '{word}' موجودة مسبقاً في القائمة.")


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
        await update.message.reply_text(f"الكلمة '{word}' غير موجودة في القائمة.")


async def cmd_list_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    words = await db.get_banned_words(chat_id)
    if not words:
        await update.message.reply_text("لا توجد كلمات محظورة حتى الآن.")
        return
    text = "الكلمات المحظورة:\n\n" + "\n".join(f"• {w}" for w in words)
    await update.message.reply_text(text)


async def filter_banned_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فلتر تلقائي للكلمات المحظورة في كل رسالة."""
    msg = update.message
    if not msg or not msg.text:
        return
    from telegram import Chat as TGChat
    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user

    # لا تفلتر رسائل المشرفين
    if await is_admin(update, context):
        return

    text = msg.text.lower()
    words = await db.get_banned_words(chat_id)

    for word in words:
        if word in text:
            try:
                await msg.delete()
            except Exception:
                pass

            count = await db.add_warning(user.id, chat_id)
            await db.log_event(chat_id, "banned_word", user_id=user.id, detail=f"كلمة: {word}")

            if count >= MAX_WARNINGS:
                await db.add_ban(user.id, chat_id, f"حظر تلقائي بعد {MAX_WARNINGS} تحذيرات", 0)
                try:
                    await context.bot.ban_chat_member(chat_id, user.id)
                except Exception:
                    pass
                await db.clear_warnings(user.id, chat_id)
                await context.bot.send_message(
                    chat_id,
                    f"⛔ تم حظر {user.full_name} بعد {MAX_WARNINGS} تحذيرات بسبب استخدام كلمات محظورة."
                )
            else:
                await context.bot.send_message(
                    chat_id,
                    f"⚠️ {user.full_name}، تم حذف رسالتك لاحتوائها على كلمات غير لائقة.\n"
                    f"التحذير {count}/{MAX_WARNINGS}"
                )
            return


# ── Mute / Unmute ─────────────────────────────────────────────────────────────

async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return

    from telegram import ChatPermissions
    from helpers import parse_duration, expires_at_from_duration

    reply_user = get_reply_user(update)
    if not reply_user and not context.args:
        await update.message.reply_text("قم بالرد على رسالة العضو أو: كتم <معرف> [مدة مثل 1h أو 1d]")
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
        await update.message.reply_text("قم بالرد أو: رفع الكتم <معرف>")
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
        await update.message.reply_text(f"🔊 تم رفع الكتم عن المستخدم {user_id}.")
        await db.log_event(chat_id, "unmute", user_id=update.effective_user.id, target_id=user_id)
    except Exception as e:
        await update.message.reply_text(f"❌ تعذّر رفع الكتم: {e}")


# ── Lock / Unlock group ────────────────────────────────────────────────────────

async def cmd_lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return

    from telegram import ChatPermissions

    chat_id = update.effective_chat.id
    try:
        await context.bot.set_chat_permissions(
            chat_id,
            permissions=ChatPermissions(can_send_messages=False),
        )
        await update.message.reply_text("🔒 تم إغلاق المجموعة — فقط المشرفون يستطيعون الكتابة.")
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
        await update.message.reply_text("🔓 تم فتح المجموعة — الجميع يستطيع الكتابة.")
        await db.log_event(chat_id, "unlock", user_id=update.effective_user.id)
    except Exception as e:
        await update.message.reply_text(f"❌ تعذّر الفتح: {e}")


# ── Expired ban auto-unban job ────────────────────────────────────────────────

async def job_expire_bans(context: ContextTypes.DEFAULT_TYPE):
    expired = await db.get_expired_bans()
    for ban in expired:
        user_id = ban["user_id"]
        chat_id = ban["chat_id"]
        logger.info("انتهت مدة حظر المستخدم %s في المجموعة %s — جارٍ رفع الحظر", user_id, chat_id)
        await db.remove_ban(user_id, chat_id)
        try:
            await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
            await context.bot.send_message(
                chat_id,
                f"انتهت مدة حظر المستخدم {user_id}. يمكنه الانضمام إلى المجموعة مجددًا."
            )
        except Exception as e:
            logger.warning("خطأ في رفع حظر المستخدم %s في المجموعة %s: %s", user_id, chat_id, e)
        await db.log_event(
            chat_id, "ban_expired", target_id=user_id,
            detail=f"السبب كان: {ban.get('reason', 'غير محدد')}"
        )
