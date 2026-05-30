import logging
import os
import random
import aiohttp
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
ADMIN_CHAT_ID = 729970974

AUTO_REPLIES = {
    "صباح الخير": ["صباح النور ☀️"],
    "صباح النور": ["صباح الورد 🌹"],
    "صباح الورد": ["صباح السعادة ☀️"],
    "مساء الخير": ["مساء النور 🌙"],
    "مساء النور": ["مساء الورد 🌹"],
    "مساء الورد": ["مساء السعادة 🌙"],
}

CRISIS_KEYWORDS = [
    "انتحار", "انتحرت", "أنتحر", "بنتحر", "بينتحر", "سأنتحر", "راح انتحر",
    "اقتل نفسي", "أقتل نفسي", "بقتل نفسي", "يقتل نفسه", "يقتل نفسي",
    "سأقتل نفسي", "أذيت", "أذيت نفسي", "اذيت نفسي", "أضر نفسي", "اضر نفسي",
    "أضر بنفسي", "أموت", "بموت", "ابي اموت", "أبي أموت", "ابغى اموت",
    "أبغى أموت", "ودي أموت", "اتمنى الموت", "اخنق نفسي", "أخنق نفسي",
    "suicide", "kill myself", "end my life", "want to die", "self harm",
]

CRISIS_REPLY = """
.يبدو أنك تمر بلحظة صعبة 🆘

أنت لست وحدك 🤍

📞 أرقام الدعم والمساعدة في السعودية:

- 937 - وزارة الصحة (استشارات ودعم صحي ونفسي)
- 920033360 - مركز الاستشارات والدعم النفسي
- 1919 - بلاغات العنف الأسري والحماية الاجتماعية
- 116111 - خط حماية الطفل
- 999 - الشرطة
- 997 - الهلال الأحمر (الإسعاف)
- 998 - الدفاع المدني
- 911 - الطوارئ العامة

أو تحدث مع احد المشرفين او الأعضاء ، نحن معك. 💙
"""

# ── Gemini ──────────────────────────────────────────────────────────────────
async def ask_gemini(question: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return "⚠️ مفتاح Gemini غير مضبوط في المتغيرات البيئية."
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": [{"text": question}]}]}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error("Gemini error %s: %s", resp.status, text)
                    return f"⚠️ خطأ من Gemini ({resp.status}). حاول مرة أخرى."
                data = await resp.json()
                answer = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                )
                return answer or "لم أتلقَّ إجابة من Gemini."
    except Exception as e:
        logger.error("Gemini request failed: %s", e)
        return "⚠️ تعذّر الاتصال بـ Gemini. حاول لاحقاً."

async def cmd_shafaq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = " ".join(context.args).strip() if context.args else ""
    if not question:
        await update.message.reply_text("اكتب سؤالك بعد كلمة شفق.\nمثال: شفق ما هو الذكاء الاصطناعي؟")
        return
    thinking_msg = await update.message.reply_text("✨ شفق تفكر...")
    answer = await ask_gemini(question)
    try:
        await thinking_msg.delete()
    except Exception:
        pass
    await update.message.reply_text(f"🌅 {answer}")
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "بوت شفق نشط ✅\n\n"
        "👮 أوامر المشرفين:\n"
        "حظر — حظر عضو (رد أو معرف)\n"
        "حظر 123 7d سبب — حظر مؤقت\n"
        "رفع الحظر — رفع الحظر\n"
        "تحذير — تحذير (3 = حظر تلقائي)\n"
        "مسح التحذير — مسح تحذيرات عضو\n"
        "التحذيرات — عدد تحذيرات عضو\n"
        "كتم — كتم عضو\n"
        "كتم 123 1h — كتم مؤقت\n"
        "رفع الكتم — رفع الكتم\n"
        "قائمة — المحظورون\n"
        "معلومات — تفاصيل الحظر\n"
        "تحقق — هل هو محظور؟\n"
        "سجل — آخر الأحداث\n"
        "تقرير — تقرير فوري\n"
        "إحصائيات — إحصائيات المجموعة (في الخاص)\n"
        "أضف كلمة — إضافة كلمة محظورة\n"
        "احذف كلمة — حذف كلمة\n"
        "الكلمات المحظورة — القائمة\n"
        "أغلق المجموعة — إغلاق\n"
        "افتح المجموعة — فتح\n"
        "/setrules — تعيين القواعد\n\n"
        "👥 للجميع:\n"
        "ايدي — معلوماتك + عدد رسائلك\n"
        "القواعد — قواعد المجموعة\n"
        "شفق <سؤال> — اسأل الذكاء الاصطناعي\n"
        "تذكير 20:00 نص — تذكير مرة واحدة (في الخاص)\n"
        "تذكير يومي 20:00 نص — تذكير يومي (في الخاص)\n\n"
        "🎵 الميديا:\n"
        "أرسل رابط مباشرة — تحميل\n\n"
        "🤖 تلقائي:\n"
        "طرد المحظورين تلقائياً\n"
        "حذف الكلمات المحظورة\n"
        "ترحيب بالأعضاء الجدد\n"
        "تقرير يومي وأسبوعي"
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
        username = f"@{reply_user.username}" if reply_user.username else "غير محدد"
        msg_count = await db.get_message_count(reply_user.id, chat.id)
        try:
            photos = await context.bot.get_user_profile_photos(reply_user.id, limit=1)
            if photos.total_count > 0:
                await update.message.reply_photo(
                    photo=photos.photos[0][-1].file_id,
                    caption=(
                        f"معلومات العضو:\n"
                        f"الاسم: {reply_user.first_name}\n"
                        f"اليوزر: {username}\n"
                        f"المعرف: {reply_user.id}\n"
                        f"عدد الرسائل: {msg_count} رسالة"
                    )
                )
                return
        except Exception:
            pass
        await update.message.reply_text(
            f"معلومات العضو:\n"
            f"الاسم: {reply_user.first_name}\n"
            f"اليوزر: {username}\n"
            f"المعرف: {reply_user.id}\n"
            f"عدد الرسائل: {msg_count} رسالة"
        )
    else:
        username = f"@{user.username}" if user.username else "غير محدد"
        msg_count = await db.get_message_count(user.id, chat.id)
        try:
            photos = await context.bot.get_user_profile_photos(user.id, limit=1)
            if photos.total_count > 0:
                await update.message.reply_photo(
                    photo=photos.photos[0][-1].file_id,
                    caption=(
                        f"معلوماتك:\n"
                        f"الاسم: {user.first_name}\n"
                        f"اليوزر: {username}\n"
                        f"المعرف: {user.id}\n"
                        f"عدد رسائلك: {msg_count} رسالة"
                    )
                )
                return
        except Exception:
            pass
        await update.message.reply_text(
            f"معلوماتك:\n"
            f"الاسم: {user.first_name}\n"
            f"اليوزر: {username}\n"
            f"المعرف: {user.id}\n"
            f"عدد رسائلك: {msg_count} رسالة"
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
    await update.message.reply_text(
        f"🚫 تم حظر المستخدم {user_id}.{duration_text}{reason_text}"
    )
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

async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    warner_id = update.effective_user.id
    reply_user = get_reply_user(update)
    if reply_user:
        user_id = reply_user.id
        user_name = reply_user.full_name
        reason = " ".join(context.args) if context.args else None
    elif context.args:
        try:
            user_id = int(context.args[0])
            user_name = str(user_id)
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
            f"⛔ تم حظر {user_name} ({user_id}) تلقائياً بعد {MAX_WARNINGS} تحذيرات.{reason_text}"
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
            f"⚠️ تحذير {count}/{MAX_WARNINGS} للعضو {user_name} ({user_id}).{reason_text}"
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
    await update.message.reply_text(
        f"عدد تحذيرات المستخدم {user_id}: {count}/{MAX_WARNINGS}"
    )

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

# ── سجل (محسّن: اسم + ايدي) ──────────────────────────────────────────────────
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
        uid = e.get('target_id') or e.get('user_id')
        name = await db.get_user_name(chat_id, uid) if uid else "—"
        lines.append(f"• {e['action']} | {name} ({uid}) — {e['created_at'][:16]}")
    await update.message.reply_text("📋 سجل الأحداث:\n" + "\n".join(lines))

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

async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    rules = await db.get_setting(chat_id, "rules")
    if rules:
        await update.message.reply_text(f"📋 قواعد المجموعة:\n{rules}")
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
    await update.message.reply_text(
        "🚫 الكلمات المحظورة:\n" + "\n".join(f"• {w}" for w in words)
    )

# ── إحصائيات (في الخاص) ──────────────────────────────────────────────────────
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import Chat as TGChat
    user = update.effective_user
    if update.effective_chat.type == TGChat.PRIVATE:
        chats = await db.get_all_active_chats()
        if not chats:
            await update.message.reply_text("لا توجد مجموعات مسجلة بعد.")
            return
        for chat_id in chats:
            total = await db.get_total_members(chat_id)
            bans = await db.get_ban_list(chat_id)
            chat_name = await db.get_chat_name(chat_id)
            top = await db.get_top_members(chat_id, 3)
            top_text = ""
            for i, m in enumerate(top, 1):
                name = await db.get_user_name(chat_id, m['user_id'])
                top_text += f"  {i}. \u200F{name} — {m['message_count']} رسالة\n"
            msg = (
                f"📊 إحصائيات — {chat_name}\n"
                f"{'━'*20}\n"
                f"👥 الأعضاء: {total}\n"
                f"🚫 المحظورون: {len(bans)}\n"
                f"{'━'*20}\n"
                f"🏆 الأكثر نشاطاً:\n{top_text or 'لا توجد بيانات'}"
            )
            await update.message.reply_text(msg)
    else:
        if not await require_admin(update, context):
            return
        chat_id = update.effective_chat.id
        total = await db.get_total_members(chat_id)
        bans = await db.get_ban_list(chat_id)
        chat_name = await db.get_chat_name(chat_id)
        top = await db.get_top_members(chat_id, 3)
        top_text = ""
        for i, m in enumerate(top, 1):
            name = await db.get_user_name(chat_id, m['user_id'])
            top_text += f"  {i}. \u200F{name} — {m['message_count']} رسالة\n"
        msg = (
            f"📊 إحصائيات — {chat_name}\n"
            f"{'━'*20}\n"
            f"👥 الأعضاء: {total}\n"
            f"🚫 المحظورون: {len(bans)}\n"
            f"{'━'*20}\n"
            f"🏆 الأكثر نشاطاً:\n{top_text or 'لا توجد بيانات'}"
        )
        try:
            await context.bot.send_message(user.id, msg)
            await update.message.reply_text("✅ تم إرسال الإحصائيات في الخاص.")
        except Exception:
            await update.message.reply_text("❌ فعّل محادثة الخاص مع البوت أولاً.")

# ── تذكير (في الخاص) ─────────────────────────────────────────────────────────
async def cmd_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import Chat as TGChat
    if update.effective_chat.type != TGChat.PRIVATE:
        await update.message.reply_text("أمر التذكير يعمل في الخاص فقط.")
        return
    args = context.args
    # تذكير يومي 20:00 النص
    # تذكير 20:00 النص
    if not args or len(args) < 2:
        await update.message.reply_text(
            "الاستخدام:\n"
            "تذكير 20:00 نص الرسالة\n"
            "تذكير يومي 20:00 نص الرسالة"
        )
        return
    daily = False
    if args[0] == "يومي":
        daily = True
        args = args[1:]
    time_str = args[0]
    text = " ".join(args[1:])
    if not text:
        await update.message.reply_text("اكتب نص التذكير بعد الوقت.")
        return
    try:
        hour, minute = map(int, time_str.split(":"))
        assert 0 <= hour <= 23 and 0 <= minute <= 59
    except Exception:
        await update.message.reply_text("صيغة الوقت خاطئة. استخدم مثلاً: 20:00")
        return
    user_id = update.effective_user.id
    if daily:
        context.job_queue.run_daily(
            _send_reminder,
            time=datetime.now(timezone.utc).replace(hour=hour, minute=minute, second=0, microsecond=0).timetz(),
            chat_id=user_id,
            name=f"reminder_{user_id}_{hour}_{minute}",
            data=text,
        )
        await update.message.reply_text(f"✅ تم ضبط تذكير يومي الساعة {time_str}:\n{text}")
    else:
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        delay = (target - now).total_seconds()
        context.job_queue.run_once(
            _send_reminder,
            when=delay,
            chat_id=user_id,
            name=f"reminder_{user_id}_{hour}_{minute}",
            data=text,
        )
        await update.message.reply_text(f"✅ تم ضبط تذكير الساعة {time_str}:\n{text}")

async def _send_reminder(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=f"🔔 تذكير:\n{context.job.data}"
    )

# ── تقرير (محسّن: كل الأعضاء + اسم في الإجراءات) ────────────────────────────
async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import timedelta
    from telegram import Chat as TGChat
    is_private = update.effective_chat.type == TGChat.PRIVATE
    if not is_private:
        if not await require_admin(update, context):
            return
        if update.effective_user.id != ADMIN_CHAT_ID:
            await update.message.reply_text("غير مصرح لك.")
            return
    if is_private:
        chats = await db.get_all_active_chats()
        if not chats:
            await update.message.reply_text("لا توجد مجموعات مسجلة بعد.")
            return
        for chat_id in chats:
            now = datetime.now(timezone.utc)
            day_ago = (now - timedelta(days=1)).isoformat()
            actions = await db.get_bot_actions_since(chat_id, day_ago)
            bans = await db.get_ban_list(chat_id)
            top = await db.get_top_members(chat_id, 999)
            chat_name = await db.get_chat_name(chat_id)
            lines = []
            for a in actions[:10]:
                name = await db.get_user_name(chat_id, a['user_id'])
                detail = f" — {a['detail']}" if a.get('detail') else ""
                lines.append(f"• {a['action']} | \u202B{name}\u202C ({a['user_id']}){detail}")
            top_text = ""
            for i, m in enumerate(top, 1):
                name = await db.get_user_name(chat_id, m['user_id'])
                top_text += f"{i}. \u202B{name}\u202C — {m['message_count']} رسالة\n"
            report = (
                f"📊 تقرير — {chat_name}\n"
                f"{'━'*20}\n"
                f"🚫 محظورون: {len(bans)}\n"
                f"{'━'*20}\n"
                f"📋 آخر الإجراءات:\n"
                + ("\n".join(lines) if lines else "لا توجد إجراءات") +
                f"\n{'━'*20}\n"
                f"🏆 الأعضاء حسب النشاط:\n{top_text}"
            )
            await update.message.reply_text(report)
    else:
        now = datetime.now(timezone.utc)
        day_ago = (now - timedelta(days=1)).isoformat()
        chat_id = update.effective_chat.id
        actions = await db.get_bot_actions_since(chat_id, day_ago)
        bans = await db.get_ban_list(chat_id)
        top = await db.get_top_members(chat_id, 999)
        lines = []
        for a in actions[:20]:
            name = await db.get_user_name(chat_id, a['user_id'])
            detail = f" — {a['detail']}" if a.get('detail') else ""
            lines.append(f"• {a['action']} | \u202B{name}\u202C ({a['user_id']}){detail}")
        top_text = ""
        for i, m in enumerate(top, 1):
            name = await db.get_user_name(chat_id, m['user_id'])
            top_text += f"{i}. \u202B{name}\u202C — {m['message_count']} رسالة\n"
        report = (
            f"📊 تقرير المجموعة\n"
            f"{'━'*20}\n"
            f"🚫 محظورون: {len(bans)}\n"
            f"{'━'*20}\n"
            f"📋 آخر الإجراءات:\n"
            + ("\n".join(lines) if lines else "لا توجد إجراءات") +
            f"\n{'━'*20}\n"
            f"🏆 الأعضاء حسب النشاط:\n{top_text}"
        )
        await update.message.reply_text(report)
async def filter_banned_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    from telegram import Chat as TGChat
    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return
    chat_id = update.effective_chat.id
    user = update.effective_user
    text = msg.text.lower()
    for keyword in CRISIS_KEYWORDS:
        if keyword.lower() in text:
            try:
                await msg.reply_text(CRISIS_REPLY)
            except Exception as e:
                logger.error("خطأ في إرسال رسالة الأزمة: %s", e)
            return
    if await is_admin(update, context):
        return
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
                await db.log_bot_action(chat_id, "auto_ban_word", user_id=user.id, detail=word)
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

async def job_weekly_report(context: ContextTypes.DEFAULT_TYPE):
    chats = await db.get_all_active_chats()
    for chat_id in chats:
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        week_ago = (now - timedelta(days=7)).isoformat()
        total = await db.get_total_members(chat_id)
        new_members = await db.get_new_members_since(chat_id, week_ago)
        bans = await db.get_ban_list(chat_id)
        top = await db.get_top_members(chat_id, 5)
        chat_name = await db.get_chat_name(chat_id)
        top_text = ""
        for i, m in enumerate(top, 1):
            name = await db.get_user_name(chat_id, m['user_id'])
            top_text += f"{i}. {name} ({m['user_id']}) — {m['message_count']} رسالة\n"
        report = (
            f"📊 التقرير الأسبوعي — {chat_name}\n"
            f"{'─'*20}\n"
            f"👥 إجمالي الأعضاء: {total}\n"
            f"🆕 أعضاء جدد: {new_members}\n"
            f"🚫 محظورون: {len(bans)}\n"
            f"{'─'*20}\n"
            f"🏆 الأكثر نشاطاً:\n{top_text}"
        )
        try:
            await context.bot.send_message(ADMIN_CHAT_ID, report)
        except Exception:
            pass

async def job_daily_report(context: ContextTypes.DEFAULT_TYPE):
    chats = await db.get_all_active_chats()
    for chat_id in chats:
        now = datetime.now(timezone.utc)
        day_ago = now.replace(hour=0, minute=0, second=0).isoformat()
        actions = await db.get_bot_actions_since(chat_id, day_ago)
        if not actions:
            continue
        lines = []
        for a in actions[:20]:
            lines.append(f"• {a['action']} — المستخدم {a['user_id']}")
        report = (
            f"📋 التقرير اليومي\n"
            f"{'─'*20}\n"
            f"إجمالي الإجراءات: {len(actions)}\n\n"
            + "\n".join(lines)
        )
        try:
            await context.bot.send_message(ADMIN_CHAT_ID, report)
        except Exception:
            pass

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
                except Exception as e:
                    logger.warning("تعذّر طرد المحظور: %s", e)
                reason = ban.get('reason') or 'لم يُحدد سبب'
                await context.bot.send_message(chat_id, f"⚠️ تم طرد عضو محظور تلقائياً.")
                try:
                    await context.bot.send_message(
                        ADMIN_CHAT_ID,
                        f"⚠️ تنبيه!\n{user.full_name} ({user.id}) حاول الدخول وهو محظور.\nسبب الحظر: {reason}\nتم طرده تلقائياً. 🚫"
                    )
                except Exception:
                    pass
                await db.log_bot_action(chat_id, "auto_kick_banned", user_id=user.id, detail=reason)
            else:
                try:
                    photos = await context.bot.get_user_profile_photos(user.id, limit=1)
                    username = f"@{user.username}" if user.username else "بدون يوزر"
                    welcome = (
                        f"👋 أهلاً وسهلاً {user.first_name}!\n"
                        f"اليوزر: {username}\n"
                        f"نرحب بك في مجموعتنا. 😊\n"
                        f"يرجى الالتزام بالقواعد واحترام الجميع."
                    )
                    if photos.total_count > 0:
                        await context.bot.send_photo(chat_id, photo=photos.photos[0][-1].file_id, caption=welcome)
                    else:
                        await context.bot.send_message(chat_id, welcome)
                except Exception:
                    await context.bot.send_message(chat_id, f"👋 أهلاً {user.first_name}! نرحب بك في مجموعتنا. 😊")

async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    from telegram import Chat as TGChat
    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return
    text = msg.text.strip()
    for keyword, replies in AUTO_REPLIES.items():
        if keyword in text:
            await msg.reply_text(random.choice(replies))
            return
    if context.bot.username and f"@{context.bot.username.lower()}" in text.lower():
        await msg.reply_text("هلا! كيف أقدر أساعدك؟ 😊")

async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    from telegram import Chat as TGChat
    if update.effective_chat.type not in (TGChat.GROUP, TGChat.SUPERGROUP):
        return
    user = update.effective_user
    chat = update.effective_chat
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    await db.increment_message_count(user.id, chat.id, full_name)
    await db.save_chat_name(chat.id, chat.title or str(chat.id))

async def job_expire_bans(context: ContextTypes.DEFAULT_TYPE):
    expired = await db.get_expired_bans()
    for ban in expired:
        user_id = ban["user_id"]
        chat_id = ban["chat_id"]
        await db.remove_ban(user_id, chat_id)
        try:
            await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
            await context.bot.send_message(chat_id, f"انتهت مدة حظر المستخدم {user_id}. يمكنه الانضمام مجدداً.")
            await context.bot.send_message(user_id, "✅ انتهت مدة حظرك. يمكنك الانضمام للمجموعة مجدداً.")
        except Exception as e:
            logger.warning("خطأ في رفع الحظر: %s", e)