import logging
import os
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

_conversation_history: dict[int, list] = {}
_user_model: dict[int, str] = {}
MAX_HISTORY = 10

async def ask_ai(user_id: int, question: str) -> str:
    model = _user_model.get(user_id, "llama")
    if model == "deepseek":
        url = "https://api.deepseek.com/v1/chat/completions"
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        model_name = "deepseek-chat"
        if not api_key:
            return "⚠️ مفتاح DeepSeek غير مضبوط."
    elif model == "gemini":
        # مؤقتاً: نموذج Gemini غير مفعل
        return "🌐 نموذج Gemini سيتم تفعيله قريباً."
    else:
        url = "https://api.groq.com/openai/v1/chat/completions"
        api_key = os.environ.get("GROQ_API_KEY", "")
        model_name = "llama-3.3-70b-versatile"
        if not api_key:
            return "⚠️ مفتاح Groq غير مضبوط."

    if user_id not in _conversation_history:
        _conversation_history[user_id] = [
            {
                "role": "system",
                "content": "أنت شفق، مساعد خليجي. تكلم بالعامية الخليجية السعودية. اختصر ردودك."
            }
        ]

    _conversation_history[user_id].append({"role": "user", "content": question})

    if len(_conversation_history[user_id]) > MAX_HISTORY:
        _conversation_history[user_id] = _conversation_history[user_id][-MAX_HISTORY:]

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model_name, "messages": _conversation_history[user_id], "max_tokens": 1024}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    return f"⚠️ خطأ من النموذج ({resp.status})"
                data = await resp.json()
                answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if answer:
                    _conversation_history[user_id].append({"role": "assistant", "content": answer})
                return answer or "لم أتلق إجابة."
    except Exception as e:
        logger.error(f"AI request failed: {e}")
        return "⚠️ تعذر الاتصال بالنموذج."

async def cmd_choose_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🦙 Llama (Groq)", callback_data="model_llama")],
        [InlineKeyboardButton("🐋 DeepSeek", callback_data="model_deepseek")],
        [InlineKeyboardButton("🌐 Gemini (قريباً)", callback_data="model_gemini")],
    ]
    await update.message.reply_text("اختر النموذج:", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_choose_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    if query.data == "model_llama":
        _user_model[user_id] = "llama"
        await query.edit_message_text("✅ تم اختيار Llama")
    elif query.data == "model_deepseek":
        _user_model[user_id] = "deepseek"
        await query.edit_message_text("✅ تم اختيار DeepSeek")
    elif query.data == "model_gemini":
        await query.edit_message_text("🌐 Gemini قيد التطوير")

async def cmd_shafaq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    if msg.reply_to_message and msg.reply_to_message.from_user.id == context.bot.id:
        question = msg.text.strip() if msg.text else ""
    else:
        question = " ".join(context.args).strip() if context.args else ""
    if not question:
        await msg.reply_text("اكتب سؤالك بعد شفق، مثال: شفق ما هو الذكاء؟")
        return
    thinking = await msg.reply_text("✨ شفق تفكر...")
    answer = await ask_ai(update.effective_user.id, question)
    await thinking.delete()
    await msg.reply_text(f"🌅 {answer}")

# ========== أمر جيمناي (نفس شفق لكن بنموذج مختلف) ==========
async def cmd_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    if msg.reply_to_message and msg.reply_to_message.from_user.id == context.bot.id:
        question = msg.text.strip() if msg.text else ""
    else:
        question = " ".join(context.args).strip() if context.args else ""
    if not question:
        await msg.reply_text("اكتب سؤالك بعد جيمناي، مثال: جيمناي ما هو الذكاء؟")
        return
    thinking = await msg.reply_text("✨ جيمناي يفكر...")
    # نغير النموذج مؤقتاً إلى gemini (تجريبي)
    user_id = update.effective_user.id
    old_model = _user_model.get(user_id, "llama")
    _user_model[user_id] = "gemini"
    answer = await ask_ai(user_id, question)
    _user_model[user_id] = old_model
    await thinking.delete()
    await msg.reply_text(f"🌐 {answer}")

# ========== أمر الحد (عرض النموذج الحالي) ==========
async def cmd_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    model = _user_model.get(user_id, "llama")
    model_name = "Llama (Groq)" if model == "llama" else "DeepSeek" if model == "deepseek" else model
    history_len = len(_conversation_history.get(user_id, []))
    await update.message.reply_text(
        f"📊 **إعدادات الذكاء:**\n"
        f"• النموذج: {model_name}\n"
        f"• عدد الرسائل المحفوظة: {history_len}/{MAX_HISTORY}\n"
        f"• غيّر النموذج عبر أمر 'موديل'"
    )