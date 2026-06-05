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

async def callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    msg = query.message
    chat_id = msg.chat.id

    # ========== إغلاق ==========
    if data == "menu_close":
        await msg.delete()
        return

    # ========== إحصائيات سريعة ==========
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

    if data == "exec_quote":
        text = f"💬 اقتباس اليوم:\n\n{random.choice(DAILY_QUOTES)}"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ========== المساعدة والتواصل (للجميع) ==========
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

    # ========== الألعاب (للجميع) ==========
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

    # ========== بحث جوجل (للجميع) ==========
    if data == "menu_google":
        context.user_data['waiting_google'] = chat_id
        text = "🔍 **أرسل ما تريد البحث عنه في جوجل:**"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    # ================= قائمة الأوامر المتقدمة =================
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

    # ========== أوامر القفل (للمشرفين فقط) ==========
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

    # ========== أوامر خدمية ==========
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

    # ========== نظام الأزمات ==========
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

    # ================= القائمة الرئيسية (ثنائية) =================
    if data == "menu_main":
        keyboard = [
            [InlineKeyboardButton("👮 أوامر المشرفين", callback_data="menu_admin"),
             InlineKeyboardButton("👥 للجميع", callback_data="menu_user")],
            [InlineKeyboardButton("🎵 الميديا", callback_data="menu_media"),
             InlineKeyboardButton("📚 الموارد", callback_data="menu_resources")],
            [InlineKeyboardButton("📊 إحصائيات", callback_data="exec_stats"),
             InlineKeyboardButton("💬 اقتباس اليوم", callback_data="exec_quote")],
            [InlineKeyboardButton("📋 تذكيراتي", callback_data="exec_my_reminders"),
             InlineKeyboardButton("❌ إلغاء تذكير يومي", callback_data="exec_cancel_daily_reminder")],
            [InlineKeyboardButton("📁 ملف", callback_data="exec_userfile"),
             InlineKeyboardButton("📜 سجل", callback_data="exec_eventlog")],
            [InlineKeyboardButton("📋 الأوامر", callback_data="menu_commands"),
             InlineKeyboardButton("🎮 ألعاب", callback_data="menu_games")],
            [InlineKeyboardButton("🔍 بحث جوجل", callback_data="menu_google"),
             InlineKeyboardButton("📢 قناة تحديثات شفق", url="https://t.me/shafaqmeqdad")],
            [InlineKeyboardButton("📞 تواصل", callback_data="menu_contact"),
             InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("🌅 بوت شفق — القائمة الرئيسية\nاختر القسم:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ========== قائمة المشرفين (بدون مساعدين) ==========
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

    # ... (بقية الكود كما هو بدون أي معالجات للمساعدين)

async def show_lock_result(msg, text, back_callback):
    """عرض نتيجة القفل مع زر الرجوع"""
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data=back_callback),
                 InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
    await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))