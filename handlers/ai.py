import logging
import os
import json
from telegram import Update
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
        "name": "LLaMA 3 (Groq)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "model_name": "llama-3.3-70b-versatile",
    },
}

# ========== اختيار النموذج ==========
async def cmd_choose_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("استخدم /model deepseek | gemini | llama")
        return
    choice = context.args[0].lower()
    if choice not in MODELS:
        await update.message.reply_text("اختر: deepseek, gemini, llama")
        return
    context.user_data["ai_model"] = choice
    await update.message.reply_text(f"✅ تم اختيار نموذج {MODELS[choice]['name']}")

async def callback_choose_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data.split("_")[1]
    if choice not in MODELS:
        await query.message.edit_text("❌ خيار غير صالح")
        return
    context.user_data["ai_model"] = choice
    await query.message.edit_text(f"✅ النموذج: {MODELS[choice]['name']}")

# ========== دالة الاتصال بالنموذج ==========
async def _call_ai(model_key: str, messages: list) -> str:
    model = MODELS[model_key]
    api_key = os.environ.get(model["key_env"])
    if not api_key:
        return f"❌ مفتاح API غير موجود ({model['key_env']})."

    headers = {"Content-Type": "application/json"}

    if model_key == "gemini":
        # تحويل messages إلى نص واحد (مبسط)
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
        if model_key == "deepseek":
            headers["Authorization"] = f"Bearer {api_key}"
        elif model_key == "llama":
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
                    return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI call error: {e}")
        return "❌ تعذر الاتصال بالذكاء الاصطناعي."

# ========== أمر شفق (نقطة الدخول الرئيسية) ==========
async def cmd_shafaq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user
    chat = update.effective_chat

    # هل هو أمر صريح أم رد على رسالة بوت؟
    if msg.reply_to_message and msg.reply_to_message.from_user and msg.reply_to_message.from_user.is_bot:
        # رد على رسالة بوت ← استمرار المحادثة
        user_input = msg.text
        is_continuation = True
    elif msg.text.startswith("شفق "):
        user_input = msg.text[5:].strip()  # إزالة "شفق "
        is_continuation = False
    else:
        return  # ليس له علاقة بالذكاء

    if not user_input:
        await msg.reply_text("⚠️ اكتب شيئًا بعد 'شفق'.")
        return

    # النموذج المختار
    model_key = context.user_data.get("ai_model", "deepseek")

    # جلب السياق السابق
    history = await db.get_conversation(user.id, chat.id)
    if not is_continuation:
        # بداية محادثة جديدة: نفرغ السياق القديم ونبدأ برسالة النظام
        history = [{"role": "system", "content": "أنت شفق، مساعد ذكي مفيد ومهذب. تجيب بالعربية الفصحى المختصرة."}]

    # إضافة رسالة المستخدم الحالية
    history.append({"role": "user", "content": user_input})

    # استدعاء النموذج
    await msg.reply_chat_action("typing")
    reply_text = await _call_ai(model_key, history)
    
    # إضافة رد البوت للسياق وحفظه
    history.append({"role": "assistant", "content": reply_text})
    await db.save_conversation(user.id, chat.id, history)

    # إرسال الرد
    await msg.reply_text(reply_text, parse_mode="Markdown")

# ========== معالجة الردود على رسائل البوت الذكية ==========
# هذه الدالة تستخدم في app.py للردود التلقائية
async def handle_ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.reply_to_message:
        return False

    replied_msg = msg.reply_to_message
    # تحقق أن الرسالة المردود عليها هي من البوت وأنها رد ذكي (ليست أمرًا عاديًا)
    if not replied_msg.from_user or not replied_msg.from_user.is_bot:
        return False

    # إذا كانت الرسالة المردود عليها تحتوي على رد من الذكاء الاصطناعي (يمكننا تمييزها بصعوبة،
    # لكننا نعتمد على أن أي رد على بوت هو متابعة محادثة)
    # فقط نتأكد أن المستخدم لا يزال لديه محادثة نشطة
    history = await db.get_conversation(msg.from_user.id, msg.chat.id)
    if not history:
        return False  # لا توجد محادثة سابقة

    # تابع كما لو كان أمر شفق
    user_input = msg.text
    if not user_input:
        return False

    model_key = context.user_data.get("ai_model", "deepseek")
    history.append({"role": "user", "content": user_input})
    
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