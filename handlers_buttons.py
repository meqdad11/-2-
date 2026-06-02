import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes
import database as db
from helpers import is_admin

logger = logging.getLogger(__name__)
temp_points = {}
temp_games = {}

class FakeUpdate:
    def __init__(self, message):
        self.message = message
        self.effective_chat = message.chat
        self.effective_user = message.from_user

async def callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    msg = query.message
    chat_id = msg.chat.id

    if data == "menu_close":
        await msg.delete()
        return

    if data == "exec_stats":
        try:
            members_count = await context.bot.get_chat_member_count(chat_id)
            admins = await context.bot.get_chat_administrators(chat_id)
            admins_count = len(admins)
            await msg.reply_text(f"📊 إحصائيات المجموعة:\n👥 الأعضاء: {members_count}\n👮 المشرفون: {admins_count}")
        except:
            await msg.reply_text("📊 لا يمكن جلب الإحصائيات حالياً.")
        return

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
        await msg.reply_text(f"💬 اقتباس اليوم:\n\n{random.choice(quotes)}")
        return

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
        await msg.reply_text(help_text, parse_mode="Markdown")
        return

    if data == "menu_contact":
        await msg.reply_text("📞 **تواصل مع المطور:**\n[اضغط هنا](https://t.me/Me8dad)", parse_mode="Markdown", disable_web_page_preview=True)
        return

    if data == "menu_games":
        keyboard = [
            [InlineKeyboardButton("🎲 تخمين رقم (1-10)", callback_data="game_guess")],
            [InlineKeyboardButton("✂️ حجر ورقة مقص", callback_data="game_rps")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("🎮 **اختر لعبة:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "game_guess":
        number = random.randint(1, 10)
        temp_games[user.id] = number
        buttons = [[InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(1,6)],
                   [InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(6,11)]]
        await msg.reply_text("🎲 خمن الرقم (1-10):", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("guess_"):
        guessed = int(data.split("_")[1])
        correct = temp_games.get(user.id)
        if not correct:
            await query.answer("ابدأ لعبة جديدة من القائمة أولاً", show_alert=True)
            return
        if guessed == correct:
            await msg.reply_text(f"🎉 **صحيح!** الرقم كان {correct}. تهانينا!")
            del temp_games[user.id]
        else:
            await msg.reply_text(f"❌ خطأ! الرقم {guessed} ليس صحيحًا. حاول مرة أخرى.")
        return

    if data == "game_rps":
        keyboard = [
            [InlineKeyboardButton("🗻 حجر", callback_data="rps_rock")],
            [InlineKeyboardButton("📄 ورقة", callback_data="rps_paper")],
            [InlineKeyboardButton("✂️ مقص", callback_data="rps_scissors")],
        ]
        await msg.reply_text("اختر:", reply_markup=InlineKeyboardMarkup(keyboard))
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
        await msg.reply_text(f"اخترت: {user_choice_text}\nالبوت اختار: {bot_choice_text}\n\n{result}")
        return

    if data == "menu_google":
        context.user_data['waiting_google'] = chat_id
        await msg.reply_text("🔍 **أرسل ما تريد البحث عنه في جوجل:**", parse_mode="Markdown")
        return

    # ================= قائمة الأوامر المتقدمة =================
    if data == "menu_commands":
        keyboard = [
            [InlineKeyboardButton("🔐 أوامر القفل والفتح", callback_data="menu_lock_commands")],
            [InlineKeyboardButton("🛠 الأوامر الخدمية", callback_data="menu_service_commands")],
            [InlineKeyboardButton("👮 أوامر الإدارة", callback_data="menu_admin_commands")],
            [InlineKeyboardButton("👨‍💻 أوامر المطور", callback_data="menu_dev_commands")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("📋 قائمة الأوامر المتخصصة:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_lock_commands":
        lock_types = [
            "links", "tags", "media", "files", "video", "voice", "gifs",
            "edit", "editmedia", "repeat", "join", "forward", "id", "badwords",
            "spam", "replies", "notifications", "persian", "bots", "iranian",
            "longtext", "quran", "porn", "ai", "autoreply", "games", "marketnews", "whisper"
        ]
        name_map = {
            "links":"الروابط", "tags":"التاك", "media":"الميديا", "files":"الملفات",
            "video":"الفيديو", "voice":"الفويسات", "gifs":"المتحركات", "edit":"التعديل",
            "editmedia":"تعديل الميديا", "repeat":"التكرار", "join":"الدخول", "forward":"التوجيه",
            "id":"ايدي", "badwords":"السب", "spam":"السبام", "replies":"الردود",
            "notifications":"الاشعارات", "persian":"الفارسية", "bots":"البوتات", "iranian":"دخول الايراني",
            "longtext":"الكلام الكثير", "quran":"القرآن", "porn":"الاباحي", "ai":"الذكاء الاصطناعي",
            "autoreply":"الرد التلقائي", "games":"الألعاب", "marketnews":"اخبار السوق", "whisper":"الهمسة"
        }
        buttons = []
        for lt in lock_types:
            display = name_map.get(lt, lt)
            buttons.append([InlineKeyboardButton(f"🔒 قفل {display}", callback_data=f"lock_{lt}"),
                            InlineKeyboardButton(f"🔓 فتح {display}", callback_data=f"unlock_{lt}")])
        buttons.append([InlineKeyboardButton("🔒 قفل الكل", callback_data="lock_all"),
                        InlineKeyboardButton("🔓 فتح الكل", callback_data="unlock_all")])
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_commands")])
        buttons.append([InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")])
        await msg.edit_text("🔐 اختر نوع القفل:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("lock_") and not data.startswith("lock_all"):
        lock_type = data.split("_")[1]
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        await db.set_lock(chat_id, lock_type, True)
        await query.answer(f"🔒 تم قفل {lock_type}", show_alert=True)
        await msg.edit_text(f"🔒 تم قفل {lock_type}.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_lock_commands")]]))
        return
    if data.startswith("unlock_") and not data.startswith("unlock_all"):
        lock_type = data.split("_")[1]
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        await db.set_lock(chat_id, lock_type, False)
        await query.answer(f"🔓 تم فتح {lock_type}", show_alert=True)
        await msg.edit_text(f"🔓 تم فتح {lock_type}.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_lock_commands")]]))
        return

    if data == "lock_all":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        lock_types = ["links","tags","media","files","video","voice","gifs","edit","editmedia","repeat","join","forward","id","badwords","spam","replies","notifications","persian","bots","iranian","longtext","quran","porn","ai","autoreply","games","marketnews","whisper"]
        for lt in lock_types:
            await db.set_lock(chat_id, lt, True)
        await query.answer("🔒 تم قفل جميع الحمايات", show_alert=True)
        await msg.edit_text("🔒 تم قفل كل شيء.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_lock_commands")]]))
        return
    if data == "unlock_all":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        lock_types = ["links","tags","media","files","video","voice","gifs","edit","editmedia","repeat","join","forward","id","badwords","spam","replies","notifications","persian","bots","iranian","longtext","quran","porn","ai","autoreply","games","marketnews","whisper"]
        for lt in lock_types:
            await db.set_lock(chat_id, lt, False)
        await query.answer("🔓 تم فتح جميع الحمايات", show_alert=True)
        await msg.edit_text("🔓 تم فتح كل شيء.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_lock_commands")]]))
        return

    if data == "menu_service_commands":
        text = (
            "🛠 **الأوامر الخدمية:**\n"
            "• ايدي - معرفك\n"
            "• افتاري - رابط المجموعة\n"
            "• اهمس @username - رسالة خاصة\n"
            "• صارحني - تواصل خاص\n"
            "• سورة [اسم السورة] - آية عشوائية\n"
            "• قران [رقم الصفحة] - نص الصفحة\n"
            "• انطقي [النص] - نطق النص\n"
            "• وش يقول (رد على فويس) - تحويل الصوت لنص\n"
            "• جيمناي - محادثة ذكاء اصطناعي\n"
            "• الحد - إدارة الموديلات"
        )
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_commands")]]))
        return
    if data == "menu_admin_commands":
        text = (
            "👮 **أوامر الإدارة (للمشرفين):**\n"
            "• كتم / الغاء كتم\n"
            "• طرد / حظر / الغاء حظر\n"
            "• رفع مشرف / تنزيل مشرف\n"
            "• رفع / تنزيل (عضو مميز)\n"
            "• المشرفين / تنزيل الكل\n"
            "• مسح [عدد] / مسح المحظورين\n"
            "• مسح المكتومين / تاك للكل\n"
            "• رتبتي / رتبته"
        )
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_commands")]]))
        return
    if data == "menu_dev_commands":
        text = (
            "👨‍💻 **أوامر المطور:**\n"
            "• رفع مطور / تنزيل مطور\n"
            "• اضف مطور / حذف مطور\n"
            "• المطور / اذاعه"
        )
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_commands")]]))
        return

    # ================= القوائم الرئيسية =================
    if data == "menu_main":
        keyboard = [
            [InlineKeyboardButton("👮 أوامر المشرفين", callback_data="menu_admin")],
            [InlineKeyboardButton("👥 للجميع", callback_data="menu_user")],
            [InlineKeyboardButton("🎵 الميديا", callback_data="menu_media")],
            [InlineKeyboardButton("📚 الموارد", callback_data="menu_resources")],
            [InlineKeyboardButton("📊 إحصائيات", callback_data="exec_stats")],
            [InlineKeyboardButton("💬 اقتباس اليوم", callback_data="exec_quote")],
            [InlineKeyboardButton("📋 الأوامر", callback_data="menu_commands")],
            [InlineKeyboardButton("❓ المساعدة", callback_data="menu_help")],
            [InlineKeyboardButton("📞 تواصل", callback_data="menu_contact")],
            [InlineKeyboardButton("🎮 ألعاب", callback_data="menu_games")],
            [InlineKeyboardButton("🔍 بحث جوجل", callback_data="menu_google")],
            [InlineKeyboardButton("📢 قناة التحديثات", url="https://t.me/shafaqmeqdad")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("🌅 بوت شفق — القائمة الرئيسية\nاختر القسم:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

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
        await msg.edit_text("👮 أوامر المشرفين — اختر:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_ban":
        keyboard = [
            [InlineKeyboardButton("📋 قائمة المحظورين", callback_data="exec_banlist")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "🚫 **الحظر:**\n• حظر — رد على عضو\n• حظر 123 7d سبب — حظر مؤقت\n• رفع الحظر — رد على عضو\n• تحقق — رد على عضو\n• معلومات — رد على عضو",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "menu_warn":
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "⚠️ **التحذيرات:**\n• تحذير — رد على عضو\n• مسح التحذير — رد على عضو\n• التحذيرات — رد على عضو\n\nملاحظة: 3 تحذيرات = حظر تلقائي",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "menu_mute":
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "🔇 **الكتم:**\n• كتم — رد على عضو\n• كتم 123 1h — كتم مؤقت\n• رفع الكتم — رد على عضو",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "menu_manage":
        keyboard = [
            [InlineKeyboardButton("🔒 أغلق المجموعة", callback_data="exec_lock")],
            [InlineKeyboardButton("🔓 افتح المجموعة", callback_data="exec_unlock")],
            [InlineKeyboardButton("📋 سجل الأحداث", callback_data="exec_eventlog")],
            [InlineKeyboardButton("📊 تقرير فوري", callback_data="exec_report")],
            [InlineKeyboardButton("🚫 الكلمات المحظورة", callback_data="exec_wordlist")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("⚙️ الإدارة — اختر أمراً:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

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
        await msg.edit_text("👥 للجميع — اختر أمراً:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "exec_id":
        first = user.first_name or ""
        username = f"@{user.username}" if user.username else ""
        await msg.reply_text(f"🪪 **معلوماتك:**\nالاسم: {first}\nالمعرف: {user.id}\n{username}", parse_mode="Markdown")
        return

    if data == "exec_rules":
        rules = await db.get_setting(chat_id, "rules")
        if rules:
            await msg.reply_text(f"📋 **قواعد المجموعة:**\n{rules}", parse_mode="Markdown")
        else:
            await query.answer("لم يتم تعيين قواعد بعد", show_alert=True)
        return

    if data == "exec_resources":
        from handlers_resources import _get_resources
        resources = await _get_resources(chat_id)
        if not resources:
            await query.answer("لا توجد موارد مضافة بعد", show_alert=True)
            return
        lines = []
        for i, r in enumerate(resources[:20], 1):
            lines.append(f"{i}. 📌 {r['title']}\n   {r['content'][:100]}")
        await msg.reply_text("📚 **الموارد:**\n\n" + "\n\n".join(lines), parse_mode="Markdown")
        return

    if data == "exec_member_stats":
        points = temp_points.get(user.id, 0)
        await msg.reply_text(f"📈 **إحصائياتك:**\nعدد النقاط: {points}\n(يمكنك كسب نقطة عبر 'هدية عشوائية')", parse_mode="Markdown")
        return

    if data == "exec_gift":
        gift = random.randint(1, 10)
        temp_points[user.id] = temp_points.get(user.id, 0) + gift
        await msg.reply_text(f"🎁 **لقد حصلت على {gift} نقطة!**\nإجمالي نقاطك: {temp_points[user.id]}", parse_mode="Markdown")
        return

    if data == "exec_translate":
        await msg.reply_text("🌐 **أرسل النص الذي تريد ترجمته إلى العربية:**", parse_mode="Markdown")
        context.user_data['waiting_translate'] = chat_id
        return

    if data == "exec_remind":
        await msg.reply_text("⏰ **أرسل عدد الدقائق ثم نص التذكير (مثال: 5 تذكير بالاجتماع)**", parse_mode="Markdown")
        context.user_data['waiting_remind'] = chat_id
        return

    if data == "menu_media":
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "🎵 **الميديا:**\n• أرسل رابط يوتيوب / تيك توك / انستقرام مباشرة\n• يوتيوب <اسم الأغنية> — بحث",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "menu_resources":
        keyboard = [
            [InlineKeyboardButton("📖 عرض الموارد", callback_data="exec_resources")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "📚 **الموارد:**\n• الموارد — عرض القائمة\n• الموارد <كلمة> — بحث",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "exec_banlist":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        bans = await db.get_ban_list(chat_id)
        if not bans:
            await query.answer("لا يوجد محظورون حالياً ✅", show_alert=True)
            return
        lines = [f"• {b['user_id']}" + (f" (ينتهي {b['expires_at'][:10]})" if b.get('expires_at') else " (دائم)") for b in bans[:20]]
        await msg.reply_text("🚫 **المحظورون:**\n" + "\n".join(lines), parse_mode="Markdown")
        return

    if data == "exec_lock":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        try:
            await context.bot.set_chat_permissions(chat_id, permissions=ChatPermissions(can_send_messages=False))
            await query.answer("🔒 تم إغلاق المجموعة", show_alert=True)
            await db.log_event(chat_id, "lock", user_id=user.id)
        except:
            await query.answer("❌ تعذّر الإغلاق", show_alert=True)
        return

    if data == "exec_unlock":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        try:
            await context.bot.set_chat_permissions(chat_id, permissions=ChatPermissions(
                can_send_messages=True, can_send_media_messages=True, can_send_polls=True,
                can_send_other_messages=True, can_add_web_page_previews=True))
            await query.answer("🔓 تم فتح المجموعة", show_alert=True)
            await db.log_event(chat_id, "unlock", user_id=user.id)
        except:
            await query.answer("❌ تعذّر الفتح", show_alert=True)
        return

    if data == "exec_eventlog":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        events = await db.get_event_log(chat_id, 10)
        if not events:
            await query.answer("لا توجد أحداث مسجلة", show_alert=True)
            return
        lines = [f"• {e['action']} — {e['created_at'][:16]}" for e in events]
        await msg.reply_text("📋 **سجل الأحداث:**\n" + "\n".join(lines))
        return

    if data == "exec_wordlist":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        words = await db.get_banned_words(chat_id)
        if not words:
            await query.answer("لا توجد كلمات محظورة", show_alert=True)
            return
        await msg.reply_text("🚫 **الكلمات المحظورة:**\n" + "\n".join(f"• {w}" for w in words))
        return

    # ========== زر التقرير الفوري مع التحقق المباشر باستخدام ChatMemberStatus ==========
    if data == "exec_report":
        try:
            member = await context.bot.get_chat_member(chat_id, user.id)
            if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
                await query.answer("⛔ هذا الأمر للمشرفين فقط.", show_alert=True)
                return
        except Exception as e:
            logger.error(f"خطأ في التحقق من صلاحية التقرير: {e}")
            await query.answer("⛔ لا يمكن التحقق من صلاحيتك.", show_alert=True)
            return
        from handlers_jobs import cmd_report
        fake_update = FakeUpdate(msg)
        context.args = []
        await cmd_report(fake_update, context)
        return

    if data == "exec_invite":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        try:
            link = await context.bot.create_chat_invite_link(chat_id, member_limit=1)
            await msg.reply_text(f"🔗 **رابط دعوة:** {link.invite_link}", parse_mode="Markdown")
        except:
            await query.answer("❌ لا يمكن إنشاء رابط، تأكد من صلاحيات البوت.", show_alert=True)
        return

    if data == "exec_purge":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        await msg.reply_text("📨 **أرسل عدد الرسائل أو رد على رسالة لمسح كل الرسائل بعدها.**", parse_mode="Markdown")
        context.user_data['purge_mode'] = chat_id
        return

    if data == "exec_broadcast":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        await msg.reply_text("📢 **أرسل النص الذي تريد بثه للمجموعة:**", parse_mode="Markdown")
        context.user_data['waiting_broadcast'] = chat_id
        return