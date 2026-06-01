import logging
import os
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# ================================================
logger = logging.getLogger(__name__)
# ================================================

_conversation_history: dict[int, list] = {}
_user_model: dict[int, str] = {}
MAX_HISTORY = 10

# ================================================

async def ask_ai(user_id: int, question: str) -> str:
    model = _user_model.get(user_id, "llama")

    if model == "deepseek":
        url = "https://api.deepseek.com/v1/chat/completions"
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        model_name = "deepseek-chat"
        if not api_key:
            return "⚠️ مفتاح DeepSeek غير مضبوط في المتغيرات البيئية."
    elif model == "gemini":
        # مؤقتاً: نموذج Gemini غير مفعل، نرجع رسالة تجريبية
        return "🌐 نموذج Gemini سيتم تفعيله قريباً. حالياً استخدم 'شفق' أو غيره."
    else:
        url = "https://api.groq.com/openai/v1/chat/completions"
        api_key = os.environ.get("GROQ_API_KEY", "")
        model_name = "llama-3.3-70b-versatile"
        if not api_key:
            return "⚠️ مفتاح Groq غير مضبوط في المتغيرات البيئية."

    if user_id not in _conversation_history:
        _conversation_history[user_id] = [
            {
                "role": "system",
                "content": (
                    "أنت شفق، مساعد خليجي. تكلم دائماً بالعامية الخليجية السعودية مثل: والله، زين، إيه، ما أدري، شنو، ليش. "
                    "اختصر ردودك، ما تطوّل. "
                    "ممنوع تعطي أي نصيحة طبية، وإذا سألك أحد عن شي طبي قله: روح اسأل طبيب."
                )
            }
        ]

    _conversation_history[user_id].append({"role": "user", "content": question})

    if len(_conversation_history[user_id]) > MAX_HISTORY:
        _conversation_history[user_id] = _conversation_history[user_id][-MAX_HISTORY:]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": _conversation_history[user_id],
        "max_tokens": 1024,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error("AI error %s: %s", resp.status, text)
                    return f"⚠️ خطأ من النموذج ({resp.status}). حاول مرة أخرى."
                data = await resp.json()
                answer = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                if answer:
                    _conversation_history[user_id].append({"role": "assistant", "content": answer})
                return answer or "لم أتلقَّ إجابة من النموذج."
    except Exception as e:
        logger.error("AI request failed: %s", e)
        return "⚠️ تعذّر الاتصال بالنموذج. حاول لاحقاً."

# ================================================

async def cmd_choose_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🦙 Llama (Groq)", callback_data="model_llama")],
        [InlineKeyboardButton("🐋 DeepSeek", callback_data="model_deepseek")],
        [InlineKeyboardButton("🌐 Gemini (قريباً)", callback_data="model_gemini")],
    ]
    await update.message.reply_text(
        "اختر النموذج الي تبيه:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def callback_choose_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if query.data == "model_llama":
        _user_model[user_id] = "llama"
        await query.answer("تم اختيار Llama ✅")
        await query.edit_message_text("✅ تم اختيار نموذج **Llama (Groq)**", parse_mode="Markdown")
    elif query.data == "model_deepseek":
        _user_model[user_id] = "deepseek"
        await query.answer("تم اختيار DeepSeek ✅")
        await query.edit_message_text("✅ تم اختيار نموذج **DeepSeek**", parse_mode="Markdown")
    elif query.data == "model_gemini":
        await query.answer("نموذج Gemini قيد التطوير", show_alert=True)

# ================================================

async def cmd_shafaq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    is_reply_to_bot = (
        msg.reply_to_message and
        msg.reply_to_message.from_user and
        msg.reply_to_message.from_user.id == context.bot.id
    )

    if is_reply_to_bot:
        question = msg.text.strip() if msg.text else ""
    else:
        question = " ".join(context.args).strip() if context.args else ""

    if not question:
        await msg.reply_text("اكتب سؤالك بعد كلمة شفق.\nمثال: شفق ما هو الذكاء الاصطناعي؟")
        return

    user_id = update.effective_user.id
    thinking_msg = await msg.reply_text("✨ شفق تفكر...")
    answer = await ask_ai(user_id, question)

    try:
        await thinking_msg.delete()
    except Exception:
        pass

    await msg.reply_text(f"🌅 {answer}")

# ================================================
# ========== الأوامر الجديدة المضافة ==========
# ================================================

# أمر "جيمناي" (نسخة تجريبية)
async def cmd_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    is_reply_to_bot = (
        msg.reply_to_message and
        msg.reply_to_message.from_user and
        msg.reply_to_message.from_user.id == context.bot.id
    )

    if is_reply_to_bot:
        question = msg.text.strip() if msg.text else ""
    else:
        question = " ".join(context.args).strip() if context.args else ""

    if not question:
        await msg.reply_text("اكتب سؤالك بعد كلمة جيمناي.\nمثال: جيمناي ما هو الذكاء الاصطناعي؟")
        return

    user_id = update.effective_user.id
    # مؤقتاً نستخدم نفس نظام الأسئلة لكن مع إضافة تذكير بأنه نموذج تجريبي
    thinking_msg = await msg.reply_text("✨ جيمناي يفكر...")
    # نغير النموذج مؤقتاً إلى gemini (لكن الدالة سترجع رسالة تجريبية حالياً)
    old_model = _user_model.get(user_id, "llama")
    _user_model[user_id] = "gemini"
    answer = await ask_ai(user_id, question)
    _user_model[user_id] = old_model  # نعيد النموذج القديم
    try:
        await thinking_msg.delete()
    except Exception:
        pass
    await msg.reply_text(f"🌐 {answer}")

# أمر "الحد" (عرض النموذج الحالي)
async def cmd_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    model = _user_model.get(user_id, "llama")
    model_name = "Llama (Groq)" if model == "llama" else "DeepSeek" if model == "deepseek" else model
    history_count = len(_conversation_history.get(user_id, []))
    await update.message.reply_text(
        f"📊 **إعدادات الذكاء الاصطناعي:**\n"
        f"• النموذج الحالي: {model_name}\n"
        f"• عدد الرسائل المحفوظة: {history_count}/{MAX_HISTORY}\n"
        f"• يمكنك تغيير النموذج عبر أمر 'موديل'."
    )