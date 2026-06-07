import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# ==================== عرض قائمة الألعاب ====================
async def show_games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعرض أزرار الألعاب المتاحة (تُستدعى من قائمة البوت الرئيسية)."""
    query = update.callback_query
    msg = query.message
    keyboard = [
        [InlineKeyboardButton("🎲 تخمين رقم (1-10)", callback_data="game_guess"),
         InlineKeyboardButton("✂️ حجر ورقة مقص", callback_data="game_rps")],
        # أضف أزرار ألعاب جديدة هنا مستقبلاً
        [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main"),
         InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
    ]
    await msg.edit_text("🎮 **اختر لعبة:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==================== معالج جميع ضغطات أزرار الألعاب ====================
async def handle_games_callback(query, user, msg, context: ContextTypes.DEFAULT_TYPE):
    """يستقبل أي callback_data يبدأ بـ game_ / guess_ / rps_ ويعالج اللعبة المناسبة."""
    data = query.data

    # --- لعبة تخمين الرقم ---
    if data == "game_guess":
        number = random.randint(1, 10)
        context.bot_data.setdefault("guess_numbers", {})[user.id] = number
        buttons = [
            [InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(1, 6)],
            [InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(6, 11)],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_games")],
        ]
        await msg.edit_text("🎲 خمن الرقم (1-10):", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("guess_"):
        guessed = int(data.split("_")[1])
        correct = context.bot_data.get("guess_numbers", {}).get(user.id)
        if not correct:
            await query.answer("ابدأ لعبة جديدة من القائمة أولاً", show_alert=True)
            return
        if guessed == correct:
            text = f"🎉 **صحيح!** الرقم كان {correct}. تهانينا!"
            del context.bot_data["guess_numbers"][user.id]
        else:
            text = f"❌ خطأ! الرقم {guessed} ليس صحيحًا. حاول مرة أخرى."
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_games"),
             InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]
        ]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    # --- لعبة حجر ورقة مقص ---
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
        bot_choice = random.choice(["rock", "paper", "scissors"])
        choices_map = {"rock": "🗻 حجر", "paper": "📄 ورقة", "scissors": "✂️ مقص"}
        user_choice_text = choices_map.get(choice, choice)
        bot_choice_text = choices_map.get(bot_choice, bot_choice)

        if choice == bot_choice:
            result = "🤝 تعادل"
        elif (choice == "rock" and bot_choice == "scissors") or \
             (choice == "scissors" and bot_choice == "paper") or \
             (choice == "paper" and bot_choice == "rock"):
            result = "🎉 فزت!"
        else:
            result = "💔 خسرت!"

        text = f"اخترت: {user_choice_text}\nالبوت اختار: {bot_choice_text}\n\n{result}"
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_games"),
             InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")]
        ]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # لو لم يتعرف على اللعبة (لأي أزرار ألعاب جديدة سنضيفها لاحقاً)
    await query.answer("اللعبة غير متوفرة حالياً.", show_alert=True)