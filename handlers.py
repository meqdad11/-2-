import logging
from datetime import datetime, timezone

from telegram import Update, ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup
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

# ── أوامر عامة ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 أوامر المشرفين", callback_data="help_admin")],
        [InlineKeyboardButton("🎵 أوامر الموسيقى", callback_data="help_music")],
        [InlineKeyboardButton("🎮 لعبة التركيز", callback_data="help_focus")],
    ])
    await update.message.reply_text(
        "👋 مرحباً بك في بوت حارس المجموعة!\n\n"
        "أنا بوت متكامل لإدارة المجموعات مع ميزات متقدمة.\n"
        "اختر من القائمة أدناه:",
        reply_markup=keyboard
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
        count = await db.get_message_count(reply_user.id, chat.id) if in_group else 0
        first_seen = await db.get_user_first_seen(reply_user.id, chat.id) if in_group else None
        username = f"@{reply_user.username}" if reply_user.username else "غير محدد"
        reg_date = estimate_telegram_registration(reply_user.id)
        seen_line = f"\nأول رسالة: {first_seen[:10]}" if first_seen else ""
        
        text = (
            f"📊 معلومات العضو:\n"
            f"👤 الاسم: {reply_user.first_name}\n"
            f"🔖 اليوزر: {username}\n"
            f"🆔 المعرف: `{reply_user.id}`\n"
            f"📅 تاريخ التسجيل: {reg_date}\n"
            f"💬 عدد الرسائل: {count}{seen_line}"
        )
        
        if reply_user.photo:
            try:
                photo_file = await reply_user.photo[-1].get_file()
                await update.message.reply_photo(
                    photo=photo_file.file_id,
                    caption=text,
                    parse_mode="Markdown"
                )
                return
            except Exception:
                pass
        
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        count = await db.get_message_count(user.id, chat.id) if in_group else 0
        first_seen = await db.get_user_first_seen(user.id, chat.id) if in_group else None
        username = f"@{user.username}" if user.username else "غير محدد"
        reg_date = estimate_telegram_registration(user.id)
        seen_line = f"\nأول رسالة: {first_seen[:10]}" if first_seen else ""
        
        text = (
            f"📊 معلوماتك:\n"
            f"👤 الاسم: {user.first_name}\n"
            f"🔖 اليوزر: {username}\n"
            f"🆔 المعرف: `{user.id}`\n"
            f"📅 تاريخ التسجيل: {reg_date}\n"
            f"💬 عدد الرسائل: {count}{seen_line}"
        )
        
        if user.photo:
            try:
                photo_file = await user.photo[-1].get_file()
                await update.message.reply_photo(
                    photo=photo_file.file_id,
                    caption=text,
                    parse_mode="Markdown"
                )
                return
            except Exception:
                pass
        
        await update.message.reply_text(text, parse_mode="Markdown")
# ── أوامر الإدارة ──────────────────────────────────────────

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
        await update.message.reply_text(f"❌ تعذّر الحظر: {e}")
        return
    
    reason_text = f"\n📌 السبب: {reason}" if reason else ""
    duration_text = f"\n⏱️ المدة: {fmt_duration(duration)}" if duration else "\n⏱️ المدة: دائم"
    
    ban_msg = (
        f"⛔ تم حظر المستخدم\n"
        f"🆔 المعرف: `{user_id}`"
        f"{duration_text}{reason_text}"
    )
    
    await update.message.reply_text(ban_msg, parse_mode="Markdown")
    await db.log_event(chat_id, "ban", user_id=banner_id, target_id=user_id, detail=reason)
    
    admin_ids = await get_admin_ids(context.bot, chat_id)
    for admin_id in admin_ids:
        if admin_id != banner_id:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"📢 إشعار إداري:\n"
                    f"تم حظر المستخدم {user_id} بواسطة {banner_id}\n"
                    f"السبب: {reason or 'غير محدد'}"
                )
            except Exception:
                pass

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
    removed = await db.remove_ban(user_id, chat_id)
    
    try:
        await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
    except Exception as e:
        logger.warning("تعذّر رفع الحظر: %s", e)
    
    if removed:
        await update.message.reply_text(f"✅ تم رفع الحظر عن المستخدم {user_id}.")
        await db.log_event(chat_id, "unban", user_id=unbanner_id, target_id=user_id)
    else:
        await update.message.reply_text(f"ℹ️ المستخدم {user_id} غير موجود في قائمة الحظر.")
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
    reason_text = f"\n📌 السبب: {reason}" if reason else ""
    await db.log_event(chat_id, "warn", user_id=warner_id, target_id=user_id, detail=reason)
    
    if count >= MAX_WARNINGS:
        auto_reason = f"حظر تلقائي بعد {MAX_WARNINGS} تحذيرات"
        await db.add_ban(user_id, chat_id, auto_reason, warner_id)
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
        except Exception as e:
            logger.warning("تعذّر الحظر التلقائي: %s", e)
        await db.clear_warnings(user_id, chat_id)
        
        await update.message.reply_text(
            f"⛔ تم حظر المستخدم {user_id} تلقائياً!\n"
            f"📌 السبب: {auto_reason}{reason_text}\n"
            f"⚠️ عدد التحذيرات: {count}/{MAX_WARNINGS}"
        )
        
        admin_ids = await get_admin_ids(context.bot, chat_id)
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"🚨 حظر تلقائي!\n"
                    f"المستخدم: {user_id}\n"
                    f"السبب: {auto_reason}\n"
                    f"بواسطة: {warner_id}"
                )
            except Exception:
                pass
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
    count = await db.get_warning_count(user_id, chat_id)
    await update.message.reply_text(f"⚠️ عدد تحذيرات المستخدم {user_id}: {count}/{MAX_WARNINGS}")
async def cmd_banlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    bans = await db.list_bans(chat_id)
    if not bans:
        await update.message.reply_text("✅ لا يوجد محظورون حالياً.")
        return
    
    lines = []
    for b in bans[:20]:
        exp = f" (ينتهي {b['expires_at'][:10]})" if b.get('expires_at') else " (دائم)"
        reason = f" | {b.get('reason', 'غير محدد')}" if b.get('reason') else ""
        lines.append(f"• {b['user_id']}{exp}{reason}")
    
    await update.message.reply_text(f"📋 المحظورون ({len(bans)}):\n" + "\n".join(lines))

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
    ban = await db.get_ban_info(user_id, chat_id)
    if not ban:
        await update.message.reply_text(f"ℹ️ المستخدم {user_id} غير محظور.")
        return
    
    exp = ban['expires_at'][:10] if ban.get('expires_at') else "دائم"
    reason = ban.get('reason') or 'غير محدد'
    banned_by = ban.get('banned_by', 'غير معروف')
    
    await update.message.reply_text(
        f"📋 معلومات الحظر:\n"
        f"🆔 المعرف: {user_id}\n"
        f"📌 السبب: {reason}\n"
        f"⏱️ ينتهي: {exp}\n"
        f"👤 حظره: {banned_by}"
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
    ban = await db.get_ban_info(user_id, chat_id)
    if ban:
        reason = ban.get('reason') or 'غير محدد'
        exp = ban['expires_at'][:10] if ban.get('expires_at') else "دائم"
        await update.message.reply_text(
            f"⛔ المستخدم {user_id} محظور.\n"
            f"📌 السبب: {reason}\n"
            f"⏱️ ينتهي: {exp}"
        )
    else:
        await update.message.reply_text(f"✅ المستخدم {user_id} غير محظور.")

async def cmd_eventlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    limit = int(context.args[0]) if context.args and context.args[0].isdigit() else 10
    events = await db.get_event_log(chat_id, limit)
    if not events:
        await update.message.reply_text("لا توجد أحداث مسجلة.")
        return
    
    lines = []
    for e in events:
        detail = f" | {e.get('detail', '')}" if e.get('detail') else ""
        lines.append(f"• {e['event_type']} — {e['created_at'][:16]}{detail}")
    
    await update.message.reply_text(f"📋 سجل الأحداث ({len(events)}):\n" + "\n".join(lines))
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
    chat_id = update.effective_chat.id
    rules = await db.get_setting(chat_id, "rules")
    if rules:
        await update.message.reply_text(f"📋 قواعد المجموعة:\n{rules}")
    else:
        await update.message.reply_text("ℹ️ لم يتم تعيين قواعد بعد.\n"
                                       "المشرفين يقدرون يضيفونها بـ: /setrules <القواعد>")

# ── فلتر الكلمات ──────────────────────────────────────────

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
        await update.message.reply_text(f"ℹ️ الكلمة '{word}' موجودة مسبقاً.")

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
        await update.message.reply_text(f"ℹ️ الكلمة '{word}' غير موجودة.")

async def cmd_list_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    words = await db.get_banned_words(chat_id)
    if not words:
        await update.message.reply_text("لا توجد كلمات محظورة.")
        return
    await update.message.reply_text("📋 الكلمات المحظورة:\n" + "\n".join(f"• {w}" for w in words))

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
                auto_reason = f"حظر تلقائي بعد {MAX_WARNINGS} تحذيرات (كلمة محظورة)"
                await db.add_ban(user.id, chat_id, auto_reason, 0)
                try:
                    await context.bot.ban_chat_member(chat_id, user.id)
                except Exception:
                    pass
                await db.clear_warnings(user.id, chat_id)
                await context.bot.send_message(
                    chat_id,
                    f"⛔ تم حظر {user.full_name} تلقائياً!\n"
                    f"📌 السبب: {auto_reason}\n"
                    f"⚠️ عدد التحذيرات: {count}/{MAX_WARNINGS}"
                )
            else:
                await context.bot.send_message(
                    chat_id,
                    f"⚠️ {user.full_name}، رسالتك تحتوي كلمات غير لائقة.\n"
                    f"التحذير {count}/{MAX_WARNINGS}"
                )
            return
# ── كتم وقفل ────────────────────────────────────────────────

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
# ── الترحيب والأعضاء ───────────────────────────────────────

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
            ban = await db.get_ban_info(user.id, chat_id)
            if ban:
                reason = ban.get('reason') or 'غير محدد'
                exp = ban['expires_at'][:10] if ban.get('expires_at') else "دائم"
                
                try:
                    await context.bot.ban_chat_member(chat_id, user.id)
                    await context.bot.send_message(
                        chat_id,
                        f"⛔ تم طرد عضو محظور تلقائياً!\n"
                        f"🆔 المعرف: {user.id}\n"
                        f"👤 الاسم: {user.full_name}\n"
                        f"📌 سبب الحظر السابق: {reason}\n"
                        f"⏱️ ينتهي: {exp}"
                    )
                except Exception as e:
                    logger.warning("تعذّر طرد المستخدم المحظور: %s", e)
                
                admin_ids = await get_admin_ids(context.bot, chat_id)
                for admin_id in admin_ids:
                    try:
                        await context.bot.send_message(
                            admin_id,
                            f"🚨 تنبيه أمني!\n"
                            f"عضو محظور حاول الدخول:\n"
                            f"🆔 المعرف: {user.id}\n"
                            f"👤 الاسم: {user.full_name}\n"
                            f"📌 سبب الحظر السابق: {reason}\n"
                            f"⏱️ ينتهي: {exp}\n"
                            f"✅ تم طرده تلقائياً."
                        )
                    except Exception:
                        pass
            else:
                welcome_text = (
                    f"👋 أهلاً وسهلاً {user.first_name}!\n\n"
                    f"🆔 معرفك: `{user.id}`\n"
                    f"📅 تاريخ التسجيل: {estimate_telegram_registration(user.id)}\n\n"
                    f"نرحب بك في مجموعتنا. يرجى الالتزام بالقواعد واحترام الجميع. 😊"
                )
                
                try:
                    if user.photo:
                        photo_file = await user.photo[-1].get_file()
                        await context.bot.send_photo(
                            chat_id,
                            photo=photo_file.file_id,
                            caption=welcome_text,
                            parse_mode="Markdown"
                        )
                    else:
                        await context.bot.send_message(
                            chat_id,
                            welcome_text,
                            parse_mode="Markdown"
                        )
                except Exception:
                    pass

async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    from telegram import Chat as TGChat
    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return
    await db.increment_message_count(update.effective_user.id, update.effective_chat.id)
    try:
        await db.add_chat(update.effective_chat.id)
    except:
        pass
# ── التقارير والإحصائيات ───────────────────────────────────

async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    
    chat_id = update.effective_chat.id
    
    bans = await db.list_bans(chat_id)
    warnings = await db.get_all_warnings(chat_id)
    message_stats = await db.get_message_stats(chat_id, days=7)
    top_users = await db.get_top_users(chat_id, limit=5)
    
    report = (
        f"📊 تقرير المجموعة\n"
        f"{'='*30}\n\n"
        f"⛔ المحظورون: {len(bans)}\n"
        f"⚠️ إجمالي التحذيرات: {warnings}\n"
        f"💬 الرسائل (7 أيام): {message_stats}\n\n"
        f"🏆 أكثر الأعضاء نشاطاً:\n"
    )
    
    for i, (user_id, count) in enumerate(top_users, 1):
        report += f"{i}. المستخدم {user_id}: {count} رسالة\n"
    
    await update.message.reply_text(report)

async def cmd_weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    
    chat_id = update.effective_chat.id
    admin_group_id = await db.get_setting(chat_id, "admin_group_id")
    if not admin_group_id:
        await update.message.reply_text(
            "⚠️ لم يتم تعيين قروب المشرفين.\n"
            "الاستخدام: /setadmingroup <معرف القروب>"
        )
        return
    
    try:
        admin_group_id = int(admin_group_id)
    except ValueError:
        await update.message.reply_text("❌ معرف قروب المشرفين غير صالح.")
        return
    
    report = await generate_full_report(chat_id, days=7)
    
    try:
        await context.bot.send_message(admin_group_id, report)
        await update.message.reply_text("✅ تم إرسال التقرير الأسبوعي لقروب المشرفين.")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل إرسال التقرير: {e}")

async def cmd_daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    
    chat_id = update.effective_chat.id
    report = await generate_bot_actions_report(chat_id, days=1)
    await update.message.reply_text(report)

async def generate_bot_actions_report(chat_id, days=1):
    events = await db.get_bot_events(chat_id, days=days)
    
    auto_bans = [e for e in events if e['event_type'] == 'auto_ban']
    word_filters = [e for e in events if e['event_type'] == 'word_filter']
    expired_bans = [e for e in events if e['event_type'] == 'expired_ban']
    welcome_count = len([e for e in events if e['event_type'] == 'welcome'])
    
    report = (
        f"🤖 تقرير تصرفات البوت (آخر {days} يوم)\n"
        f"{'='*40}\n\n"
        f"⛔ الحظر التلقائي: {len(auto_bans)}\n"
    )
    
    if auto_bans:
        report += "\n📋 تفاصيل الحظر التلقائي:\n"
        for e in auto_bans[:10]:
            detail = e.get('detail', 'غير محدد')
            time = e['created_at'][:16]
            report += f"• {time} | {detail}\n"
    
    report += (
        f"\n🚫 فلتر الكلمات: {len(word_filters)}\n"
        f"✅ انتهاء حظر: {len(expired_bans)}\n"
        f"👋 ترحيب أعضاء: {welcome_count}\n"
    )
    
    return report

async def generate_full_report(chat_id, days=7):
    bans = await db.list_bans(chat_id)
    new_bans = await db.get_new_bans(chat_id, days=days)
    warnings = await db.get_all_warnings(chat_id)
    message_stats = await db.get_message_stats(chat_id, days=days)
    top_users = await db.get_top_users(chat_id, limit=10)
    events = await db.get_event_log(chat_id, limit=20)
    
    report = (
        f"📊 التقرير الأسبوعي\n"
        f"📅 الفترة: آخر {days} أيام\n"
        f"{'='*40}\n\n"
        f"⛔ المحظورون الحاليون: {len(bans)}\n"
        f"🆕 محظورون جدد: {len(new_bans)}\n"
        f"⚠️ إجمالي التحذيرات: {warnings}\n"
        f"💬 إجمالي الرسائل: {message_stats}\n\n"
        f"🏆 أكثر 10 أعضاء نشاطاً:\n"
    )
    
    for i, (user_id, count) in enumerate(top_users, 1):
        report += f"{i}. المستخدم {user_id}: {count} رسالة\n"
    
    report += "\n📋 آخر 20 حدث:\n"
    for e in events[:20]:
        detail = f" | {e.get('detail', '')}" if e.get('detail') else ""
        report += f"• {e['event_type']} — {e['created_at'][:16]}{detail}\n"
    
    return report

async def cmd_setadmingroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: /setadmingroup <معرف القروب>")
        return
    
    try:
        group_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ معرف غير صالح.")
        return
    
    chat_id = update.effective_chat.id
    await db.set_setting(chat_id, "admin_group_id", str(group_id))
    await update.message.reply_text(f"✅ تم تعيين قروب المشرفين: {group_id}")
# ── الألعاب - لعبة التركيز فقط ─────────────────────────────

_focus_games = {}

async def cmd_focus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    import random
    
    challenges = [
        ("🧮 احسب: 15 + 27 = ?", "42"),
        ("🧮 احسب: 8 × 7 = ?", "56"),
        ("🧮 احسب: 100 - 37 = ?", "63"),
        ("🔤 أكمل: أ ب ت _", "ث"),
        ("🎯 ما هو لون السماء؟", "أزرق"),
        ("🌍 كم عدد أيام الأسبوع؟", "7"),
        ("⏰ كم عدد ساعات اليوم؟", "24"),
        ("🧮 احسب: 9 × 9 = ?", "81"),
        ("🔤 أكمل: د ج ح _", "خ"),
        ("🌍 كم قارة في العالم؟", "7"),
    ]
    
    challenge, answer = random.choice(challenges)
    
    _focus_games[(chat_id, user.id)] = {
        "answer": answer,
        "start_time": datetime.now(timezone.utc),
        "answered": False
    }
    
    await update.message.reply_text(
        f"🎮 لعبة التركيز!\n"
        f"{'='*20}\n"
        f"{challenge}\n\n"
        f"⏱️ أجب بأسرع وقت!"
    )

async def check_focus_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    msg = update.message
    
    if not msg or not msg.text:
        return
    
    key = (chat_id, user.id)
    if key not in _focus_games:
        return
    
    game = _focus_games[key]
    if game["answered"]:
        return
    
    user_answer = msg.text.strip()
    correct_answer = game["answer"]
    
    if user_answer == correct_answer:
        game["answered"] = True
        elapsed = (datetime.now(timezone.utc) - game["start_time"]).total_seconds()
        
        await db.add_game_score(user.id, chat_id, "focus", int(elapsed))
        
        await msg.reply_text(
            f"🎉 إجابة صحيحة!\n"
            f"⏱️ وقتك: {elapsed:.2f} ثانية\n"
            f"🏆 أحسنت!"
        )
        del _focus_games[key]
    else:
        await msg.reply_text("❌ إجابة خاطئة! حاول مرة أخرى.")

async def cmd_gamescore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    scores = await db.get_game_scores(user.id, chat_id)
    
    if not scores:
        await update.message.reply_text("🎮 لم تلعب أي لعبة بعد.\nجرب: /تركيز")
        return
    
    text = f"🏆 نقاطك في الألعاب:\n{'='*20}\n"
    for game_type, score, count in scores:
        emoji = "🧮" if game_type == "focus" else "🎮"
        text += f"{emoji} {game_type}: {score} نقطة ({count} مرة)\n"
    
    await update.message.reply_text(text)

# ── مهمة انتهاء الحظر ──────────────────────────────────────

async def job_expire_bans(context: ContextTypes.DEFAULT_TYPE):
    expired = await db.get_expired_bans()
    for ban in expired:
        user_id = ban["user_id"]
        chat_id = ban["chat_id"]
        reason = ban.get('reason', 'غير محدد')
        
        await db.remove_ban(user_id, chat_id)
        try:
            await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
            await context.bot.send_message(
                chat_id,
                f"✅ انتهت مدة حظر المستخدم {user_id}.\n"
                f"📌 السبب السابق: {reason}\n"
                f"يمكنه الانضمام مجدداً."
            )
            await db.log_event(chat_id, "expired_ban", target_id=user_id, detail=reason)
        except Exception as e:
            logger.warning("خطأ في رفع حظر المستخدم %s: %s", user_id, e)

# ── مهمة التقرير اليومي ────────────────────────────────────

async def job_daily_report(context: ContextTypes.DEFAULT_TYPE):
    try:
        chats = await db.get_all_chats()
        for chat_id in chats:
            admin_group_id = await db.get_setting(chat_id, "admin_group_id")
            if not admin_group_id:
                continue
            
            try:
                admin_group_id = int(admin_group_id)
            except ValueError:
                continue
            
            report = await generate_bot_actions_report(chat_id, days=1)
            
            try:
                await context.bot.send_message(admin_group_id, report)
            except Exception as e:
                logger.warning("فشل إرسال التقرير اليومي للمجموعة %s: %s", chat_id, e)
    except Exception as e:
        logger.error("خطأ في إرسال التقارير اليومية: %s", e)

# ── ردود تلقائية وتفاعل ──────────────────────────────────────────

AUTO_REPLIES = {
    "صباح الخير": ["صباح النور ☀️", "صباح الورد 🌹", "صباحك أجمل"],
    "مساء الخير": ["مساء النور 🌙", "مساء الورد"],
    "هلا": ["هلا والله", "أهلين", "مرحباً"],
    "شلونك": ["بخير الحمدلله", "تمام وأنت؟"],
}

async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    
    text = msg.text.strip().lower()
    
    # ردود تلقائية بناءً على الكلمات المفتاحية
    for keyword, replies in AUTO_REPLIES.items():
        if keyword in text:
            import random
            await msg.reply_text(random.choice(replies))
            return
    
    # رد ذكي بسيط عند ذكر اسم البوت (Tag)
    bot_user = await context.bot.get_me()
    if bot_user.username and f"@{bot_user.username.lower()}" in text:
        await msg.reply_text("هلا! كيف أقدر أساعدك؟ 😊")
