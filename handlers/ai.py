import logging
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import aiohttp

from utils import database as db

logger = logging.getLogger(__name__)

# ========== إعدادات النماذج ==========
MODELS = {
    "deepseek": {
        "name": "DeepSeek",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "key_env": "DEEPSEEK_API_KEY",
        "model_name": "deepseek-chat",
    },
    "gemini": {
        "name": "Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent",
        "key_env": "GEMINI_API_KEY",
    },
    "llama": {
        "name": "LLaMA 3.3 (Groq)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "model_name": "llama-3.3-70b-versatile",
    },
    "llama4": {
        "name": "LLaMA 4 Scout (Groq)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
    },
    "qwen": {
        "name": "Qwen 3 (Groq)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "model_name": "qwen/qwen3-32b",
    },
    "sambanova": {
        "name": "SambaNova (Llama 3.1)",
        "url": "https://api.sambanova.ai/v1/chat/completions",
        "key_env": "SAMBANOVA_API_KEY",
        "model_name": "Meta-Llama-3.1-8B-Instruct",
    },
}

# ========== System Prompt ==========
SYSTEM_PROMPT = """/no_think
أنت شفق، مساعد ذكي ومهذب يتحدث العربية فقط.
- رد دائماً بالعربية بغض النظر عن لغة السؤال
- إذا سألك أحد "كيفك" أو "كيف حالك" فأجب بشكل ودي طبيعي
- اجعل ردودك مختصرة ومفيدة
- لا تفكر بصوت عالٍ ولا تكتب تفكيرك، فقط الجواب النهائي
- لا تستخدم وسوم مثل <think> أو </think>"""

# ========== عدد الرسائل المحفوظة في الذاكرة ==========
MAX_HISTORY = 10

# ========== كلمات تدل على رسائل البوت غير الذكاء ==========
BOT_NON_AI_PREFIXES = (
    "📱", "⏳", "✅", "❌", "🔗", "📥", "📤", "🎵", "🎬",
    "/download", "تم إرسال", "بدأ التحميل", "اكتمل التحميل",
)

# ========== دالة تقليص السياق ==========
def _trim_history(history: list) -> list:
    system_msgs = [m for m in history if m["role"] == "system"]
    other_msgs = [m for m in history if m["role"] != "system"]
    if len(other_msgs) > MAX_HISTORY:
        other_msgs = other_msgs[-MAX_HISTORY:]
    return system_msgs + other_msgs

# ========== هل رسالة البوت من محادثة ذكاء؟ ==========
def _is_ai_message(text: str) -> bool:
    if not text:
        return False
    for prefix in BOT_NON_AI_PREFIXES:
        if text.startswith(prefix):
            return False
    return True

# ========== دالة مساعدة: النماذج المتاحة فقط ==========
def _get_available_models():
    available = {}
    for key, model in MODELS.items():
        if os.environ.get(model["key_env"]):
            available[key] = model
    return available

# ========== اختيار النموذج ==========
async def cmd_choose_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    available = _get_available_models()

    if context.args:
        choice = context.args[0].lower()
        if choice not in MODELS:
            await update.message.reply_text("❌ النموذج غير معروف.")
            return
        if choice not in available:
            await update.message.reply_text(f"❌ النموذج {MODELS[choice]['name']} غير مفعّل (لا يوجد مفتاح API).")
            return
        context.user_data["ai_model"] = choice
        await update.message.reply_text(f"✅ تم اختيار نموذج {MODELS[choice]['name']}")
        return

    if not available:
        await update.message.reply_text("❌ لا توجد نماذج ذكاء اصطناعي مفعّلة حالياً.")
        return

    keyboard = []
    for key, model in available.items():
        keyboard.append([InlineKeyboardButton(model["name"], callback_data=f"model_{key}")])
    await update.message.reply_text(
        "🧠 اختر نموذج الذكاء الاصطناعي:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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

# ========== مسح محادثة الذكاء ==========
async def cmd_clear_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    # ✅ احفظ محادثة فارغة مع system prompt فقط
    initial_conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
    await db.save_conversation(user.id, chat.id, initial_conversation)
    await update.message.reply_text("🧹 تم مسح محادثة الذكاء الاصطناعي.")

# ========== أمر عرض نماذج Groq المتاحة ==========
async def cmd_list_groq_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        await update.message.reply_text("❌ مفتاح GROQ_API_KEY غير موجود.")
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            ) as resp:
                data = await resp.json()
                names = [m["id"] for m in data.get("data", [])]
                if names:
                    await update.message.reply_text("📋 نماذج Groq المتاحة:\n\n" + "\n".join(names))
                else:
                    await update.message.reply_text("❌ لا توجد نماذج متاحة.")
    except Exception as e:
        logger.error(f"Groq models error: {e}")
        await update.message.reply_text("❌ تعذر جلب قائمة النماذج.")

# ========== دالة الاتصال بالنموذج ==========
async def _call_ai(model_key: str, messages: list) -> str:
    model = MODELS[model_key]
    api_key = os.environ.get(model["key_env"])
    if not api_key:
        return f"❌ مفتاح API غير موجود ({model['key_env']})."

    headers = {"Content-Type": "application/json"}

    if model_key == "gemini":
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
        }
        url = f"{model['url']}?key={api_key}"
    else:
        payload = {
            "model": model.get("model_name", "default"),
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        if model_key in ("deepseek", "llama", "llama4", "qwen", "sambanova"):
            headers["Authorization"] = f"Bearer {api_key}"
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
                    content = data["choices"][0]["message"]["content"]
                    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                    return content
    except Exception as e:
        logger.error(f"AI call error: {e}")
        return "❌ تعذر الاتصال بالذكاء الاصطناعي."

# ========== أمر شفق (نقطة الدخول الرئيسية) ==========
async def cmd_shafaq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user
    chat = update.effective_chat

    if msg.reply_to_message and msg.reply_to_message.from_user and msg.reply_to_message.from_user.is_bot:
        user_input = msg.text
        is_continuation = True
    elif msg.text.startswith("شفق "):
        user_input = msg.text[5:].strip()
        is_continuation = False
    else:
        return

    if not user_input:
        await msg.reply_text("⚠️ اكتب شيئًا بعد 'شفق'.")
        return

    model_key = context.user_data.get("ai_model", "llama")

    history = await db.get_conversation(user.id, chat.id)

    # ✅ التأكد من وجود system prompt دائماً
    if not history or history[0].get("role") != "system":
        system_msg = {"role": "system", "content": SYSTEM_PROMPT}
        if not is_continuation:
            history = [system_msg]
        else:
            history.insert(0, system_msg)
    elif not is_continuation:
        # إذا كانت بداية محادثة جديدة، نمسح السياق القديم ونبدأ من جديد
        history = [{"role": "system", "content": SYSTEM_PROMPT}]

    history.append({"role": "user", "content": user_input})
    history = _trim_history(history)

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

    # ✅ تحقق إن الرسالة المردود عليها من محادثة ذكاء وليست رسالة تحميل
    if not _is_ai_message(replied_msg.text or ""):
        return False

    history = await db.get_conversation(msg.from_user.id, msg.chat.id)

    # ✅ تأكد من وجود system prompt
    if not history or history[0].get("role") != "system":
        history.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

    user_input = msg.text
    if not user_input:
        return False

    model_key = context.user_data.get("ai_model", "llama")
    history.append({"role": "user", "content": user_input})
    history = _trim_history(history)

    await msg.reply_chat_action("typing")
    reply_text = await _call_ai(model_key, history)

    history.append({"role": "assistant", "content": reply_text})
    await db.save_conversation(msg.from_user.id, msg.chat.id, history)

    await msg.reply_text(reply_text, parse_mode="Markdown")
    return True

# ========== أوامر أخرى ==========
async def cmd_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ai_model"] = "gemini"
    await update.message.reply_text("✅ تم اختيار Gemini")

async def cmd_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("الحدود غير مفعلة حاليًا.")