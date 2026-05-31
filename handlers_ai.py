import logging
import os
import aiohttp
from telegram import Update
from telegram.ext import ContextTypes

# ================================================

logger = logging.getLogger(__name__)

# ================================================

_conversation_history: dict[int, list] = {}
MAX_HISTORY = 10

# ================================================

async def ask_gemini(user_id: int, question: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY", "")
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

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": _conversation_history[user_id],
        "max_tokens": 1024,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error("Groq error %s: %s", resp.status, text)
                    return f"⚠️ خطأ من Groq ({resp.status}). حاول مرة أخرى."
                data = await resp.json()
                answer = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                if answer:
                    _conversation_history[user_id].append({"role": "assistant", "content": answer})
                return answer or "لم أتلقَّ إجابة من Groq."
    except Exception as e:
        logger.error("Groq request failed: %s", e)
        return "⚠️ تعذّر الاتصال بـ Groq. حاول لاحقاً."

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
    answer = await ask_gemini(user_id, question)
    try:
        await thinking_msg.delete()
    except Exception:
        pass
    await msg.reply_text(f"🌅 {answer}")