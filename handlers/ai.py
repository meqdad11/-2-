import logging
import os
import json
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import aiohttp

from utils import database as db
from utils.helpers import is_admin

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "أنت 'شفق'، مساعد ذكي مفيد ومهذب. مهمتك هي تقديم إجابات دقيقة ومفيدة باللغة العربية الفصحى المختصرة. يجب أن تلتزم بالحقائق. إذا سُئلت عن شيء لا تعرفه أو كان خارج نطاق معرفتك، يجب أن تعتذر بلطف وتقول 'لا أعلم' بدلاً من تخمين إجابة. لا تؤلف معلومات. كن مباشرًا وواضحًا."

INTENT_SYSTEM_PROMPT = """أنت محلل نوايا لبوت تيليجرام. مهمتك تحليل رسالة المستخدم وإرجاع JSON فقط بدون أي نص إضافي.

الـ intents المتاحة:
- reminder, daily_reminder, cancel_reminder, my_reminders
- ban, unban, mute, unmute, warn, report, deep_report
- pin, unpin, list_admins, my_rank, rules, id, stats
- need_someone, event_log, user_warnings, banned_words, crisis_toggle
- group_mood, group_summary, group_search
- none

صيغة الرد JSON:
{"intent": "...", "minutes": null, "time": null, "text": null, "target": null, "duration": null, "enabled": null}

قواعد: أرجع JSON فقط بدون أي كلام. إذا لم تكن متأكداً أرجع intent: none."""

MODELS = {
    "llama": {"name": "LLaMA 3 (Groq)", "url": "https://api.groq.com/openai/v1/chat/completions", "key_env": "GROQ_API_KEY", "model_name": "llama-3.3-70b-versatile"},
    "cerebras": {"name": "Cerebras (Llama 3.3)", "url": "https://api.cerebras.ai/v1/chat/completions", "key_env": "CEREBRAS_API_KEY", "model_name": "llama-3.3-70b"},
    "openrouter": {"name": "OpenRouter", "url": "https://openrouter.ai/api/v1/chat/completions", "key_env": "OPENROUTER_API_KEY", "model_name": "mistralai/mistral-7b-instruct:free"},
    "deepseek": {"name": "DeepSeek", "url": "https://api.deepseek.com/v1/chat/completions", "key_env": "DEEPSEEK_API_KEY", "model_name": "deepseek-chat"},
    "gemini": {"name": "Gemini", "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent", "key_env": "GEMINI_API_KEY"},
    "sambanova": {"name": "SambaNova (Llama 3.1)", "url": "https://api.sambanova.ai/v1/chat/completions", "key_env": "SAMBANOVA_API_KEY", "model_name": "Meta-Llama-3.1-8B-Instruct"},
    "openai": {"name": "OpenAI GPT", "url": "https://api.openai.com/v1/chat/completions", "key_env": "OPENAI_API_KEY", "model_name": "gpt-3.5-turbo"},
}

def _get_available_models():
    available = {}
    for key, model in MODELS.items():
        if os.environ.get(model["key_env"]):
            available[key] = model
    return available

async def cmd_choose_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    available = _get_available_models()
    if context.args:
        choice = context.args[0].lower()
        if choice not in MODELS:
            await update.message.reply_text("❌ النموذج غير معروف.")
            return
        if choice not in available:
            await update.message.reply_text(f"❌ النموذج {MODELS[choice]['name']} غير مفعّل.")
            return
        context.user_data["ai_model"] = choice
        await update.message.reply_text(f"✅ تم اختيار نموذج {MODELS[choice]['name']}")
        return
    if not available:
        await update.message.reply_text("❌ لا توجد نماذج ذكاء اصطناعي مفعّلة حالياً.")
        return
    keyboard = [[InlineKeyboardButton(model["name"], callback_data=f"model_{key}")] for key, model in available.items()]
    await update.message.reply_text("🧠 اختر نموذج الذكاء الاصطناعي:", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_choose_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data.split("_")[1]
    available = _get_available_models()
    if choice not in available:
        await query.message.edit_text("❌ هذا النموذج غير متاح حالياً.")
        return
    context.user_data["ai_model"] = choice
    await query.message.edit_text(f"✅ النموذج: {MODELS[choice]['name']}")

async def _call_ai(model_key: str, messages: list) -> str:
    model = MODELS[model_key]
    api_key = os.environ.get(model["key_env"])
    if not api_key:
        return f"❌ مفتاح API غير موجود ({model['key_env']})."
    headers = {"Content-Type": "application/json"}
    if model_key == "gemini":
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        url = f"{model['url']}?key={api_key}"
    else:
        payload = {"model": model.get("model_name", "default"), "messages": messages, "temperature": 0.7, "max_tokens": 2048}
        headers["Authorization"] = f"Bearer {api_key}"
        if model_key == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/shafaq-bot"
            headers["X-Title"] = "Shafaq Bot"
        url = model["url"]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"AI API error: {resp.status} {text}")
                    return "❌ خطأ من خدمة الذكاء الاصطناعي."
                data = await resp.json()
                if model_key == "gemini":
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI call error: {e}")
        return "❌ تعذر الاتصال بالذكاء الاصطناعي."

_rate_limit_store: dict = {}

def _check_rate_limit(user_id: int, max_commands: int = 10, window_seconds: int = 60) -> bool:
    import time
    now = time.time()
    timestamps = _rate_limit_store.get(user_id, [])
    timestamps = [t for t in timestamps if now - t < window_seconds]
    if len(timestamps) >= max_commands:
        _rate_limit_store[user_id] = timestamps
        return True
    timestamps.append(now)
    _rate_limit_store[user_id] = timestamps
    return False

def _parse_arabic_time(text: str):
    patterns = [
        (r"ربع ساعة", 15), (r"نص ساعة|نصف ساعة", 30),
        (r"ثلاثة أرباع ساعة", 45), (r"ساعة ونص|ساعة ونصف", 90),
        (r"ساعتين", 120), (r"(\d+)\s*ساعة", None),
        (r"(\d+)\s*دقيقة|(\d+)\s*دقائق", None),
        (r"بعد شوي|بعد قليل", 5),
    ]
    for pattern, value in patterns:
        match = re.search(pattern, text.strip())
        if match:
            if value is not None:
                return value
            num = int(next(g for g in match.groups() if g))
            return num * 60 if "ساعة" in pattern else num
    return None

async def _detect_intent(user_input: str, model_key: str) -> dict:
    intent_model = "llama" if os.environ.get("GROQ_API_KEY") else model_key
    messages = [{"role": "system", "content": INTENT_SYSTEM_PROMPT}, {"role": "user", "content": user_input}]
    try:
        raw = await _call_ai(intent_model, messages)
        raw = re.sub(r"```json|```", "", raw).strip()
        result = json.loads(raw)
        if result.get("intent") == "reminder" and not result.get("minutes"):
            arabic_minutes = _parse_arabic_time(user_input)
            if arabic_minutes:
                result["minutes"] = arabic_minutes
        return result
    except Exception as e:
        logger.error(f"Intent detection error: {e}")
        return {"intent": "none"}


# ========== ملخص المجموعة (وش فاتني) ==========
async def cmd_group_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = update.effective_chat

    if chat.type not in ("group", "supergroup"):
        await msg.reply_text("⚠️ هذا الأمر للمجموعات فقط.")
        return

    if await db.is_locked(chat.id, "ai"):
        await msg.reply_text("🚫 الذكاء الاصطناعي مقفل في هذه المجموعة.")
        return

    messages = await db.get_group_messages(chat.id, 100)
    if not messages or len(messages) < 5:
        await msg.reply_text("💬 ما في رسائل كافية بعد للتلخيص (أقل من 5 رسائل).")
        return

    thinking = await msg.reply_text("⏳ ألخص اللي فاتك...")
    convo = "\n".join([f"{m['user_name']}: {m['message_text']}" for m in messages])
    model_key = context.user_data.get("ai_model", "llama")
    result = await _call_ai(model_key, [
        {"role": "system", "content": "أنت ملخص محادثات ذكي. ردك مختصر ومفيد وبالعربي. لخّص أهم ما دار في المحادثة، اذكر المواضيع الرئيسية والقرارات المهمة إن وجدت. لا تذكر كل رسالة."},
        {"role": "user", "content": f"لخّص هذه المحادثة:\n{convo[:4000]}"}
    ])
    try:
        await thinking.delete()
    except:
        pass
    await msg.reply_text(f"📋 **ملخص المحادثة:**\n\n{result}", parse_mode="Markdown")


# ========== مزاج المجموعة ==========
async def cmd_group_mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = update.effective_chat

    if chat.type not in ("group", "supergroup"):
        await msg.reply_text("⚠️ هذا الأمر للمجموعات فقط.")
        return

    if await db.is_locked(chat.id, "ai"):
        await msg.reply_text("🚫 الذكاء الاصطناعي مقفل في هذه المجموعة.")
        return

    messages = await db.get_group_messages(chat.id, 50)
    if not messages or len(messages) < 5:
        await msg.reply_text("💬 ما في رسائل كافية بعد لتحليل المزاج.")
        return

    thinking = await msg.reply_text("⏳ أحلل مزاج المجموعة...")
    convo = "\n".join([f"{m['user_name']}: {m['message_text']}" for m in messages])
    model_key = context.user_data.get("ai_model", "llama")
    result = await _call_ai(model_key, [
        {"role": "system", "content": "أنت محلل نفسي للمحادثات. ردك جملتين مختصرتين وبالعربي. حلّل المزاج العام والموضوع السائد واستخدم إيموجي مناسب."},
        {"role": "user", "content": f"حلّل مزاج هذه المحادثة:\n{convo[:3000]}"}
    ])
    try:
        await thinking.delete()
    except:
        pass
    await msg.reply_text(f"🌡️ **مزاج المجموعة:**\n\n{result}", parse_mode="Markdown")


# ========== بحث في رسائل المجموعة ==========
async def cmd_group_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = update.effective_chat

    if chat.type not in ("group", "supergroup"):
        await msg.reply_text("⚠️ هذا الأمر للمجموعات فقط.")
        return

    if not context.args:
        await msg.reply_text("الاستخدام: `دور على [كلمة]`\nمثال: دور على اجتماع", parse_mode="Markdown")
        return

    keyword = " ".join(context.args)
    results = await db.search_group_messages(chat.id, keyword, 10)
    if not results:
        await msg.reply_text(f"🔍 ما لقيت رسائل تحتوي على: **{keyword}**", parse_mode="Markdown")
        return

    lines = [f"• **{r['user_name']}:** {r['message_text'][:100]} _({r['created_at'][11:16]})_" for r in results]
    await msg.reply_text(
        f"🔍 **نتائج البحث عن '{keyword}'** ({len(results)} رسالة):\n\n" + "\n".join(lines),
        parse_mode="Markdown"
    )


# ========== أمر شفق (نقطة الدخول الرئيسية) ==========
async def cmd_shafaq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user
    chat = update.effective_chat

    if msg.reply_to_message and msg.reply_to_message.from_user and msg.reply_to_message.from_user.is_bot:
        user_input = msg.text
        is_continuation = True
    elif msg.text.startswith("شفق "):
        user_input = msg.text.split("شفق ", 1)[1].strip()
        is_continuation = False
    elif msg.text.startswith("شوشو "):
        user_input = msg.text.split("شوشو ", 1)[1].strip()
        is_continuation = False
    else:
        return

    if not user_input:
        await msg.reply_text("⚠️ اكتب شيئًا بعد 'شفق'.")
        return

    if chat.type in ("group", "supergroup") and await db.is_locked(chat.id, "ai"):
        await msg.reply_text("🚫 الذكاء الاصطناعي مقفل في هذه المجموعة.")
        return

    if _check_rate_limit(user.id):
        await msg.reply_text("⏱️ أرسلت أوامر كثيرة، انتظر دقيقة ثم حاول.")
        return

    model_key = context.user_data.get("ai_model", "llama")

    if not is_continuation:
        await db.delete_conversation(user.id, chat.id)
        history = [{"role": "system", "content": SYSTEM_PROMPT}]
    else:
        history = await db.get_conversation(user.id, chat.id)
        if not history:
            history = [{"role": "system", "content": SYSTEM_PROMPT}]

    history.append({"role": "user", "content": user_input})
    await msg.reply_chat_action("typing")
    reply_text = await _call_ai(model_key, history)
    history.append({"role": "assistant", "content": reply_text})
    await db.save_conversation(user.id, chat.id, history)
    await msg.reply_text(reply_text, parse_mode="Markdown")


# ========== معالجة الردود على رسائل البوت الذكية ==========
async def handle_ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.reply_to_message:
        return False
    replied_msg = msg.reply_to_message
    if not replied_msg.from_user or not replied_msg.from_user.is_bot:
        return False
    chat = update.effective_chat
    if chat.type in ("group", "supergroup") and await db.is_locked(chat.id, "ai"):
        return False
    history = await db.get_conversation(msg.from_user.id, msg.chat.id)
    if not history:
        return False
    user_input = msg.text
    if not user_input:
        return False
    model_key = context.user_data.get("ai_model", "llama")
    history.append({"role": "user", "content": user_input})
    await msg.reply_chat_action("typing")
    reply_text = await _call_ai(model_key, history)
    history.append({"role": "assistant", "content": reply_text})
    await db.save_conversation(msg.from_user.id, msg.chat.id, history)
    await msg.reply_text(reply_text, parse_mode="Markdown")
    return True


async def cmd_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ai_model"] = "gemini"
    await update.message.reply_text("✅ تم اختيار Gemini")

async def cmd_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("الحدود غير مفعلة حاليًا.")
