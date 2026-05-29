import os
import random
import logging
import httpx

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

_conversations: dict[int, dict] = {}
MAX_HISTORY = 20
def _pick_provider() -> str:
    providers = []
    if GEMINI_API_KEY:
        providers.append("gemini")
    if OPENAI_API_KEY:
        providers.append("openai")
    if not providers:
        raise RuntimeError("لا يوجد مفتاح API مفعّل!")
    return random.choice(providers)

async def ask_ai(user_id: int, question: str) -> str:
    session = _get_session(user_id)
    provider = session["provider"]
    history = session["history"]

    history.append({"role": "user", "content": question})

    try:
        if provider == "gemini":
            answer = await _ask_gemini(history)
        else:
            answer = await _ask_openai(history)
    except Exception as e:
        logger.error("خطأ في %s: %s", provider, e)
        try:
            other = "openai" if provider == "gemini" else "gemini"
            if other == "gemini" and GEMINI_API_KEY:
                answer = await _ask_gemini(history)
            elif other == "openai" and OPENAI_API_KEY:
                answer = await _ask_openai(history)
            else:
                return "❌ حدث خطأ، حاول مرة أخرى."
        except Exception as e2:
            logger.error("خطأ في المزود الثاني: %s", e2)
            return "❌ حدث خطأ، حاول مرة أخرى."

    history.append({"role": "assistant", "content": answer})

    if len(history) > MAX_HISTORY:
        session["history"] = history[-MAX_HISTORY:]

    provider_label = "🤖 Gemini" if provider == "gemini" else "🧠 ChatGPT"
    return f"{provider_label}:\n{answer}"

def _get_session(user_id: int) -> dict:
    if user_id not in _conversations:
        _conversations[user_id] = {
            "provider": _pick_provider(),
            "history": [],
        }
    return _conversations[user_id]


def clear_session(user_id: int):
    _conversations.pop(user_id, None)

async def _ask_gemini(history: list[dict]) -> str:
    contents = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024,
        },
        "systemInstruction": {
            "parts": [{"text": "أنت مساعد ذكي ومفيد. أجب باللغة العربية دائماً ما لم يسألك المستخدم بلغة أخرى."}]
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
async def _ask_openai(history: list[dict]) -> str:
    messages = [
        {"role": "system", "content": "أنت مساعد ذكي ومفيد. أجب باللغة العربية دائماً ما لم يسألك المستخدم بلغة أخرى."}
    ] + history

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"].strip()