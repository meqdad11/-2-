import random
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# ==================== عرض قائمة الألعاب الرئيسية ====================
async def show_games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    msg = query.message
    keyboard = [
        [InlineKeyboardButton("🧩 تحديات وتفكير", callback_data="menu_games_thinking")],
        [InlineKeyboardButton("⚡ سرعة وحظ", callback_data="menu_games_speed")],
        [InlineKeyboardButton("🎯 ترفيهية سريعة", callback_data="menu_games_fun")],
        [InlineKeyboardButton("🏆 النقاط", callback_data="menu_games_points")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main"),
         InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
    ]
    await msg.edit_text("🎮 **الألعاب** — اختر القسم:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==================== النقاط المساعدة ====================
def get_points(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> int:
    return context.bot_data.setdefault("game_points", {}).get(user_id, 0)

def add_points(context: ContextTypes.DEFAULT_TYPE, user_id: int, amount: int):
    pts = context.bot_data.setdefault("game_points", {})
    pts[user_id] = pts.get(user_id, 0) + amount

def reset_points(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    pts = context.bot_data.setdefault("game_points", {})
    pts[user_id] = 0


# دوال بدء الألعاب عبر الرسائل النصية
async def start_guess_game(message, context):
    number = random.randint(1, 10)
    context.bot_data.setdefault("guess_numbers", {})[message.from_user.id] = number
    buttons = [
        [InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(6, 11)],
    ]
    await message.reply_text("🎲 خمن الرقم (1-10):", reply_markup=InlineKeyboardMarkup(buttons))

async def start_rps_game(message, context):
    keyboard = [
        [InlineKeyboardButton("🗻 حجر", callback_data="rps_rock"),
         InlineKeyboardButton("📄 ورقة", callback_data="rps_paper")],
        [InlineKeyboardButton("✂️ مقص", callback_data="rps_scissors")],
    ]
    await message.reply_text("✂️ حجر ورقة مقص - اختر:", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_bank_game(message, context):
    # نفس كود bank_menu لكن بدون query
    user = message.from_user
    last_claim = context.bot_data.setdefault("bank_last", {}).get(user.id)
    now = datetime.now()
    if last_claim and now - last_claim < timedelta(hours=12):
        remain = timedelta(hours=12) - (now - last_claim)
        hours, remainder = divmod(remain.seconds, 3600)
        minutes = remainder // 60
        await message.reply_text(f"⏳ يمكنك استلام الراتب كل 12 ساعة. متبقي {hours}h {minutes}m")
        return
    salary = random.randint(20, 100)
    add_points(context, user.id, salary)
    context.bot_data["bank_last"][user.id] = now
    keyboard = [[InlineKeyboardButton("💰 بخشيش", callback_data="bank_tip")]]
    await message.reply_text(f"🏦 **البنك**\nراتبك اليوم: {salary} نقطة.\nهل تريد بخشيش؟", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_slot_game(message, context):
    symbols = ["🍒", "🍋", "🍊", "🔔", "7️⃣"]
    result = [random.choice(symbols) for _ in range(3)]
    display = " | ".join(result)
    pts = 20 if len(set(result)) == 1 else 5 if len(set(result)) == 2 else 0
    if pts: add_points(context, message.from_user.id, pts)
    keyboard = [[InlineKeyboardButton("🔄 لف مرة أخرى", callback_data="slot_spin")]]
    await message.reply_text(f"{display}\n{'🎉 جاكبوت! +20' if pts==20 else '💰 جيد! +5' if pts==5 else '😕 لا شيء'}", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_dart_game(message, context):
    score = random.choices([50, 25, 10, 5, 1, 0], weights=[5, 10, 30, 30, 20, 5])[0]
    pts = score // 5 if score >= 25 else 0
    if pts: add_points(context, message.from_user.id, pts)
    keyboard = [[InlineKeyboardButton("🎯 ارمي مرة أخرى", callback_data="dart_throw")]]
    await message.reply_text(f"🎯 **{score} نقطة** {'(+'+str(pts)+' نقاط)' if pts else ''}", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_fastest_game(message, context):
    context.bot_data["fastest_game"] = {
        "chat_id": message.chat.id,
        "msg_id": None,
        "active": True,
        "start_time": time.time()
    }
    keyboard = [[InlineKeyboardButton("🏃 اضغط هنا بأسرع وقت!", callback_data="fastest_press")],
                [InlineKeyboardButton("❌ إلغاء", callback_data="fastest_cancel")]]
    await message.reply_text("🏃 **الأسرع!** أول من يضغط الزر يفوز.", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_cups_game(message, context):
    cups = ["🥛", "🍵", "🧃"]
    winning_cup = random.randint(0, 2)
    context.bot_data[f"cups_{message.chat.id}"] = winning_cup
    keyboard = [[InlineKeyboardButton(cups[i], callback_data=f"cups_choose_{i}") for i in range(3)]]
    await message.reply_text("🏺 **محيبس** — اختر الكوب الذي يخفي الخاتم:", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_roulette_game(message, context):
    names = ["الأسد", "النمر", "الفيل", "الغزال", "الثعلب", "الضبع", "الأرنب"]
    choice = random.choice(names)
    add_points(context, message.from_user.id, 2)
    keyboard = [[InlineKeyboardButton("🔄 لف مرة أخرى", callback_data="roulette_spin")]]
    await message.reply_text(f"🎡 **الروليت:**  ⟳  **{choice}**  (+2 نقطة)", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_judge_game(message, context):
    judgments = ["أنت شخص رائع 👍", "تحتاج شوية نوم 😴", "ستربح مليون نقطة 🔮", "لا تتأخر على العشاء 🍽", "اليوم يوم حظك 🍀", "ابتسم! 😄"]
    text = f"⚖️ **الحكم:** {random.choice(judgments)}"
    keyboard = [[InlineKeyboardButton("⚖️ حكم آخر", callback_data="judge_get")]]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def start_bowling_game(message, context):
    pins = random.choices([0,1,2,3,4,5,6,7,8,9,10], weights=[5,5,5,5,5,10,10,15,20,15,5])[0]
    add_points(context, message.from_user.id, pins)
    text = f"🎳 سقط {pins} قارورة! (+{pins} نقطة)"
    if pins == 10: text = "🎳 ضربة كاملة! 10 قوارير! (+10 نقاط)"
    keyboard = [[InlineKeyboardButton("🎳 ارمي مرة أخرى", callback_data="bowling_roll")]]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def start_dice_game(message, context):
    dice = random.randint(1, 6)
    add_points(context, message.from_user.id, dice)
    keyboard = [[InlineKeyboardButton("🎲 الف مرة أخرى", callback_data="dice_roll")]]
    await message.reply_text(f"🎲 **{dice}** (+{dice} نقطة)", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_football_game(message, context):
    keyboard = [
        [InlineKeyboardButton("↖️ يسار عالي", callback_data="foot_choice_up_left"),
         InlineKeyboardButton("⬆️ وسط عالي", callback_data="foot_choice_up_center"),
         InlineKeyboardButton("↗️ يمين عالي", callback_data="foot_choice_up_right")],
        [InlineKeyboardButton("⬅️ يسار أرضي", callback_data="foot_choice_low_left"),
         InlineKeyboardButton("⬇️ وسط أرضي", callback_data="foot_choice_low_center"),
         InlineKeyboardButton("➡️ يمين أرضي", callback_data="foot_choice_low_right")],
    ]
    await message.reply_text("⚽ اختر اتجاه التسديدة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_basketball_game(message, context):
    score = random.choices([3, 2, 0], weights=[30, 40, 30])[0]
    if score == 3:
        add_points(context, message.from_user.id, 5)
        text = "🏀 رمية ثلاثية! +5 نقاط"
    elif score == 2:
        add_points(context, message.from_user.id, 3)
        text = "🏀 نقطتين! +3 نقاط"
    else:
        text = "🏀 أخطأت السلة."
    keyboard = [[InlineKeyboardButton("🏀 ارمي مرة أخرى", callback_data="basketball_shot")]]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# قاموس الكلمات -> دوال البدء
GAME_STARTERS = {
    "تخمين": start_guess_game,
    "حجر": start_rps_game,
    "ورقة": start_rps_game,
    "مقص": start_rps_game,
    "بنك": start_bank_game,
    "البنك": start_bank_game,
    "سلوت": start_slot_game,
    "أرقام": start_slot_game,
    "سهم": start_dart_game,
    "الأسرع": start_fastest_game,
    "محيبس": start_cups_game,
    "روليت": start_roulette_game,
    "أحكام": start_judge_game,
    "بولينق": start_bowling_game,
    "بولينج": start_bowling_game,
    "نرد": start_dice_game,
    "زهر": start_dice_game,
    "ركلة": start_football_game,
    "كورة": start_football_game,
    "سلة": start_basketball_game,
}

async def handle_text_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text in GAME_STARTERS:
        await GAME_STARTERS[text](update.message, context)

# ==================== معالج جميع ضغطات أزرار الألعاب (تم تصحيح التوقيع) ====================
async def handle_games_callback(query, user, msg, context: ContextTypes.DEFAULT_TYPE):
    """يستقبل query, user, msg, context تماماً كما يُستدعى من بوتنز"""
    await query.answer()
    data = query.data
    chat_id = msg.chat.id

    # --- الأقسام الرئيسية ---
    if data == "menu_games_thinking":
        keyboard = [
            [InlineKeyboardButton("🎲 تخمين رقم (1-10)", callback_data="game_guess"),
             InlineKeyboardButton("✂️ حجر ورقة مقص", callback_data="game_rps")],
            [InlineKeyboardButton("🏦 البنك", callback_data="bank_menu"),
             InlineKeyboardButton("🎰 أرقام (سلوت)", callback_data="slot_spin")],
            [InlineKeyboardButton("🎯 سهم", callback_data="dart_throw")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_games"),
             InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("🧩 **تحديات وتفكير**", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_games_speed":
        keyboard = [
            [InlineKeyboardButton("🏃 الأسرع", callback_data="fastest_start"),
             InlineKeyboardButton("🏺 محيبس", callback_data="cups_start")],
            [InlineKeyboardButton("🎡 روليت", callback_data="roulette_spin"),
             InlineKeyboardButton("⚖️ أحكام", callback_data="judge_get")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_games"),
             InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("⚡ **سرعة وحظ**", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_games_fun":
        keyboard = [
            [InlineKeyboardButton("🎳 بولينق", callback_data="bowling_roll"),
             InlineKeyboardButton("🎲 نرد", callback_data="dice_roll")],
            [InlineKeyboardButton("⚽ الكورة (ركلة جزاء)", callback_data="football_kick"),
             InlineKeyboardButton("🏀 السلة", callback_data="basketball_shot")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_games"),
             InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("🎯 **ترفيهية سريعة**", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_games_points":
        pts = get_points(context, user.id)
        text = f"🏆 **نقاطك الحالية:** {pts}\n\nاستخدم الألعاب لتربح المزيد!"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_games"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== الألعاب القديمة ====================
    if data == "game_guess":
        number = random.randint(1, 10)
        context.bot_data.setdefault("guess_numbers", {})[user.id] = number
        buttons = [
            [InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(1, 6)],
            [InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(6, 11)],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_thinking")],
        ]
        await msg.edit_text("🎲 خمن الرقم (1-10):", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("guess_"):
        guessed = int(data.split("_")[1])
        correct = context.bot_data.get("guess_numbers", {}).get(user.id)
        if not correct:
            await query.answer("ابدأ لعبة جديدة أولاً", show_alert=True)
            return
        if guessed == correct:
            add_points(context, user.id, 5)
            text = f"🎉 **صحيح!** الرقم كان {correct}. ربحت 5 نقاط!"
            del context.bot_data["guess_numbers"][user.id]
        else:
            text = f"❌ خطأ! الرقم {guessed} ليس صحيحًا. حاول مرة أخرى."
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_thinking"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "game_rps":
        keyboard = [
            [InlineKeyboardButton("🗻 حجر", callback_data="rps_rock"),
             InlineKeyboardButton("📄 ورقة", callback_data="rps_paper")],
            [InlineKeyboardButton("✂️ مقص", callback_data="rps_scissors"),
             InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_thinking")],
        ]
        await msg.edit_text("اختر:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("rps_"):
        choice = data.split("_")[1]
        bot_choice = random.choice(["rock", "paper", "scissors"])
        choices_map = {"rock": "🗻 حجر", "paper": "📄 ورقة", "scissors": "✂️ مقص"}
        if choice == bot_choice:
            result = "🤝 تعادل"
            pts = 1
        elif (choice == "rock" and bot_choice == "scissors") or \
             (choice == "scissors" and bot_choice == "paper") or \
             (choice == "paper" and bot_choice == "rock"):
            result = "🎉 فزت! +3 نقاط"
            pts = 3
        else:
            result = "💔 خسرت!"
            pts = 0
        add_points(context, user.id, pts)
        text = f"اخترت: {choices_map[choice]}\nالبوت اختار: {choices_map[bot_choice]}\n\n{result}"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_thinking"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== بنك ====================
    if data == "bank_menu":
        last_claim = context.bot_data.setdefault("bank_last", {}).get(user.id)
        now = datetime.now()
        if last_claim and now - last_claim < timedelta(hours=12):
            remain = timedelta(hours=12) - (now - last_claim)
            hours, remainder = divmod(remain.seconds, 3600)
            minutes = remainder // 60
            await query.answer(f"يمكنك استلام الراتب كل 12 ساعة. متبقي {hours}h {minutes}m", show_alert=True)
            return
        salary = random.randint(20, 100)
        add_points(context, user.id, salary)
        context.bot_data["bank_last"][user.id] = now
        keyboard = [
            [InlineKeyboardButton("💰 بخشيش", callback_data="bank_tip")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_thinking")],
        ]
        await msg.edit_text(f"🏦 **البنك**\nراتبك اليوم: {salary} نقطة.\nهل تريد بخشيش؟", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "bank_tip":
        tip = random.randint(5, 30)
        add_points(context, user.id, tip)
        await msg.edit_text(f"🎁 حصلت على بخشيش: {tip} نقطة!\nإجمالي نقاطك: {get_points(context, user.id)}",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_thinking")]]))
        return

    # ==================== سلوت ====================
    if data == "slot_spin":
        symbols = ["🍒", "🍋", "🍊", "🔔", "7️⃣"]
        result = [random.choice(symbols) for _ in range(3)]
        display = " | ".join(result)
        if len(set(result)) == 1:
            pts = 20
            add_points(context, user.id, pts)
            msg_text = f"{display}\n🎉 جاكبوت! +{pts} نقطة"
        elif len(set(result)) == 2:
            pts = 5
            add_points(context, user.id, pts)
            msg_text = f"{display}\n💰 جيد! +{pts} نقاط"
        else:
            msg_text = f"{display}\n😕 لا شيء"
        keyboard = [[InlineKeyboardButton("🔄 لف مرة أخرى", callback_data="slot_spin"),
                     InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_thinking")]]
        await msg.edit_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== سهم ====================
    if data == "dart_throw":
        score = random.choices([50, 25, 10, 5, 1, 0], weights=[5, 10, 30, 30, 20, 5])[0]
        if score >= 25:
            pts = score // 5
            add_points(context, user.id, pts)
            text = f"🎯 **{score} نقطة!** (ربحت {pts} نقاط ألعاب)"
        else:
            text = f"🎯 **{score} نقطة** (حاول مرة)"
        keyboard = [[InlineKeyboardButton("🎯 ارمي مرة أخرى", callback_data="dart_throw"),
                     InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_thinking")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== الأسرع ====================
    if data == "fastest_start":
        context.bot_data.pop("fastest_winner", None)
        context.bot_data["fastest_game"] = {
            "chat_id": chat_id,
            "msg_id": msg.message_id,
            "active": True,
            "start_time": time.time()
        }
        keyboard = [[InlineKeyboardButton("🏃 اضغط هنا بأسرع وقت!", callback_data="fastest_press")],
                    [InlineKeyboardButton("❌ إلغاء", callback_data="fastest_cancel")]]
        await msg.edit_text("🏃 **الأسرع!** أول من يضغط الزر يفوز.",
                            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "fastest_press":
        game = context.bot_data.get("fastest_game")
        if not game or not game["active"]:
            await query.answer("انتهت اللعبة!", show_alert=True)
            return
        winner_name = user.full_name
        context.bot_data["fastest_game"]["active"] = False
        pts = 10
        add_points(context, user.id, pts)
        await msg.edit_text(f"🏆 **{winner_name}** هو الأسرع! +{pts} نقاط",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_speed")]]))
        return

    if data == "fastest_cancel":
        context.bot_data.pop("fastest_game", None)
        await msg.edit_text("تم إلغاء اللعبة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_speed")]]))
        return

    # ==================== محيبس (أكواب) ====================
    if data == "cups_start":
        cups = ["🥛", "🍵", "🧃"]
        winning_cup = random.randint(0, 2)
        context.bot_data[f"cups_{chat_id}"] = winning_cup
        keyboard = [
            [InlineKeyboardButton(cups[i], callback_data=f"cups_choose_{i}") for i in range(3)]
        ]
        await msg.edit_text("🏺 **محيبس** — اختر الكوب الذي يخفي الخاتم:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("cups_choose_"):
        cup_index = int(data.split("_")[2])
        winning = context.bot_data.get(f"cups_{chat_id}")
        if winning is None:
            await query.answer("انتهت اللعبة", show_alert=True)
            return
        cups_emoji = ["🥛", "🍵", "🧃"]
        if cup_index == winning:
            add_points(context, user.id, 3)
            text = f"💍 وجدت الخاتم في {cups_emoji[cup_index]}! +3 نقاط"
        else:
            text = f"❌ لا يوجد خاتم في {cups_emoji[cup_index]}. الخاتم كان في {cups_emoji[winning]}."
        context.bot_data.pop(f"cups_{chat_id}", None)
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_speed"),
                     InlineKeyboardButton("🔄 العب ثانية", callback_data="cups_start")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== روليت ====================
    if data == "roulette_spin":
        names = ["الأسد", "النمر", "الفيل", "الغزال", "الثعلب", "الضبع", "الأرنب"]
        choice = random.choice(names)
        add_points(context, user.id, 2)
        await msg.edit_text(f"🎡 **الروليت:**  ⟳  **{choice}**  (+2 نقطة)",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 لف مرة أخرى", callback_data="roulette_spin"),
                                                               InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_speed")]]))
        return

    # ==================== أحكام ====================
    if data == "judge_get":
        judgments = [
            "أنت شخص رائع 👍",
            "تحتاج شوية نوم 😴",
            "ستربح مليون نقطة 🔮",
            "لا تتأخر على العشاء 🍽",
            "اليوم يوم حظك 🍀",
            "ابتسم! 😄"
        ]
        text = f"⚖️ **الحكم:** {random.choice(judgments)}"
        keyboard = [[InlineKeyboardButton("⚖️ حكم آخر", callback_data="judge_get"),
                     InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_speed")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== بولينق ====================
    if data == "bowling_roll":
        pins = random.choices([0,1,2,3,4,5,6,7,8,9,10], weights=[5,5,5,5,5,10,10,15,20,15,5])[0]
        pts = pins
        add_points(context, user.id, pts)
        text = f"🎳 سقط {pins} قارورة! (+{pts} نقطة)"
        if pins == 10:
            text = "🎳 ضربة كاملة! 10 قوارير! (+10 نقاط)"
        keyboard = [[InlineKeyboardButton("🎳 ارمي مرة أخرى", callback_data="bowling_roll"),
                     InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_fun")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== نرد ====================
    if data == "dice_roll":
        dice = random.randint(1, 6)
        pts = dice
        add_points(context, user.id, pts)
        text = f"🎲 **{dice}**  (+{pts} نقطة)"
        keyboard = [[InlineKeyboardButton("🎲 الف مرة أخرى", callback_data="dice_roll"),
                     InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_fun")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== كرة قدم (ركلة جزاء) ====================
    if data == "football_kick":
        keyboard = [
            [InlineKeyboardButton("↖️ يسار عالي", callback_data="foot_choice_up_left"),
             InlineKeyboardButton("⬆️ وسط عالي", callback_data="foot_choice_up_center"),
             InlineKeyboardButton("↗️ يمين عالي", callback_data="foot_choice_up_right")],
            [InlineKeyboardButton("⬅️ يسار أرضي", callback_data="foot_choice_low_left"),
             InlineKeyboardButton("⬇️ وسط أرضي", callback_data="foot_choice_low_center"),
             InlineKeyboardButton("➡️ يمين أرضي", callback_data="foot_choice_low_right")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_fun")],
        ]
        await msg.edit_text("⚽ اختر اتجاه التسديدة:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("foot_choice_"):
        direction = data[len("foot_choice_"):]
        keeper = random.choice(["up_left", "up_center", "up_right", "low_left", "low_center", "low_right"])
        if direction == keeper:
            result = "🧤 الحارس تصدى! خسرت"
            pts = 0
        else:
            result = "⚽ هدف! +4 نقاط"
            pts = 4
        add_points(context, user.id, pts)
        keyboard = [[InlineKeyboardButton("⚽ العب مرة أخرى", callback_data="football_kick"),
                     InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_fun")]]
        await msg.edit_text(f"تسديدتك: {direction}\nالحارس: {keeper}\n{result}", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ==================== سلة ====================
    if data == "basketball_shot":
        score = random.choices([3, 2, 0], weights=[30, 40, 30])[0]
        if score == 3:
            add_points(context, user.id, 5)
            text = "🏀 رمية ثلاثية! +5 نقاط"
        elif score == 2:
            add_points(context, user.id, 3)
            text = "🏀 نقطتين! +3 نقاط"
        else:
            text = "🏀 أخطأت السلة."
        keyboard = [[InlineKeyboardButton("🏀 ارمي مرة أخرى", callback_data="basketball_shot"),
                     InlineKeyboardButton("🔙 رجوع", callback_data="menu_games_fun")]]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # لو لم يتعرف على اللعبة
    await query.answer("اللعبة غير متوفرة.", show_alert=True)