import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes
from utils import database as db
from utils.helpers import is_admin
from data.quotes import DAILY_QUOTES

logger = logging.getLogger(__name__)
temp_points = {}
temp_games = {}

class FakeUpdate:
    def __init__(self, message):
        self.message = message
        self.effective_chat = message.chat
        self.effective_user = message.from_user


# ==================== دالة القائمة الرئيسية ====================
async def callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    msg = query.message
    chat_id = msg.chat.id

    # ==================== إغلاق القائمة ====================
    if data == "menu_close":
        await msg.delete()
        return

    # ==================== طوارئ — أحتاج أحد ====================
    if data == "menu_emergency":
        keyboard = [
            [InlineKeyboardButton("✅ نعم، أحتاج مساعدة", callback_data="emergency_confirm")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
        ]
        await msg.edit_text(
            "🆘 **هل تحتاج مساعدة فعلاً؟**\n\n"
            "سيتم إبلاغ المشرفين فوراً عند التأكيد.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "emergency_confirm":
        from handlers.support import get_admin_group

        is_private = chat_id > 0
        chat_context = "خاص مع البوت" if is_private else (msg.chat.title or "مجموعة")
        clean_chat_id = str(chat_id).replace("-100", "")
        message_link = f"https://t.me/c/{clean_chat_id}/{msg.message_id}"

        user_mention = f"[{user.full_name}](tg://user?id={user.id})"
        alert_text = (
            f"🆘 **طلب مساعدة فورية**\n\n"
            f"👤 العضو: {user_mention}\n"
            f"🆔 المعرف: `{user.id}`\n"
            f"💬 المصدر: {chat_context}\n\n"
            f"يرجى التواصل معه في أقرب وقت."
        )
        keyboard_admin = [
            [InlineKeyboardButton(
                f"💬 راسل {user.first_name}",
                url=f"tg://user?id={user.id}"
            )],
            [InlineKeyboardButton(
                "📩 الرسالة الأصلية",
                url=message_link
            )]
        ]

        if is_private:
            try:
                await context.bot.send_message(
                    729970974,
                    alert_text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard_admin)
                )
            except Exception as e:
                logger.error(f"emergency_confirm DM to dev error: {e}")
        else:
            admin_group_id = await get_admin_group(chat_id)
            if admin_group_id:
                try:
                    await context.bot.send_message(
                        admin_group_id,
                        alert_text,
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard_admin)
                    )
                except Exception as e:
                    logger.error(f"emergency_confirm notify error: {e}")
            else:
                try:
                    admins = await context.bot.get_chat_administrators(chat_id)
                    for admin in admins:
                        if not admin.user.is_bot:
                            try:
                                await context.bot.send_message(
                                    admin.user.id,
                                    alert_text,
                                    parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(keyboard_admin)
                                )
                            except:
                                pass
                except Exception as e:
                    logger.error(f"emergency_confirm admin DM error: {e}")

        # رسالة الرد للمستخدم — مع زر يفتح محادثة معك في الخاص
        keyboard = [
            [InlineKeyboardButton("💬 راسل المطور مباشرة", url="https://t.me/Me8dad")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]
        ]
        await msg.edit_text(
            "💙 لست وحدك.\n\n"
            "تم إبلاغ المشرفين وسيتواصلون معك قريباً.\n\n"
            "إذا كنت في خطر فوري:\n"
            "📞 الطوارئ: **911**\n"
            "📞 الدعم النفسي: **920033360**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ==================== إحصائيات سريعة ====================
    if data == "exec_stats":
        try:
            members_count = await context.bot.get_chat_member_count(chat_id)
            admins = await context.bot.get_chat_administrators(chat_id)
            admins_count = len(admins)
            text = f"📊 إحصائيات المجموعة:\n👥 الأعضاء: {members_count}\n👮 المشرفون: {admins_count}"
        except:
            text = "📊 لا يمكن جلب الإحصائيات حالياً."
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== اقتباس اليوم ====================
    if data == "exec_quote":
        text = f"💬 اقتباس اليوم:\n\n{random.choice(DAILY_QUOTES)}"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== المساعدة والتواصل (للجميع) ====================
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
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "menu_contact":
        text = "📞 **تواصل مع المطور:**\n[اضغط هنا](https://t.me/Me8dad)"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown", disable_web_page_preview=True)
        return

    # ==================== الألعاب (للجميع) ====================
    if data == "menu_games":
        keyboard = [
            [InlineKeyboardButton("🎲 تخمين رقم (1-10)", callback_data="game_guess"),
             InlineKeyboardButton("✂️ حجر ورقة مقص", callback_data="game_rps")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main"),
             InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("🎮 **اختر لعبة:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "game_guess":
        number = random.randint(1, 10)
        temp_games[user.id] = number
        buttons = [[InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(1,6)],
                   [InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(6,11)],
                   [InlineKeyboardButton("🔙 رجوع", callback_data="menu_games")]]
        await msg.edit_text("🎲 خمن الرقم (1-10):", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("guess_"):
        guessed = int(data.split("_")[1])
        correct = temp_games.get(user.id)
        if not correct:
            await query.answer("ابدأ لعبة جديدة من القائمة أولاً", show_alert=True)
            return
        if guessed == correct:
            text = f"🎉 **صحيح!** الرقم كان {correct}. تهانينا!"
            del temp_games[user.id]
        else:
            text = f"❌ خطأ! الرقم {guessed} ليس صحيحًا. حاول مرة أخرى."
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_games"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "game_rps":
        keyboard = [
            [InlineKeyboardButton("🗻 حجر", callback_data="rps_rock"),
             InlineKeyboardButton("📄 ورقة", callback_data="rps_paper")],
            [InlineKeyboardButton("✂️ مقص", callback_data="rps_scissors"),
             InlineKeyboardButton("🔙 رجوع", callback_data="menu_games")],
        ]
        await msg.edit_text("اختر:", reply_markup=InlineKeyboardMarkup(keyboard))
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
        text = f"اخترت: {user_choice_text}\nالبوت اختار: {bot_choice_text}\n\n{result}"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_games"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== بحث جوجل (للجميع) ====================
    if data == "menu_google":
        context.user_data['waiting_google'] = chat_id
        text = "🔍 **أرسل ما تريد البحث عنه في جوجل:**"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    # ==================== قائمة الأوامر المتقدمة ====================
    if data == "menu_commands":
        keyboard = [
            [InlineKeyboardButton("🔐 أوامر القفل والفتح", callback_data="menu_lock_commands"),
             InlineKeyboardButton("🛠 الأوامر الخدمية", callback_data="menu_service_commands")],
            [InlineKeyboardButton("👮 أوامر الإدارة", callback_data="menu_admin_commands"),
             InlineKeyboardButton("👨‍💻 أوامر المطور", callback_data="menu_dev_commands")],
            [InlineKeyboardButton("🚨 نظام الأزمات", callback_data="menu_crisis_commands")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main"),
             InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("📋 قائمة الأوامر المتخصصة:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== أوامر القفل (للمشرفين فقط) ====================
    if data == "menu_lock_commands":
        if not await is_admin(update, context):
            await query.answer("⛔ هذه القائمة للمشرفين فقط", show_alert=True)
            return
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
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_commands"),
                        InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")])
        await msg.edit_text("🔐 اختر نوع القفل:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("lock_") and not data.startswith("lock_all"):
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        lock_type = data.split("_")[1]
        await db.set_lock(chat_id, lock_type, True)
        await query.answer(f"🔒 تم قفل {lock_type}", show_alert=True)
        await show_lock_result(msg, f"🔒 تم قفل {lock_type}.", "menu_lock_commands")
        return
    if data.startswith("unlock_") and not data.startswith("unlock_all"):
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        lock_type = data.split("_")[1]
        await db.set_lock(chat_id, lock_type, False)
        await query.answer(f"🔓 تم فتح {lock_type}", show_alert=True)
        await show_lock_result(msg, f"🔓 تم فتح {lock_type}.", "menu_lock_commands")
        return

    if data == "lock_all":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        lock_types = ["links","tags","media","files","video","voice","gifs","edit","editmedia","repeat","join","forward","id","badwords","spam","replies","notifications","persian","bots","iranian","longtext","quran","porn","ai","autoreply","games","marketnews","whisper"]
        for lt in lock_types:
            await db.set_lock(chat_id, lt, True)
        await query.answer("🔒 تم قفل جميع الحمايات", show_alert=True)
        await show_lock_result(msg, "🔒 تم قفل كل شيء.", "menu_lock_commands")
        return
    if data == "unlock_all":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        lock_types = ["links","tags","media","files","video","voice","gifs","edit","editmedia","repeat","join","forward","id","badwords","spam","replies","notifications","persian","bots","iranian","longtext","quran","porn","ai","autoreply","games","marketnews","whisper"]
        for lt in lock_types:
            await db.set_lock(chat_id, lt, False)
        await query.answer("🔓 تم فتح جميع الحمايات", show_alert=True)
        await show_lock_result(msg, "🔓 تم فتح كل شيء.", "menu_lock_commands")
        return

    # ==================== الأوامر الخدمية ====================
    if data == "menu_service_commands":
        text = (
            "🛠 **الأوامر الخدمية:**\n"
            "• ايدي - معرفك\n"
            "• افتاري - رابط المجموعة\n"
            "• صارحني - رابط لرسائل مجهولة\n"
            "• سورة [رقم] - معلومات السورة\n"
            "• المالك - تواصل مع المطور\n"
            "• بايـو - عرض البايو\n"
            "• ترجم - ترجمة النص\n"
            "• رسائلي - إحصائيات رسائلك\n"
            "• تذكر [دقائق] [نص] - تذكير\n"
            "• تذكير يومي [وقت] [نص] - تذكير يومي"
        )
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_commands"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    # ==================== أوامر الإدارة ====================
    if data == "menu_admin_commands":
        if not await is_admin(update, context):
            await query.answer("⛔ هذه القائمة للمشرفين فقط", show_alert=True)
            return
        text = (
            "👮 **أوامر الإدارة (للمشرفين):**\n"
            "• كتم / رفع الكتم\n"
            "• حظر / رفع الحظر\n"
            "• رفع مشرف / تنزيل مشرف\n"
            "• المشرفين / تنزيل الكل\n"
            "• مسح المحظورين / مسح المكتومين\n"
            "• تاك للكل / رتبتي / رتبته\n"
            "• ملف - ملف العضو (بالرد)\n"
            "• ثبت / الغاء تثبيت\n"
            "• تنبيه - تنبيه عضو\n"
            "• تقرير متقدم - تقرير مفصل"
        )
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_commands"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    # ==================== أوامر المطور ====================
    if data == "menu_dev_commands":
        if not await is_admin(update, context):
            await query.answer("⛔ هذه القائمة للمشرفين فقط", show_alert=True)
            return
        text = (
            "👨‍💻 **أوامر المطور:**\n"
            "• رفع مطور / تنزيل مطور\n"
            "• اذاعه - بث للكل\n"
            "• احصائيات - إحصائيات البوت\n"
            "• نسخ احتياطي - نسخ القاعدة\n"
            "• مستخدمين نشطين"
        )
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_commands"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    # ==================== نظام الأزمات ====================
    if data == "menu_crisis_commands":
        if not await is_admin(update, context):
            await query.answer("⛔ هذه القائمة للمشرفين فقط", show_alert=True)
            return
        text = (
            "🚨 **نظام الأزمات:**\n\n"
            "• اضف كلمة ازمة - إضافة كلمة\n"
            "• اضف كلمات ازمة - إضافة عدة كلمات\n"
            "• حذف كلمة ازمة - حذف كلمة\n"
            "• كلمات الازمة - عرض الكلمات\n"
            "• رد الازمة - تعيين الرد\n"
            "• تفعيل الازمة - تشغيل النظام\n"
            "• تعطيل الازمة - إيقاف النظام\n"
            "• حالة الازمة - معرفة الحالة"
        )
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_commands"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    # ==================== القائمة الرئيسية (فهرس فقط) ====================
    if data == "menu_main":
        keyboard = [
            [InlineKeyboardButton("👮 أوامر المشرفين", callback_data="menu_admin"),
             InlineKeyboardButton("👥 للجميع", callback_data="menu_user")],
            [InlineKeyboardButton("🎵 الميديا", callback_data="menu_media"),
             InlineKeyboardButton("📚 الموارد", callback_data="menu_resources")],
            [InlineKeyboardButton("📋 الأوامر المتقدمة", callback_data="menu_commands"),
             InlineKeyboardButton("🎮 ألعاب", callback_data="menu_games")],
            [InlineKeyboardButton("🔍 بحث جوجل", callback_data="menu_google"),
             InlineKeyboardButton("📞 تواصل", callback_data="menu_contact")],
            [InlineKeyboardButton("🆘 طوارئ — أحتاج أحد", callback_data="menu_emergency")],
            [InlineKeyboardButton("📢 قناة تحديثات شفق", url="https://t.me/shafaqmeqdad")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("🌅 بوت شفق — القائمة الرئيسية\nاختر القسم:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== قائمة المشرفين ====================
    if data == "menu_admin":
        if not await is_admin(update, context):
            await query.answer("⛔ هذه القائمة للمشرفين فقط", show_alert=True)
            return
        keyboard = [
            [InlineKeyboardButton("🚫 الحظر", callback_data="menu_ban"),
             InlineKeyboardButton("⚠️ التحذيرات", callback_data="menu_warn")],
            [InlineKeyboardButton("🔇 الكتم", callback_data="menu_mute"),
             InlineKeyboardButton("⚙️ الإدارة", callback_data="menu_manage")],
            [InlineKeyboardButton("📄 ملف عضو", callback_data="exec_userfile")],
            [InlineKeyboardButton("📢 تاك للكل", callback_data="exec_tagall"),
             InlineKeyboardButton("📌 تثبيت", callback_data="exec_pin_menu")],
            [InlineKeyboardButton("🔗 رابط دعوة", callback_data="exec_invite"),
             InlineKeyboardButton("🗑️ مسح رسائل", callback_data="exec_purge")],
            [InlineKeyboardButton("📢 بث", callback_data="exec_broadcast"),
             InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("👮 أوامر المشرفين — اختر:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== الأقسام الفرعية للمشرفين ====================
    if data == "menu_ban":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        keyboard = [
            [InlineKeyboardButton("📋 قائمة المحظورين", callback_data="exec_banlist"),
             InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "🚫 **الحظر:**\n• حظر — رد على عضو\n• حظر 123 7d سبب — حظر مؤقت\n• رفع الحظر — رد على عضو\n• تحقق — رد على عضو\n• معلومات — رد على عضو",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "menu_warn":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin"),
             InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "⚠️ **التحذيرات:**\n• تحذير — رد على عضو\n• مسح التحذير — رد على عضو\n• التحذيرات — رد على عضو\n\nملاحظة: 3 تحذيرات = حظر تلقائي",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "menu_mute":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin"),
             InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "🔇 **الكتم:**\n• كتم — رد على عضو\n• كتم 123 1h — كتم مؤقت\n• رفع الكتم — رد على عضو",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "menu_manage":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        keyboard = [
            [InlineKeyboardButton("🔒 أغلق المجموعة", callback_data="exec_lock"),
             InlineKeyboardButton("🔓 افتح المجموعة", callback_data="exec_unlock")],
            [InlineKeyboardButton("📋 سجل الأحداث", callback_data="exec_eventlog"),
             InlineKeyboardButton("📊 تقرير فوري", callback_data="exec_report")],
            [InlineKeyboardButton("📊 تقرير متقدم", callback_data="exec_deep_report"),
             InlineKeyboardButton("🚫 الكلمات المحظورة", callback_data="exec_wordlist")],
            [InlineKeyboardButton("🧹 مسح المحظورين", callback_data="exec_purge_bans"),
             InlineKeyboardButton("🧹 مسح المكتومين", callback_data="exec_purge_muted")],
            [InlineKeyboardButton("📊 إحصائيات المجموعة", callback_data="exec_stats")],
            [InlineKeyboardButton("🔇 المكتومون", callback_data="exec_mutelist"),
             InlineKeyboardButton("⚠️ المحذّرون", callback_data="exec_warnlist")],
            [InlineKeyboardButton("📈 تقرير أسبوعي", callback_data="exec_weekly_report")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin"),
             InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("⚙️ الإدارة — اختر أمراً:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== قائمة المستخدمين (شاملة) ====================
    if data == "menu_user":
        keyboard = [
            [InlineKeyboardButton("🪪 معلوماتي", callback_data="exec_id"),
             InlineKeyboardButton("📋 القواعد", callback_data="exec_rules")],
            [InlineKeyboardButton("📚 الموارد", callback_data="exec_resources"),
             InlineKeyboardButton("📈 إحصائياتي", callback_data="exec_member_stats")],
            [InlineKeyboardButton("💬 رسائلي", callback_data="exec_my_messages"),
             InlineKeyboardButton("🎁 هدية عشوائية", callback_data="exec_gift")],
            [InlineKeyboardButton("🌐 ترجمة", callback_data="exec_translate_msg"),
             InlineKeyboardButton("⏰ تذكير", callback_data="exec_remind")],
            [InlineKeyboardButton("🔄 تذكير يومي", callback_data="exec_daily_remind"),
             InlineKeyboardButton("📋 تذكيراتي", callback_data="exec_my_reminders")],
            [InlineKeyboardButton("❌ إلغاء تذكير يومي", callback_data="exec_cancel_daily_reminder"),
             InlineKeyboardButton("💬 اقتباس اليوم", callback_data="exec_quote")],
            [InlineKeyboardButton("👤 المالك", callback_data="exec_owner")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main"),
             InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("👥 للجميع — اختر أمراً:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== تنفيذ أوامر المستخدم ====================
    if data == "exec_id":
        first = user.first_name or ""
        username = f"@{user.username}" if user.username else ""
        text = f"🪪 **معلوماتك:**\nالاسم: {first}\nالمعرف: {user.id}\n{username}"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_user"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_rules":
        rules = await db.get_setting(chat_id, "rules")
        if rules:
            text = f"📋 **قواعد المجموعة:**\n{rules}"
        else:
            text = "لم يتم تعيين قواعد بعد"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_user"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_resources":
        from handlers.resources import _get_resources
        resources = await _get_resources(chat_id)
        if not resources:
            text = "📚 لا توجد موارد مضافة بعد"
        else:
            lines = []
            for i, r in enumerate(resources[:20], 1):
                lines.append(f"{i}. 📌 {r['title']}\n   {r['content'][:100]}")
            text = "📚 **الموارد:**\n\n" + "\n\n".join(lines)
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_user"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_member_stats":
        points = temp_points.get(user.id, 0)
        text = f"📈 **إحصائياتك:**\nعدد النقاط: {points}\n(يمكنك كسب نقطة عبر 'هدية عشوائية')"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_user"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_my_messages":
        count = await db.get_message_count(user.id, chat_id)
        text = f"💬 **رسائلك:**\nعدد رسائلك في المجموعة: {count}"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_user"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_gift":
        gift = random.randint(1, 10)
        temp_points[user.id] = temp_points.get(user.id, 0) + gift
        text = f"🎁 **لقد حصلت على {gift} نقطة!**\nإجمالي نقاطك: {temp_points[user.id]}"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_user"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_translate_msg":
        text = "📌 **الاستخدام:** رد على أي رسالة واكتب `ترجم`"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_user"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_remind":
        text = (
            "📌 **تذكير لمرة واحدة:**\n"
            "أرسل الأمر التالي:\n"
            "`تذكر 5 نص التذكير`\n\n"
            "• الرقم = عدد الدقائق (1-1440)\n"
            "• مثال: `تذكر 10 شرب الماء`\n"
            "• يعمل في الخاص والمجموعات"
        )
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_user"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_daily_remind":
        text = (
            "📌 **تذكير يومي:**\n"
            "أرسل الأمر التالي:\n"
            "`تذكير يومي 14:30 نص التذكير`\n\n"
            "• الوقت بصيغة HH:MM (مثال: 09:00، 20:30)\n"
            "• يعمل في الخاص والمجموعات"
        )
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_user"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_owner":
        text = "📞 **المالك:**\n[اضغط هنا للتواصل مع المطور](https://t.me/Me8dad)"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_user"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown", disable_web_page_preview=True)
        return

    # ==================== تنفيذ أوامر المشرفين ====================
    if data == "exec_userfile":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        text = "📄 **ملف العضو:**\nرد على العضو واكتب: `ملف`"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_tagall":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        text = "📢 **تاك للكل:**\nاستخدم: `تاك للكل` أو `تاك للكل [سبب]`"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_pin_menu":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        text = "📌 **تثبيت الرسائل:**\n• رد على رسالة واكتب: `ثبت`\n• لإلغاء التثبيت: `الغاء تثبيت`"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_purge_bans":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        from handlers.admin import cmd_purge_bans
        fake_update = FakeUpdate(msg)
        context.args = []
        await cmd_purge_bans(fake_update, context)
        await msg.delete()
        return

    if data == "exec_purge_muted":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        from handlers.admin import cmd_purge_muted
        fake_update = FakeUpdate(msg)
        context.args = []
        await cmd_purge_muted(fake_update, context)
        await msg.delete()
        return

    if data == "exec_deep_report":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        from handlers.jobs import cmd_deep_report
        fake_update = FakeUpdate(msg)
        context.args = []
        await cmd_deep_report(fake_update, context)
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_manage"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text("✅ تم إرسال التقرير المتقدم.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== تنفيذ أوامر التذكير ====================
    if data == "exec_my_reminders":
        reminders = await db.get_user_reminders(user.id, chat_id)
        if not reminders:
            text = "📭 ليس لديك أي تذكيرات يومية."
        else:
            lines = [f"⏰ {r['reminder_time']} - 📝 {r['reminder_text']}" for r in reminders]
            text = "📋 **تذكيراتك اليومية:**\n\n" + "\n".join(lines)
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_user"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_cancel_daily_reminder":
        user_id = user.id
        await db.delete_reminder(user_id, chat_id)
        jobs_removed = 0
        for job in context.job_queue.jobs():
            if job.name and job.name.startswith("daily_reminder_") and hasattr(job, 'data'):
                j_data = job.data
                if isinstance(j_data, dict) and j_data.get("user_id") == user_id and job.chat_id == chat_id:
                    job.schedule_removal()
                    jobs_removed += 1
        text = f"✅ تم إلغاء جميع تذكيراتك اليومية ({jobs_removed} تذكير)."
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_user"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== معالج الهمسة ====================
    if data.startswith("show_whisper_"):
        whisper_id = data.split("_")[2]
        user_id = update.effective_user.id
        whisper = context.bot_data.get(f'whisper_{whisper_id}')
        if not whisper:
            await query.answer("❌ هذه الهمسة غير متاحة (انتهت صلاحيتها).", show_alert=True)
            await msg.delete()
            return
        if user_id not in [whisper['sender_id'], whisper['target_id']]:
            await query.answer("❌ هذه الهمسة ليست لك!", show_alert=True)
            return
        await query.answer(f"💬 {whisper['text']}", show_alert=True)
        del context.bot_data[f'whisper_{whisper_id}']
        await msg.delete()
        return

    # ==================== الميديا والموارد ====================
    if data == "menu_media":
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main"),
             InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "🎵 **خدمات الميديا**\n"
            "• تيك شغال برابط\n"
            "• بحث ساوند شغال\n"
            "• انستا ويوتيوب مقفل مؤقتاً",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "menu_resources":
        keyboard = [
            [InlineKeyboardButton("📖 عرض الموارد", callback_data="exec_resources"),
             InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "📚 **الموارد:**\n• الموارد — عرض القائمة\n• أضف مورد — إضافة\n• احذف مورد — حذف",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    # ==================== أزرار تنفيذية (محمية) ====================
    if data == "exec_banlist":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        bans = await db.get_ban_list(chat_id)
        if not bans:
            text = "✅ لا يوجد محظورون حالياً"
        else:
            lines = [f"• {b['user_id']}" + (f" (ينتهي {b['expires_at'][:10]})" if b.get('expires_at') else " (دائم)") for b in bans[:20]]
            text = "🚫 **المحظورون:**\n" + "\n".join(lines)
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
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
                can_send_messages=True, can_send_polls=True,
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
            text = "📭 لا توجد أحداث مسجلة"
        else:
            lines = [f"• {e['action']} — {e['created_at'][:16]}" for e in events]
            text = "📋 **سجل الأحداث:**\n" + "\n".join(lines)
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_manage"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "exec_wordlist":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        words = await db.get_banned_words(chat_id)
        if not words:
            text = "✅ لا توجد كلمات محظورة"
        else:
            text = "🚫 **الكلمات المحظورة:**\n" + "\n".join(f"• {w}" for w in words)
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_manage"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "exec_report":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        from handlers.jobs import cmd_report
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
            text = f"🔗 **رابط دعوة:** {link.invite_link}"
        except:
            text = "❌ لا يمكن إنشاء رابط، تأكد من صلاحيات البوت."
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_purge":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        context.user_data['purge_mode'] = chat_id
        text = "📨 **أرسل عدد الرسائل أو رد على رسالة لمسح كل الرسائل بعدها.**"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "exec_broadcast":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        context.user_data['waiting_broadcast'] = chat_id
        text = "📢 **أرسل النص الذي تريد بثه للمجموعة:**"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return


    if data == "exec_mutelist":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        from handlers.admin import cmd_mutelist
        fake_update = FakeUpdate(msg)
        context.args = []
        await cmd_mutelist(fake_update, context)
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_manage"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        try:
            await msg.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            pass
        return

    if data == "exec_warnlist":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        from handlers.admin import cmd_warnlist
        fake_update = FakeUpdate(msg)
        context.args = []
        await cmd_warnlist(fake_update, context)
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_manage"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        try:
            await msg.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            pass
        return

    if data == "exec_weekly_report":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        from handlers.jobs import cmd_weekly_report_now
        fake_update = FakeUpdate(msg)
        context.args = []
        await cmd_weekly_report_now(fake_update, context)
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_manage"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text("✅ تم إرسال التقرير الأسبوعي.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

# ==================== دالة عرض نتيجة القفل مع زر الرجوع ====================
async def show_lock_result(msg, text, back_callback):
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data=back_callback),
                 InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
    await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
