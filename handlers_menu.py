import logging
import random
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
from helpers import require_admin, is_admin

logger = logging.getLogger(__name__)

# ================================================
# القائمة الرئيسية
# ================================================
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("👮 أوامر المشرفين", callback_data="menu_admin"),
            InlineKeyboardButton("👥 للجميع",         callback_data="menu_user"),
        ],
        [
            InlineKeyboardButton("🎵 الميديا",        callback_data="menu_media"),
            InlineKeyboardButton("📚 الموارد",        callback_data="menu_resources"),
        ],
        [
            InlineKeyboardButton("📊 إحصائيات",       callback_data="exec_stats"),
            InlineKeyboardButton("💬 اقتباس اليوم",   callback_data="exec_quote"),
        ],
        [
            InlineKeyboardButton("❓ المساعدة",       callback_data="menu_help"),
            InlineKeyboardButton("📞 تواصل",          callback_data="menu_contact"),
        ],
        [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
    ]
    await update.message.reply_text(
        "🌅 بوت شفق — القائمة الرئيسية\nاختر القسم:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================================================
# معالج الأزرار
# ================================================
async def callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── إغلاق القائمة ──────────────────────────
    if data == "menu_close":
        await query.message.delete()
        return

    # ── إحصائيات المجموعة ──────────────────────
    if data == "exec_stats":
        chat_id = update.effective_chat.id
        try:
            members_count = await context.bot.get_chat_member_count(chat_id)
            admins = await context.bot.get_chat_administrators(chat_id)
            admins_count = len(admins)
            text = f"📊 إحصائيات المجموعة:\n👥 الأعضاء: {members_count}\n👮 المشرفون: {admins_count}"
        except:
            text = "📊 لا يمكن جلب الإحصائيات حالياً."
        await query.message.reply_text(text)
        return

    # ── اقتباس اليوم ───────────────────────────
    if data == "exec_quote":
        quotes = [
            "🌟 لا تؤجل عمل اليوم إلى الغد.",
            "💪 النجاح ليس حكراً على أحد، جربه بإصرار.",
            "🧠 تعلم شيئاً جديداً كل يوم.",
            "😊 ابتسم فأنت بخير.",
            "⭐ الحياة قصيرة، عشها بفرح.",
            "📖 المعرفة نور والجهل ظلام.",
            "🤝 كن لطيفاً مع الجميع."
        ]
        quote = random.choice(quotes)
        await query.message.reply_text(f"💬 اقتباس اليوم:\n\n{quote}")
        return

    # ── المساعدة ───────────────────────────────
    if data == "menu_help":
        help_text = (
            "❓ **أوامر البوت**\n\n"
            "/start - إظهار القائمة\n"
            "/id - معرفك\n"
            "/rules - عرض القواعد\n"
            "/report - تقرير للمشرفين\n"
            "/ban @username - حظر\n"
            "/unban @username - رفع الحظر\n"
            "/mute @username - كتم\n"
            "/unmute @username - رفع الكتم\n"
            "يمكنك استخدام الأزرار للتنقل."
        )
        await query.message.reply_text(help_text, parse_mode="Markdown")
        return

    # ── تواصل مع المطور (تم تعديل الرابط) ───────
    if data == "menu_contact":
        contact_text = "📞 **تواصل مع المطور:**\n[اضغط هنا](https://t.me/Me8dad)\nأو راسلني مباشرة."
        await query.message.reply_text(contact_text, parse_mode="Markdown", disable_web_page_preview=True)
        return

    # ── القائمة الرئيسية ──────────────────────
    if data == "menu_main":
        keyboard = [
            [
                InlineKeyboardButton("👮 أوامر المشرفين", callback_data="menu_admin"),
                InlineKeyboardButton("👥 للجميع",         callback_data="menu_user"),
            ],
            [
                InlineKeyboardButton("🎵 الميديا",        callback_data="menu_media"),
                InlineKeyboardButton("📚 الموارد",        callback_data="menu_resources"),
            ],
            [
                InlineKeyboardButton("📊 إحصائيات",       callback_data="exec_stats"),
                InlineKeyboardButton("💬 اقتباس اليوم",   callback_data="exec_quote"),
            ],
            [
                InlineKeyboardButton("❓ المساعدة",       callback_data="menu_help"),
                InlineKeyboardButton("📞 تواصل",          callback_data="menu_contact"),
            ],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "🌅 بوت شفق — القائمة الرئيسية\nاختر القسم:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── أوامر المشرفين ────────────────────────
    elif data == "menu_admin":
        keyboard = [
            [
                InlineKeyboardButton("🚫 الحظر",      callback_data="menu_ban"),
                InlineKeyboardButton("⚠️ التحذيرات", callback_data="menu_warn"),
            ],
            [
                InlineKeyboardButton("🔇 الكتم",      callback_data="menu_mute"),
                InlineKeyboardButton("⚙️ الإدارة",   callback_data="menu_manage"),
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "👮 أوامر المشرفين — اختر القسم:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── قسم الحظر ────────────────────────────
    elif data == "menu_ban":
        keyboard = [
            [InlineKeyboardButton("📋 قائمة المحظورين", callback_data="exec_banlist")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "🚫 الحظر:\n"
            "• حظر — رد على عضو\n"
            "• حظر 123 7d سبب — حظر مؤقت\n"
            "• رفع الحظر — رد على عضو\n"
            "• تحقق — رد على عضو\n"
            "• معلومات — رد على عضو",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── قسم التحذيرات ─────────────────────────
    elif data == "menu_warn":
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "⚠️ التحذيرات:\n"
            "• تحذير — رد على عضو\n"
            "• مسح التحذير — رد على عضو\n"
            "• التحذيرات — رد على عضو\n\n"
            "ملاحظة: 3 تحذيرات = حظر تلقائي",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── قسم الكتم ────────────────────────────
    elif data == "menu_mute":
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "🔇 الكتم:\n"
            "• كتم — رد على عضو\n"
            "• كتم 123 1h — كتم مؤقت\n"
            "• رفع الكتم — رد على عضو",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── قسم الإدارة ───────────────────────────
    elif data == "menu_manage":
        keyboard = [
            [
                InlineKeyboardButton("🔒 أغلق المجموعة", callback_data="exec_lock"),
                InlineKeyboardButton("🔓 افتح المجموعة", callback_data="exec_unlock"),
            ],
            [
                InlineKeyboardButton("📋 سجل الأحداث",   callback_data="exec_eventlog"),
                InlineKeyboardButton("📊 تقرير فوري",    callback_data="exec_report"),
            ],
            [
                InlineKeyboardButton("🚫 الكلمات المحظورة", callback_data="exec_wordlist"),
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "⚙️ الإدارة — اختر أمراً:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── للجميع ───────────────────────────────
    elif data == "menu_user":
        keyboard = [
            [
                InlineKeyboardButton("🪪 معلوماتي",    callback_data="exec_id"),
                InlineKeyboardButton("📋 القواعد",     callback_data="exec_rules"),
            ],
            [
                InlineKeyboardButton("📚 الموارد",     callback_data="exec_resources"),
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "👥 للجميع — اختر أمراً:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── الميديا ──────────────────────────────
    elif data == "menu_media":
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "🎵 الميديا:\n"
            "• أرسل رابط يوتيوب / تيك توك / انستقرام مباشرة\n"
            "• يوتيوب <اسم الأغنية> — بحث",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── الموارد ──────────────────────────────
    elif data == "menu_resources":
        keyboard = [
            [InlineKeyboardButton("📖 عرض الموارد", callback_data="exec_resources")],
            [InlineKeyboardButton("🔙 رجوع",        callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "📚 الموارد:\n"
            "• الموارد — عرض القائمة\n"
            "• الموارد <كلمة> — بحث",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ================================================
    # تنفيذ الأوامر المباشرة
    # ================================================
    elif data == "exec_banlist":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        chat_id = update.effective_chat.id
        bans = await db.get_ban_list(chat_id)
        if not bans:
            await query.answer("لا يوجد محظورون حالياً ✅", show_alert=True)
            return
        lines = []
        for b in bans[:20]:
            exp = f" (ينتهي {b['expires_at'][:10]})" if b.get('expires_at') else " (دائم)"
            lines.append(f"• {b['user_id']}{exp}")
        await query.message.reply_text("🚫 المحظورون:\n" + "\n".join(lines))

    elif data == "exec_lock":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        from telegram import ChatPermissions
        chat_id = update.effective_chat.id
        try:
            await context.bot.set_chat_permissions(
                chat_id, permissions=ChatPermissions(can_send_messages=False)
            )
            await query.answer("🔒 تم إغلاق المجموعة", show_alert=True)
            await db.log_event(chat_id, "lock", user_id=update.effective_user.id)
        except Exception as e:
            await query.answer(f"❌ تعذّر الإغلاق", show_alert=True)

    elif data == "exec_unlock":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
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
                )
            )
            await query.answer("🔓 تم فتح المجموعة", show_alert=True)
            await db.log_event(chat_id, "unlock", user_id=update.effective_user.id)
        except Exception as e:
            await query.answer("❌ تعذّر الفتح", show_alert=True)

    elif data == "exec_eventlog":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        chat_id = update.effective_chat.id
        events = await db.get_event_log(chat_id, 10)
        if not events:
            await query.answer("لا توجد أحداث مسجلة", show_alert=True)
            return
        lines = [f"• {e['action']} — {e['created_at'][:16]}" for e in events]
        await query.message.reply_text("📋 سجل الأحداث:\n" + "\n".join(lines))

    elif data == "exec_report":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        context.args = []
        from handlers_jobs import cmd_report
        await cmd_report(update, context)

    elif data == "exec_wordlist":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        chat_id = update.effective_chat.id
        words = await db.get_banned_words(chat_id)
        if not words:
            await query.answer("لا توجد كلمات محظورة", show_alert=True)
            return
        await query.message.reply_text("🚫 الكلمات المحظورة:\n" + "\n".join(f"• {w}" for w in words))

    elif data == "exec_id":
        from handlers_user import cmd_id
        await cmd_id(update, context)

    elif data == "exec_rules":
        chat_id = update.effective_chat.id
        rules = await db.get_setting(chat_id, "rules")
        if rules:
            await query.message.reply_text(f"📋 قواعد المجموعة:\n{rules}")
        else:
            await query.answer("لم يتم تعيين قواعد بعد", show_alert=True)

    elif data == "exec_resources":
        chat_id = update.effective_chat.id
        from handlers_resources import _get_resources
        resources = await _get_resources(chat_id)
        if not resources:
            await query.answer("لا توجد موارد مضافة بعد", show_alert=True)
            return
        lines = []
        for i, r in enumerate(resources, 1):
            lines.append(f"{i}. 📌 {r['title']}\n   {r['content']}")
        await query.message.reply_text("📚 الموارد:\n\n" + "\n\n".join(lines))