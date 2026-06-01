import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes
import database as db
from helpers import is_admin

logger = logging.getLogger(__name__)

# متغيرات مؤقتة
temp_points = {}
temp_games = {}

# ================================================
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👮 أوامر المشرفين", callback_data="menu_admin")],
        [InlineKeyboardButton("👥 للجميع", callback_data="menu_user")],
        [InlineKeyboardButton("🎵 الميديا", callback_data="menu_media")],
        [InlineKeyboardButton("📚 الموارد", callback_data="menu_resources")],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="exec_stats")],
        [InlineKeyboardButton("💬 اقتباس اليوم", callback_data="exec_quote")],
        [InlineKeyboardButton("❓ المساعدة", callback_data="menu_help")],
        [InlineKeyboardButton("📞 تواصل", callback_data="menu_contact")],
        [InlineKeyboardButton("🎮 ألعاب", callback_data="menu_games")],
        [InlineKeyboardButton("🔍 بحث جوجل", callback_data="menu_google")],
        [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
    ]
    await update.message.reply_text(
        "🌅 بوت شفق — القائمة الرئيسية\nاختر:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================================================
async def callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    msg = query.message

    # إغلاق
    if data == "menu_close":
        await msg.delete()
        return

    # إحصائيات المجموعة
    if data == "exec_stats":
        chat_id = msg.chat.id
        try:
            members_count = await context.bot.get_chat_member_count(chat_id)
            admins = await context.bot.get_chat_administrators(chat_id)
            admins_count = len(admins)
            await msg.reply_text(f"📊 الأعضاء: {members_count}\n👮 المشرفون: {admins_count}")
        except:
            await msg.reply_text("لا يمكن جلب الإحصائيات.")
        return

    # اقتباس اليوم
    if data == "exec_quote":
        quotes = ["🌟 لا تؤجل عمل اليوم.", "💪 النجاح بالإصرار.", "🧠 تعلم كل يوم.", "😊 ابتسم."]
        await msg.reply_text(f"💬 اقتباس اليوم:\n{random.choice(quotes)}")
        return

    # المساعدة
    if data == "menu_help":
        await msg.reply_text(
            "❓ الأوامر:\n/start - القائمة\n/id - معرفك\n/rules - القواعد\n/report - بلاغ\n/ban - حظر\n/unban - رفع الحظر\n/mute - كتم\n/unmute - رفع الكتم"
        )
        return

    # تواصل مع المطور
    if data == "menu_contact":
        await msg.reply_text("📞 [المطور](https://t.me/Me8dad)", parse_mode="Markdown", disable_web_page_preview=True)
        return

    # ألعاب
    if data == "menu_games":
        keyboard = [
            [InlineKeyboardButton("🎲 تخمين رقم", callback_data="game_guess")],
            [InlineKeyboardButton("✂️ حجر ورقة مقص", callback_data="game_rps")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
        ]
        await msg.edit_text("🎮 اختر لعبة:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # لعبة التخمين
    if data == "game_guess":
        number = random.randint(1, 10)
        temp_games[user.id] = number
        buttons = [[InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(1,6)],
                   [InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(6,11)]]
        await msg.reply_text("خمن رقمًا:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("guess_"):
        guessed = int(data.split("_")[1])
        correct = temp_games.get(user.id)
        if correct is None:
            await query.answer("ابدأ لعبة جديدة أولاً")
            return
        if guessed == correct:
            await msg.reply_text(f"🎉 صحيح! الرقم {correct}")
            del temp_games[user.id]
        else:
            await msg.reply_text(f"❌ خطأ، حاول مرة أخرى.")
        return

    # حجر ورقة مقص
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
        win = (choice == 'rock' and bot_choice == 'scissors') or \
              (choice == 'scissors' and bot_choice == 'paper') or \
              (choice == 'paper' and bot_choice == 'rock')
        result = "🎉 فزت!" if win else "💔 خسرت!" if choice != bot_choice else "🤝 تعادل"
        await msg.reply_text(f"أنت: {choice}\nالبوت: {bot_choice}\n{result}")
        return

    # بحث جوجل
    if data == "menu_google":
        context.user_data['waiting_google'] = msg.chat.id
        await msg.reply_text("🔍 أرسل ما تريد البحث عنه:")
        return

    # معلوماتي (بدون استدعاء cmd_id من ملف آخر)
    if data == "exec_id":
        user_id = user.id
        first = user.first_name or ""
        username = f"@{user.username}" if user.username else ""
        await msg.reply_text(f"🪪 اسمك: {first}\nالمعرف: {user_id}\n{username}")
        return

    # القواعد (بدون cmd_rules)
    if data == "exec_rules":
        chat_id = msg.chat.id
        rules = await db.get_setting(chat_id, "rules")
        if rules:
            await msg.reply_text(f"📋 القواعد:\n{rules}")
        else:
            await msg.reply_text("لا توجد قواعد بعد.")
        return

    # باقي الأقسام (مختصرة)
    if data == "menu_main":
        await cmd_menu(update, context)  # يعيد عرض القائمة لكن يجب إعادة توجيهها
        # بدلاً من ذلك نستخدم edit:
        keyboard = [
            [InlineKeyboardButton("👮 أوامر المشرفين", callback_data="menu_admin")],
            [InlineKeyboardButton("👥 للجميع", callback_data="menu_user")],
            [InlineKeyboardButton("🎵 الميديا", callback_data="menu_media")],
            [InlineKeyboardButton("📚 الموارد", callback_data="menu_resources")],
            [InlineKeyboardButton("📊 إحصائيات", callback_data="exec_stats")],
            [InlineKeyboardButton("💬 اقتباس اليوم", callback_data="exec_quote")],
            [InlineKeyboardButton("❓ المساعدة", callback_data="menu_help")],
            [InlineKeyboardButton("📞 تواصل", callback_data="menu_contact")],
            [InlineKeyboardButton("🎮 ألعاب", callback_data="menu_games")],
            [InlineKeyboardButton("🔍 بحث جوجل", callback_data="menu_google")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("🌅 القائمة الرئيسية:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # أوامر المشرفين (مختصرة، يمكنك توسيعها)
    if data == "menu_admin":
        keyboard = [
            [InlineKeyboardButton("🚫 الحظر", callback_data="menu_ban")],
            [InlineKeyboardButton("🔇 الكتم", callback_data="menu_mute")],
            [InlineKeyboardButton("⚙️ إدارة", callback_data="menu_manage")],
            [InlineKeyboardButton("🔗 رابط دعوة", callback_data="exec_invite")],
            [InlineKeyboardButton("🗑️ مسح رسائل", callback_data="exec_purge")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
        ]
        await msg.edit_text("👮 المشرفين:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_user":
        keyboard = [
            [InlineKeyboardButton("🪪 معلوماتي", callback_data="exec_id")],
            [InlineKeyboardButton("📋 القواعد", callback_data="exec_rules")],
            [InlineKeyboardButton("📚 الموارد", callback_data="exec_resources")],
            [InlineKeyboardButton("🎁 هدية", callback_data="exec_gift")],
            [InlineKeyboardButton("⏰ تذكير", callback_data="exec_remind")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
        ]
        await msg.edit_text("👥 للجميع:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # اختصارات سريعة
    if data == "exec_resources":
        chat_id = msg.chat.id
        from handlers_resources import _get_resources
        resources = await _get_resources(chat_id)
        if not resources:
            await msg.reply_text("لا توجد موارد.")
        else:
            lines = [f"{i}. {r['title']}" for i, r in enumerate(resources[:10], 1)]
            await msg.reply_text("📚 الموارد:\n" + "\n".join(lines))
        return

    if data == "exec_gift":
        points = random.randint(1, 10)
        temp_points[user.id] = temp_points.get(user.id, 0) + points
        await msg.reply_text(f"🎁 حصلت على {points} نقطة! إجماليك {temp_points[user.id]}")
        return

    if data == "exec_remind":
        await msg.reply_text("أرسل عدد الدقائق والنص (مثال: 5 تذكير)")
        context.user_data['waiting_remind'] = msg.chat.id
        return

    if data == "exec_invite":
        if not await is_admin(update, context):
            await query.answer("للمشرفين فقط", show_alert=True)
            return
        link = await context.bot.create_chat_invite_link(msg.chat.id, member_limit=1)
        await msg.reply_text(f"🔗 رابط: {link.invite_link}")
        return

    if data == "exec_purge":
        await msg.reply_text("أرسل عدد الرسائل أو رد على رسالة")
        context.user_data['purge_mode'] = msg.chat.id
        return

    # إلخ ... يمكنك إضافة باقي القوائم بنفس الأسلوب

# معالج الرسائل التفاعلية (مسح، تذكير، بحث)
async def handle_interactive_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    text = msg.text.strip()
    user_id = msg.from_user.id
    chat_id = msg.chat.id

    # بحث جوجل
    if context.user_data.get('waiting_google') == chat_id:
        del context.user_data['waiting_google']
        query = text.replace(' ', '+')
        link = f"https://www.google.com/search?q={query}"
        await msg.reply_text(f"🔍 [نتائج البحث]({link})", parse_mode="Markdown", disable_web_page_preview=True)
        return

    # مسح الرسائل
    if context.user_data.get('purge_mode') == chat_id:
        del context.user_data['purge_mode']
        if text.isdigit():
            count = int(text)
            if count > 100:
                await msg.reply_text("الحد الأقصى 100")
                return
            try:
                for i in range(count):
                    await context.bot.delete_message(chat_id, msg.message_id - i - 1)
            except:
                pass
            await msg.reply_text(f"🗑️ تم مسح {count} رسالة")
        elif msg.reply_to_message:
            start_id = msg.reply_to_message.message_id
            for mid in range(start_id, msg.message_id):
                try:
                    await context.bot.delete_message(chat_id, mid)
                except:
                    pass
            await msg.reply_text("🗑️ تم المسح")
        else:
            await msg.reply_text("أرسل رقمًا أو رد على رسالة")
        return

    # تذكير
    if context.user_data.get('waiting_remind') == chat_id:
        del context.user_data['waiting_remind']
        parts = text.split(maxsplit=1)
        if len(parts) != 2 or not parts[0].isdigit():
            await msg.reply_text("الصيغة: 5 التذكير")
            return
        minutes = int(parts[0])
        delay = minutes * 60
        if delay > 86400:
            await msg.reply_text("أكثر من يوم غير مسموح")
            return
        context.job_queue.run_once(lambda ctx: ctx.bot.send_message(chat_id, f"⏰ تذكير: {parts[1]}"), delay)
        await msg.reply_text(f"✅ تم التذكير بعد {minutes} دقيقة")
        return