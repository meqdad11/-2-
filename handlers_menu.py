import logging
import random
import datetime
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes
import database as db
from helpers import require_admin, is_admin

logger = logging.getLogger(__name__)

# متغيرات مؤقتة لتخزين الهدية والنقاط (للتجربة)
temp_points = {}
temp_games = {}

# ================================================
# دوال مساعدة
# ================================================
async def is_admin_group(update: Update, user_id: int) -> bool:
    chat_id = update.effective_chat.id
    try:
        member = await update.effective_chat.get_member(user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

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
        [
            InlineKeyboardButton("🎮 ألعاب",          callback_data="menu_games"),
            InlineKeyboardButton("🔍 بحث جوجل",       callback_data="menu_google"),
        ],
        [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
    ]
    await update.message.reply_text(
        "🌅 بوت شفق — القائمة الرئيسية\nاختر القسم:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================================================
# معالج الأزرار الرئيسي
# ================================================
async def callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    # تأكد من وجود message في update (للاستدعاءات اللي تحتاج update.message)
    if not hasattr(update, 'message') or update.message is None:
        update.message = query.message

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

    # ── تواصل مع المطور ────────────────────────
    if data == "menu_contact":
        contact_text = "📞 **تواصل مع المطور:**\n[اضغط هنا](https://t.me/Me8dad)\nأو راسلني مباشرة."
        await query.message.reply_text(contact_text, parse_mode="Markdown", disable_web_page_preview=True)
        return

    # ── قائمة الألعاب ──────────────────────────
    if data == "menu_games":
        keyboard = [
            [InlineKeyboardButton("🎲 تخمين رقم (1-10)", callback_data="game_guess")],
            [InlineKeyboardButton("✂️ حجر ورقة مقص", callback_data="game_rps")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text("🎮 **اختر لعبة:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    # ── لعبة تخمين الرقم ───────────────────────
    if data == "game_guess":
        number = random.randint(1, 10)
        temp_games[user.id] = {'game': 'guess', 'number': number}
        await query.message.reply_text(f"🎲 **خمن الرقم بين 1 و 10**\nأرسل رقمًا:", parse_mode="Markdown")
        # سنقوم بمعالجة الرسالة التالية لهذا المستخدم - لكننا لا نضيف معالج هنا.
        # لهذا سنضيف معالج رسائل مؤقت (سيتم شرحه لاحقًا). ولكن لتسهيل الأمور، سنجعل اللعبة تفاعلية عبر الأزرار.
        # بدلاً من ذلك، سنضيف أزرار أرقام:
        keyboard = [[InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(1,6)],
                    [InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(6,11)]]
        await query.message.reply_text("اختر رقمًا:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("guess_"):
        guessed = int(data.split("_")[1])
        if user.id not in temp_games or temp_games[user.id].get('game') != 'guess':
            await query.answer("ابدأ لعبة جديدة من القائمة أولاً", show_alert=True)
            return
        correct = temp_games[user.id]['number']
        if guessed == correct:
            await query.message.reply_text(f"🎉 **صحيح!** الرقم كان {correct}. تهانينا!")
            del temp_games[user.id]
        else:
            await query.message.reply_text(f"❌ خطأ! الرقم {guessed} ليس صحيحًا. حاول مرة أخرى.")
        return

    # ── لعبة حجر ورقة مقص ─────────────────────
    if data == "game_rps":
        keyboard = [
            [InlineKeyboardButton("🗻 حجر", callback_data="rps_rock")],
            [InlineKeyboardButton("📄 ورقة", callback_data="rps_paper")],
            [InlineKeyboardButton("✂️ مقص", callback_data="rps_scissors")],
        ]
        await query.message.reply_text("اختر:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("rps_"):
        choice = data.split("_")[1]
        bot_choice = random.choice(['rock', 'paper', 'scissors'])
        choices_map = {'rock':'🗻 حجر', 'paper':'📄 ورقة', 'scissors':'✂️ مقص'}
        user_choice_text = choices_map.get(choice, choice)
        bot_choice_text = choices_map.get(bot_choice, bot_choice)
        if choice == bot_choice:
            result = "🤝 تعادل"
        elif (choice == 'rock' and bot_choice == 'scissors') or \
             (choice == 'scissors' and bot_choice == 'paper') or \
             (choice == 'paper' and bot_choice == 'rock'):
            result = "🎉 فزت!"
        else:
            result = "💔 خسرت!"
        await query.message.reply_text(f"اخترت: {user_choice_text}\nالبوت اختار: {bot_choice_text}\n\n{result}")
        return

    # ── بحث جوجل ────────────────────────────
    if data == "menu_google":
        await query.message.reply_text("🔍 **أرسل ما تريد البحث عنه في جوجل:**", parse_mode="Markdown")
        context.user_data['waiting_google'] = True
        return

    # ── رابط الدعوة (للمشرفين) ───────────────
    if data == "exec_invite":
        if not await is_admin_group(update, user.id):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        try:
            link = await context.bot.create_chat_invite_link(update.effective_chat.id, member_limit=1)
            await query.message.reply_text(f"🔗 رابط دعوة: {link.invite_link}")
        except:
            await query.message.reply_text("❌ لا يمكن إنشاء رابط، تأكد من صلاحيات البوت.")
        return

    # ── مسح الرسائل (للمشرفين) ────────────────
    if data == "exec_purge":
        if not await is_admin_group(update, user.id):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        context.user_data['purge_mode'] = True
        await query.message.reply_text("📨 **قم بالرد على رسالة لمسح كل الرسائل التي بعدها، أو أرسل عدد الرسائل المراد مسحها (مثل: 10)**", parse_mode="Markdown")
        return

    # ── تذكير ────────────────────────────────
    if data == "exec_remind":
        await query.message.reply_text("⏰ **أرسل عدد الدقائق ثم نص التذكير (مثال: 5 تذكير بالاجتماع)**", parse_mode="Markdown")
        context.user_data['waiting_remind'] = True
        return

    # ── إحصائيات العضو ───────────────────────
    if data == "exec_member_stats":
        # نحتاج قاعدة بيانات لعدد رسائل الأعضاء - سنقوم بمحاكاة بسيطة
        # هنا نستخدم متغير مؤقت
        points = temp_points.get(user.id, 0)
        await query.message.reply_text(f"📈 **إحصائياتك:**\nعدد النقاط: {points}\n(يمكنك كسب نقطة عبر الأمر 'هدية عشوائية')", parse_mode="Markdown")
        return

    # ── هدية عشوائية ─────────────────────────
    if data == "exec_gift":
        gift = random.randint(1, 10)
        temp_points[user.id] = temp_points.get(user.id, 0) + gift
        await query.message.reply_text(f"🎁 **لقد حصلت على {gift} نقطة!**\nإجمالي نقاطك: {temp_points[user.id]}", parse_mode="Markdown")
        return

    # ── ترجمة ────────────────────────────────
    if data == "exec_translate":
        await query.message.reply_text("🌐 **أرسل النص الذي تريد ترجمته إلى العربية:**", parse_mode="Markdown")
        context.user_data['waiting_translate'] = True
        return

    # ── بث للمجموعة (للمشرفين) ───────────────
    if data == "exec_broadcast":
        if not await is_admin_group(update, user.id):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        await query.message.reply_text("📢 **أرسل النص الذي تريد بثه للمجموعة:**", parse_mode="Markdown")
        context.user_data['waiting_broadcast'] = True
        return

    # ──────────────────────────────────────────
    # الأقسام والقوائم الفرعية (مثل menu_main, menu_admin, etc.)
    # ──────────────────────────────────────────

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
            [
                InlineKeyboardButton("🎮 ألعاب",          callback_data="menu_games"),
                InlineKeyboardButton("🔍 بحث جوجل",       callback_data="menu_google"),
            ],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "🌅 بوت شفق — القائمة الرئيسية\nاختر القسم:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ── أوامر المشرفين ────────────────────────
    if data == "menu_admin":
        keyboard = [
            [InlineKeyboardButton("🚫 الحظر", callback_data="menu_ban")],
            [InlineKeyboardButton("⚠️ التحذيرات", callback_data="menu_warn")],
            [InlineKeyboardButton("🔇 الكتم", callback_data="menu_mute")],
            [InlineKeyboardButton("⚙️ الإدارة", callback_data="menu_manage")],
            [InlineKeyboardButton("🔗 رابط دعوة", callback_data="exec_invite")],
            [InlineKeyboardButton("🗑️ مسح رسائل", callback_data="exec_purge")],
            [InlineKeyboardButton("📢 بث", callback_data="exec_broadcast")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "👮 أوامر المشرفين — اختر:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ── قسم الحظر (قائمة فرعية سريعة) ────────
    if data == "menu_ban":
        keyboard = [
            [InlineKeyboardButton("📋 قائمة المحظورين", callback_data="exec_banlist")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "🚫 الحظر:\n• حظر — رد على عضو\n• حظر 123 7d سبب\n• رفع الحظر — رد على عضو\n• تحقق — رد على عضو\n• معلومات — رد على عضو",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "menu_warn":
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "⚠️ التحذيرات:\n• تحذير — رد على عضو\n• مسح التحذير — رد على عضو\n• التحذيرات — رد على عضو\n(3 تحذيرات = حظر تلقائي)",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "menu_mute":
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "🔇 الكتم:\n• كتم — رد على عضو\n• كتم 123 1h — كتم مؤقت\n• رفع الكتم — رد على عضو",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "menu_manage":
        keyboard = [
            [
                InlineKeyboardButton("🔒 أغلق المجموعة", callback_data="exec_lock"),
                InlineKeyboardButton("🔓 افتح المجموعة", callback_data="exec_unlock"),
            ],
            [
                InlineKeyboardButton("📋 سجل الأحداث", callback_data="exec_eventlog"),
                InlineKeyboardButton("📊 تقرير فوري", callback_data="exec_report"),
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
        return

    # ── للجميع ───────────────────────────────
    if data == "menu_user":
        keyboard = [
            [InlineKeyboardButton("🪪 معلوماتي", callback_data="exec_id")],
            [InlineKeyboardButton("📋 القواعد", callback_data="exec_rules")],
            [InlineKeyboardButton("📚 الموارد", callback_data="exec_resources")],
            [InlineKeyboardButton("📈 إحصائياتي", callback_data="exec_member_stats")],
            [InlineKeyboardButton("🎁 هدية عشوائية", callback_data="exec_gift")],
            [InlineKeyboardButton("🌐 ترجمة", callback_data="exec_translate")],
            [InlineKeyboardButton("⏰ تذكير", callback_data="exec_remind")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "👥 للجميع — اختر أمراً:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ── الميديا ──────────────────────────────
    if data == "menu_media":
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "🎵 الميديا:\n• أرسل رابط يوتيوب / تيك توك / انستقرام مباشرة\n• يوتيوب <اسم الأغنية> — بحث",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ── الموارد ──────────────────────────────
    if data == "menu_resources":
        keyboard = [
            [InlineKeyboardButton("📖 عرض الموارد", callback_data="exec_resources")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await query.edit_message_text(
            "📚 الموارد:\n• الموارد — عرض القائمة\n• الموارد <كلمة> — بحث",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ──────────────────────────────────────────
    # الأوامر المنفذة المباشرة (exec_*)
    # ──────────────────────────────────────────

    # معلوماتي
    if data == "exec_id":
        from handlers_user import cmd_id
        # إعادة توجيه update.message إلى query.message
        update.message = query.message
        await cmd_id(update, context)
        return

    # القواعد
    if data == "exec_rules":
        from handlers_user import cmd_rules
        update.message = query.message
        await cmd_rules(update, context)
        return

    # الموارد
    if data == "exec_resources":
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
        return

    # قائمة المحظورين
    if data == "exec_banlist":
        if not await is_admin_group(update, user.id):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        bans = await db.get_ban_list(update.effective_chat.id)
        if not bans:
            await query.answer("لا يوجد محظورون حالياً ✅", show_alert=True)
            return
        lines = [f"• {b['user_id']}" + (f" (ينتهي {b['expires_at'][:10]})" if b.get('expires_at') else " (دائم)") for b in bans[:20]]
        await query.message.reply_text("🚫 المحظورون:\n" + "\n".join(lines))
        return

    # إغلاق المجموعة
    if data == "exec_lock":
        if not await is_admin_group(update, user.id):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        try:
            await context.bot.set_chat_permissions(update.effective_chat.id, permissions=ChatPermissions(can_send_messages=False))
            await query.answer("🔒 تم إغلاق المجموعة", show_alert=True)
            await db.log_event(update.effective_chat.id, "lock", user_id=user.id)
        except:
            await query.answer("❌ تعذّر الإغلاق", show_alert=True)
        return

    # فتح المجموعة
    if data == "exec_unlock":
        if not await is_admin_group(update, user.id):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        try:
            await context.bot.set_chat_permissions(update.effective_chat.id, permissions=ChatPermissions(
                can_send_messages=True, can_send_media_messages=True, can_send_polls=True,
                can_send_other_messages=True, can_add_web_page_previews=True))
            await query.answer("🔓 تم فتح المجموعة", show_alert=True)
            await db.log_event(update.effective_chat.id, "unlock", user_id=user.id)
        except:
            await query.answer("❌ تعذّر الفتح", show_alert=True)
        return

    # سجل الأحداث
    if data == "exec_eventlog":
        if not await is_admin_group(update, user.id):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        events = await db.get_event_log(update.effective_chat.id, 10)
        if not events:
            await query.answer("لا توجد أحداث", show_alert=True)
            return
        lines = [f"• {e['action']} — {e['created_at'][:16]}" for e in events]
        await query.message.reply_text("📋 سجل الأحداث:\n" + "\n".join(lines))
        return

    # تقرير فوري
    if data == "exec_report":
        if not await is_admin_group(update, user.id):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        from handlers_jobs import cmd_report
        context.args = []
        await cmd_report(update, context)
        return

    # قائمة الكلمات المحظورة
    if data == "exec_wordlist":
        if not await is_admin_group(update, user.id):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        words = await db.get_banned_words(update.effective_chat.id)
        if not words:
            await query.answer("لا توجد كلمات محظورة", show_alert=True)
            return
        await query.message.reply_text("🚫 الكلمات المحظورة:\n" + "\n".join(f"• {w}" for w in words))
        return

# ================================================
# معالج الرسائل النصية للأوامر التفاعلية (مسح، تذكير، ترجمة، بث، بحث جوجل)
# ================================================
async def handle_interactive_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text
    user_id = update.effective_user.id

    # بحث جوجل
    if context.user_data.get('waiting_google'):
        del context.user_data['waiting_google']
        query_text = text.replace(' ', '+')
        link = f"https://www.google.com/search?q={query_text}"
        await update.message.reply_text(f"🔍 **نتائج بحث جوجل:**\n[اضغط هنا]({link})", parse_mode="Markdown", disable_web_page_preview=True)
        return

    # وضع مسح الرسائل (purge)
    if context.user_data.get('purge_mode'):
        del context.user_data['purge_mode']
        # إذا كان الرقم صحيحًا
        if text.isdigit():
            count = int(text)
            if count > 100:
                await update.message.reply_text("لا يمكن مسح أكثر من 100 رسالة.")
                return
            try:
                await context.bot.delete_messages(update.effective_chat.id, range(update.message.message_id - count, update.message.message_id))
            except:
                await update.message.reply_text("فشل المسح، ربما الرسائل قديمة.")
        else:
            # الرد على رسالة: لمسح جميع الرسائل بعدها
            if update.message.reply_to_message:
                msg_id = update.message.reply_to_message.message_id
                try:
                    for i in range(msg_id, update.message.message_id):
                        await context.bot.delete_message(update.effective_chat.id, i)
                except:
                    pass
            else:
                await update.message.reply_text("أرسل عددًا أو رد على رسالة لمسح ما بعدها.")
        return

    # تذكير
    if context.user_data.get('waiting_remind'):
        del context.user_data['waiting_remind']
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[0].isdigit():
            await update.message.reply_text("❌ الصيغة: عدد الدقائق ثم النص (مثال: 5 تذكير بالاجتماع)")
            return
        minutes = int(parts[0])
        reminder_text = parts[1]
        delay = minutes * 60
        if delay > 86400:
            await update.message.reply_text("لا يمكن ضبط تذكير لأكثر من يوم.")
            return
        context.job_queue.run_once(lambda ctx: ctx.bot.send_message(chat_id=update.effective_chat.id, text=f"⏰ تذكير: {reminder_text}"), delay)
        await update.message.reply_text(f"✅ تم ضبط تذكير بعد {minutes} دقيقة.")
        return

    # ترجمة (بسيطة - تستخدم مكتبة وهمية، سنستخدم ترجمة عبر API مجاني)
    if context.user_data.get('waiting_translate'):
        del context.user_data['waiting_translate']
        # هنا يمكنك استخدام googletrans أو أي خدمة. للتبسيط سنقوم بمحاكاة ترجمة
        # في الواقع ستحتاج إلى تثبيت googletrans==4.0.0-rc1 وإضافة:
        # from googletrans import Translator
        # translator = Translator()
        # result = translator.translate(text, dest='ar')
        # await update.message.reply_text(f"🌐 الترجمة:\n{result.text}")
        await update.message.reply_text("🌐 خدمة الترجمة غير متاحة حالياً بسبب القيود التقنية. جرب يدوياً عبر Google Translate.")
        return

    # بث للمجموعة (للمشرفين)
    if context.user_data.get('waiting_broadcast'):
        del context.user_data['waiting_broadcast']
        if not await is_admin_group(update, user_id):
            await update.message.reply_text("⛔ ليس لديك صلاحية.")
            return
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"📢 **بث من المشرف:**\n{text}", parse_mode="Markdown")
        await update.message.reply_text("✅ تم إرسال البث.")
        return

# يجب إضافة هذا المعالج في app.py (MessageHandler بعد handle_text)
# أضف السطر التالي في app.py داخل register_handlers:
# app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_interactive_messages))