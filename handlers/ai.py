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

# ========== السيستم بروبت الموحد ==========
SYSTEM_PROMPT = "أنت 'شفق'، مساعد ذكي مفيد ومهذب. مهمتك هي تقديم إجابات دقيقة ومفيدة باللغة العربية الفصحى المختصرة. يجب أن تلتزم بالحقائق. إذا سُئلت عن شيء لا تعرفه أو كان خارج نطاق معرفتك، يجب أن تعتذر بلطف وتقول 'لا أعلم' بدلاً من تخمين إجابة. لا تؤلف معلومات. كن مباشرًا وواضحًا."

# ========== سيستم بروبت كشف النية ==========
INTENT_SYSTEM_PROMPT = """أنت محلل نوايا لبوت تيليجرام. مهمتك تحليل رسالة المستخدم وإرجاع JSON فقط بدون أي نص إضافي.

الـ intents المتاحة:
- reminder: تذكير لمرة واحدة (مثال: ذكرني بعد 5 دقائق بكذا)
- daily_reminder: تذكير يومي (مثال: ذكرني يومياً الساعة 9 بكذا)
- cancel_reminder: إلغاء التذكير اليومي
- my_reminders: عرض التذكيرات
- ban: حظر عضو (مثال: احظر @فلان / احظر هذا الشخص)
- unban: رفع الحظر (مثال: ارفع الحظر عن @فلان)
- mute: كتم عضو
- unmute: رفع الكتم
- warn: تحذير عضو
- report: تقرير عن عضو
- deep_report: تقرير متقدم عن عضو
- pin: تثبيت رسالة
- unpin: إلغاء تثبيت
- list_admins: عرض المشرفين
- my_rank: رتبتي
- rules: عرض القواعد
- id: معرفي أو معرف شخص
- stats: إحصائيات المجموعة
- need_someone: طلب مساعدة / طوارئ نفسية
- event_log: آخر أحداث المجموعة (مثال: وش صار، آخر أحداث، سجل الأحداث)
- user_warnings: تحذيرات عضو (مثال: كم تحذير عند فلان، تحذيرات @فلان)
- banned_words: الكلمات المحظورة (مثال: وش الكلمات المحظورة، اعرض المحظور)
- crisis_toggle: تفعيل أو تعطيل نظام الأزمات (مثال: فعّل الأزمات، عطّل الأزمات)
- none: محادثة عادية أو سؤال

صيغة الرد JSON:
{
  "intent": "اسم النية",
  "minutes": رقم أو null,
  "time": "HH:MM" أو null,
  "text": "نص التذكير أو السبب" أو null,
  "target": "يوزر أو معرف الشخص المستهدف" أو null,
  "duration": "مدة الحظر مثل 1d أو 2h" أو null,
  "enabled": true أو false أو null
}

قواعد مهمة:
- أرجع JSON فقط، بدون أي كلام قبله أو بعده
- إذا لم تكن متأكداً من النية أرجع intent: none
- الأوامر التي تحتاج reply (pin, report, ban بدون يوزر) أرجعها كـ none إذا لم يكن هناك target واضح
- crisis_toggle: إذا كانت الرسالة تفعيل/شغّل/افتح أرجع enabled: true، إذا تعطيل/أوقف/أغلق أرجع enabled: false"""

# ========== إعدادات النماذج ==========
MODELS = {
    "llama": {
        "name": "LLaMA 3 (Groq)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "model_name": "llama-3.3-70b-versatile",
    },
    "cerebras": {
        "name": "Cerebras (Llama 3.3)",
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "key_env": "CEREBRAS_API_KEY",
        "model_name": "llama-3.3-70b",
    },
    "openrouter": {
        "name": "OpenRouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_env": "OPENROUTER_API_KEY",
        "model_name": "mistralai/mistral-7b-instruct:free",
    },
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
    "sambanova": {
        "name": "SambaNova (Llama 3.1)",
        "url": "https://api.sambanova.ai/v1/chat/completions",
        "key_env": "SAMBANOVA_API_KEY",
        "model_name": "Meta-Llama-3.1-8B-Instruct",
    },
    "openai": {
        "name": "OpenAI GPT",
        "url": "https://api.openai.com/v1/chat/completions",
        "key_env": "OPENAI_API_KEY",
        "model_name": "gpt-3.5-turbo",
    },
}

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

# ========== Rate Limiting ==========
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

# ========== كشف الوقت بالعربي ==========
def _parse_arabic_time(text: str) -> int | None:
    text = text.strip()
    patterns = [
        (r"ربع ساعة", 15),
        (r"نص ساعة|نصف ساعة", 30),
        (r"ثلاثة أرباع ساعة|٣ أرباع ساعة", 45),
        (r"ساعة ونص|ساعة ونصف", 90),
        (r"ساعتين", 120),
        (r"(\d+)\s*ساعة", None),
        (r"(\d+)\s*دقيقة", None),
        (r"(\d+)\s*دقائق", None),
        (r"بعد شوي|بعد قليل", 5),
    ]
    for pattern, value in patterns:
        match = re.search(pattern, text)
        if match:
            if value is not None:
                return value
            num = int(match.group(1))
            if "ساعة" in pattern:
                return num * 60
            return num
    return None

# ========== كشف النية ==========
async def _detect_intent(user_input: str, model_key: str) -> dict:
    intent_model = "llama" if os.environ.get("GROQ_API_KEY") else model_key

    messages = [
        {"role": "system", "content": INTENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]

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

# ========== تنفيذ النية ==========
async def _execute_intent(intent_data: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    intent = intent_data.get("intent", "none")
    msg = update.message
    user = update.effective_user
    chat = update.effective_chat

    # ===== تذكير لمرة واحدة =====
    if intent == "reminder":
        minutes = intent_data.get("minutes")
        text = intent_data.get("text")
        if not minutes or not text:
            await msg.reply_text("⚠️ لم أفهم المدة أو النص. مثال: شفق ذكرني بعد 5 دقائق بشرب الماء")
            return True
        try:
            minutes = int(minutes)
            if minutes <= 0 or minutes > 1440:
                await msg.reply_text("❌ المدة يجب أن تكون بين 1 و 1440 دقيقة.")
                return True
            from handlers.user import _send_reminder
            context.job_queue.run_once(
                _send_reminder,
                when=minutes * 60,
                chat_id=chat.id,
                name=f"reminder_{chat.id}_{msg.message_id}",
                data=text
            )
            await msg.reply_text(f"✅ تم!\n⏰ سأذكرك بعد {minutes} دقيقة\n📝 {text}")
        except Exception as e:
            logger.error(f"Intent reminder error: {e}")
            await msg.reply_text("❌ حدث خطأ في ضبط التذكير.")
        return True

    # ===== تذكير يومي =====
    if intent == "daily_reminder":
        time_str = intent_data.get("time")
        text = intent_data.get("text")
        if not time_str or not text:
            await msg.reply_text("⚠️ لم أفهم الوقت أو النص. مثال: شفق ذكرني يومياً الساعة 9:00 بالاجتماع")
            return True
        try:
            import datetime as dt_mod
            from handlers.jobs import _send_daily_reminder
            from config import TIMEZONE
            hour, minute = map(int, time_str.split(":"))
            saved = await db.save_reminder(user.id, chat.id, time_str, text)
            if not saved:
                await msg.reply_text("❌ فشل حفظ التذكير.")
                return True
            target_time = dt_mod.time(hour=hour, minute=minute, second=0, tzinfo=TIMEZONE)
            context.job_queue.run_daily(
                _send_daily_reminder,
                time=target_time,
                chat_id=chat.id,
                data={"user_id": user.id, "text": text},
                name=f"daily_reminder_{saved['id']}"
            )
            await msg.reply_text(f"✅ تم!\n⏰ سأذكرك يومياً الساعة {time_str}\n📝 {text}")
        except Exception as e:
            logger.error(f"Intent daily_reminder error: {e}")
            await msg.reply_text("❌ حدث خطأ في ضبط التذكير اليومي.")
        return True

    # ===== إلغاء التذكير =====
    if intent == "cancel_reminder":
        await db.delete_reminder(user.id, chat.id)
        removed = 0
        for job in context.job_queue.jobs():
            if job.name and job.name.startswith("daily_reminder_") and hasattr(job, 'data'):
                if isinstance(job.data, dict) and job.data.get("user_id") == user.id and job.chat_id == chat.id:
                    job.schedule_removal()
                    removed += 1
        await msg.reply_text(f"✅ تم إلغاء تذكيراتك اليومية ({removed} تذكير).")
        return True

    # ===== عرض التذكيرات =====
    if intent == "my_reminders":
        reminders = await db.get_user_reminders(user.id, chat.id)
        if not reminders:
            await msg.reply_text("📭 ليس لديك أي تذكيرات يومية.")
        else:
            lines = [f"{i}. ⏰ {r['reminder_time']} - 📝 {r['reminder_text']}" for i, r in enumerate(reminders, 1)]
            await msg.reply_text("📋 **تذكيراتك:**\n\n" + "\n".join(lines), parse_mode="Markdown")
        return True

    # ===== أوامر تحتاج صلاحيات مشرف =====
    admin_intents = ["ban", "unban", "mute", "unmute", "warn", "pin", "unpin",
                     "event_log", "banned_words", "crisis_toggle"]
    if intent in admin_intents:
        if not await is_admin(update, context):
            await msg.reply_text("⛔ هذا الأمر للمشرفين فقط.")
            return True

    # ===== حظر =====
    if intent == "ban":
        target = intent_data.get("target")
        duration = intent_data.get("duration")
        reason = intent_data.get("text") or "بأمر شفق"

        if not target and not msg.reply_to_message:
            await msg.reply_text("⚠️ حدد الشخص برد على رسالته أو اذكر يوزره.\nمثال: شفق احظر @فلان")
            return True

        target_id = None
        target_name = target or "المستخدم"

        if msg.reply_to_message:
            target_id = msg.reply_to_message.from_user.id
            target_name = msg.reply_to_message.from_user.first_name
        elif target:
            target = target.lstrip("@")
            try:
                member = await context.bot.get_chat_member(chat.id, target)
                target_id = member.user.id
                target_name = member.user.first_name
            except:
                await msg.reply_text(f"❌ لم أجد المستخدم: {target}")
                return True

        try:
            from datetime import datetime, timedelta, timezone as tz
            from utils.helpers import parse_duration
            until = None
            if duration:
                duration_obj = parse_duration(duration)
                if duration_obj:
                    until = datetime.now(tz.utc) + duration_obj
                    await context.bot.ban_chat_member(chat.id, target_id, until_date=until)
                else:
                    await context.bot.ban_chat_member(chat.id, target_id)
            else:
                await context.bot.ban_chat_member(chat.id, target_id)

            await db.add_ban(target_id, chat.id, reason, user.id, until)
            await db.log_event(chat.id, "ban", user_id=user.id, target_id=target_id, detail=reason)
            duration_str = f" لمدة {duration}" if duration else " دائماً"
            await msg.reply_text(f"🚫 تم حظر {target_name}{duration_str}\n📝 السبب: {reason}\n👤 بأمر: {user.first_name}")
        except Exception as e:
            logger.error(f"Intent ban error: {e}")
            await msg.reply_text("❌ فشل الحظر.")
        return True

    # ===== رفع الحظر =====
    if intent == "unban":
        target = intent_data.get("target")
        if not target and not msg.reply_to_message:
            await msg.reply_text("⚠️ حدد الشخص. مثال: شفق ارفع الحظر عن @فلان")
            return True

        target_id = None
        target_name = target or "المستخدم"

        if msg.reply_to_message:
            target_id = msg.reply_to_message.from_user.id
            target_name = msg.reply_to_message.from_user.first_name
        elif target:
            target = target.lstrip("@")
            try:
                member = await context.bot.get_chat_member(chat.id, target)
                target_id = member.user.id
                target_name = member.user.first_name
            except:
                await msg.reply_text(f"❌ لم أجد المستخدم: {target}")
                return True

        try:
            await context.bot.unban_chat_member(chat.id, target_id)
            await db.remove_ban(target_id, chat.id, user.id)
            await msg.reply_text(f"✅ تم رفع الحظر عن {target_name}\n👤 بأمر: {user.first_name}")
        except Exception as e:
            logger.error(f"Intent unban error: {e}")
            await msg.reply_text("❌ فشل رفع الحظر.")
        return True

    # ===== كتم =====
    if intent == "mute":
        target_id = None
        target_name = "المستخدم"

        if msg.reply_to_message:
            target_id = msg.reply_to_message.from_user.id
            target_name = msg.reply_to_message.from_user.first_name
        elif intent_data.get("target"):
            target = intent_data["target"].lstrip("@")
            try:
                member = await context.bot.get_chat_member(chat.id, target)
                target_id = member.user.id
                target_name = member.user.first_name
            except:
                await msg.reply_text(f"❌ لم أجد المستخدم: {target}")
                return True
        else:
            await msg.reply_text("⚠️ حدد الشخص برد على رسالته أو اذكر يوزره.")
            return True

        try:
            from telegram import ChatPermissions
            await context.bot.restrict_chat_member(chat.id, target_id, ChatPermissions(can_send_messages=False))
            await db.log_event(chat.id, "mute", user_id=user.id, target_id=target_id)
            await msg.reply_text(f"🔇 تم كتم {target_name}\n👤 بأمر: {user.first_name}")
        except Exception as e:
            logger.error(f"Intent mute error: {e}")
            await msg.reply_text("❌ فشل الكتم.")
        return True

    # ===== رفع الكتم =====
    if intent == "unmute":
        target_id = None
        target_name = "المستخدم"

        if msg.reply_to_message:
            target_id = msg.reply_to_message.from_user.id
            target_name = msg.reply_to_message.from_user.first_name
        elif intent_data.get("target"):
            target = intent_data["target"].lstrip("@")
            try:
                member = await context.bot.get_chat_member(chat.id, target)
                target_id = member.user.id
                target_name = member.user.first_name
            except:
                await msg.reply_text(f"❌ لم أجد المستخدم: {target}")
                return True
        else:
            await msg.reply_text("⚠️ حدد الشخص برد على رسالته أو اذكر يوزره.")
            return True

        try:
            from telegram import ChatPermissions
            await context.bot.restrict_chat_member(chat.id, target_id, ChatPermissions(
                can_send_messages=True, can_send_polls=True,
                can_send_other_messages=True, can_add_web_page_previews=True
            ))
            await db.log_event(chat.id, "unmute", user_id=user.id, target_id=target_id)
            await msg.reply_text(f"🔊 تم رفع الكتم عن {target_name}\n👤 بأمر: {user.first_name}")
        except Exception as e:
            logger.error(f"Intent unmute error: {e}")
            await msg.reply_text("❌ فشل رفع الكتم.")
        return True

    # ===== تحذير =====
    if intent == "warn":
        target_id = None
        target_name = "المستخدم"

        if msg.reply_to_message:
            target_id = msg.reply_to_message.from_user.id
            target_name = msg.reply_to_message.from_user.first_name
        elif intent_data.get("target"):
            target = intent_data["target"].lstrip("@")
            try:
                member = await context.bot.get_chat_member(chat.id, target)
                target_id = member.user.id
                target_name = member.user.first_name
            except:
                await msg.reply_text(f"❌ لم أجد المستخدم: {target}")
                return True
        else:
            await msg.reply_text("⚠️ حدد الشخص برد على رسالته أو اذكر يوزره.")
            return True

        from config import MAX_WARNINGS
        count = await db.add_warning(target_id, chat.id)
        await msg.reply_text(f"⚠️ تم تحذير {target_name} ({count}/{MAX_WARNINGS})\n👤 بأمر: {user.first_name}")
        if count >= MAX_WARNINGS:
            try:
                await context.bot.ban_chat_member(chat.id, target_id)
                await db.add_ban(target_id, chat.id, f"حظر تلقائي بعد {MAX_WARNINGS} تحذيرات", 0)
                await db.clear_warnings(target_id, chat.id)
                await msg.reply_text(f"🚫 تم حظر {target_name} تلقائياً بعد {MAX_WARNINGS} تحذيرات.")
            except Exception as e:
                logger.error(f"Intent auto ban error: {e}")
        return True

    # ===== تقرير =====
    if intent == "report":
        if not msg.reply_to_message:
            await msg.reply_text("⚠️ رد على رسالة الشخص ثم قل: شفق بلّغ عنه")
            return True
        target = msg.reply_to_message.from_user
        reason = intent_data.get("text") or "لم يحدد سبب"
        from datetime import datetime as dt_mod
        from config import TIMEZONE
        report_text = (
            f"📢 **تقرير جديد عبر شفق**\n\n"
            f"👤 مقدم التقرير: {user.full_name}\n"
            f"🚨 العضو: {target.full_name} (`{target.id}`)\n"
            f"📋 السبب: {reason}\n"
            f"🕒 الوقت: {dt_mod.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        admins = await context.bot.get_chat_administrators(chat.id)
        sent = 0
        for admin in admins:
            if not admin.user.is_bot:
                try:
                    await context.bot.send_message(admin.user.id, report_text, parse_mode="Markdown")
                    sent += 1
                except:
                    pass
        await msg.reply_text(f"✅ تم إرسال التقرير إلى {sent} مشرف.")
        return True

    # ===== تقرير متقدم =====
    if intent == "deep_report":
        if not msg.reply_to_message:
            await msg.reply_text("⚠️ رد على رسالة الشخص ثم قل: شفق تقرير متقدم")
            return True
        context.args = [intent_data.get("text") or ""]
        from handlers.jobs import cmd_deep_report
        await cmd_deep_report(update, context)
        return True

    # ===== تثبيت =====
    if intent == "pin":
        if not msg.reply_to_message:
            await msg.reply_text("⚠️ رد على الرسالة التي تريد تثبيتها ثم قل: شفق ثبّت")
            return True
        try:
            await msg.reply_to_message.pin()
            await msg.reply_text("📌 تم التثبيت.")
        except:
            await msg.reply_text("❌ فشل التثبيت.")
        return True

    # ===== إلغاء تثبيت =====
    if intent == "unpin":
        try:
            await msg.chat.unpin_all_messages()
            await msg.reply_text("📌 تم إلغاء التثبيت.")
        except:
            await msg.reply_text("❌ فشل إلغاء التثبيت.")
        return True

    # ===== المشرفين =====
    if intent == "list_admins":
        try:
            admins = await msg.chat.get_administrators()
            lines = [f"• {a.user.first_name} {'(المالك)' if a.status == 'creator' else ''}" for a in admins]
            await msg.reply_text("👮 **المشرفون:**\n" + "\n".join(lines), parse_mode="Markdown")
        except:
            await msg.reply_text("❌ لا يمكن جلب قائمة المشرفين.")
        return True

    # ===== رتبتي =====
    if intent == "my_rank":
        try:
            member = await context.bot.get_chat_member(chat.id, user.id)
            rank_map = {
                'creator': '👑 المالك',
                'administrator': '👮 مشرف',
                'member': '👤 عضو',
                'restricted': '🔇 مكتوم',
                'left': '🚪 غادر',
                'kicked': '🚫 محظور',
            }
            rank = rank_map.get(member.status, '❓ غير معروف')
            await msg.reply_text(f"🏅 رتبتك: {rank}")
        except:
            await msg.reply_text("❌ لا يمكن تحديد الرتبة.")
        return True

    # ===== القواعد =====
    if intent == "rules":
        rules = await db.get_setting(chat.id, "rules")
        if rules:
            await msg.reply_text(f"📋 **قواعد المجموعة:**\n{rules}", parse_mode="Markdown")
        else:
            await msg.reply_text("لم يتم تعيين قواعد بعد.")
        return True

    # ===== المعرف =====
    if intent == "id":
        target_user = msg.reply_to_message.from_user if msg.reply_to_message else user
        await msg.reply_text(f"🆔 المعرف: `{target_user.id}`\n👤 الاسم: {target_user.first_name}", parse_mode="Markdown")
        return True

    # ===== إحصائيات =====
    if intent == "stats":
        try:
            count = await context.bot.get_chat_member_count(chat.id)
            admins = await context.bot.get_chat_administrators(chat.id)
            await msg.reply_text(f"📊 **إحصائيات المجموعة:**\n👥 الأعضاء: {count}\n👮 المشرفون: {len(admins)}", parse_mode="Markdown")
        except:
            await msg.reply_text("❌ لا يمكن جلب الإحصائيات.")
        return True

    # ===== طوارئ =====
    if intent == "need_someone":
        from handlers.support import cmd_need_someone
        await cmd_need_someone(update, context)
        return True

    # ===== آخر أحداث المجموعة =====
    if intent == "event_log":
        if not await is_admin(update, context):
            await msg.reply_text("⛔ هذا الأمر للمشرفين فقط.")
            return True
        events = await db.get_event_log(chat.id, 10)
        if not events:
            await msg.reply_text("📭 لا توجد أحداث مسجلة.")
        else:
            lines = []
            for e in events:
                action = e.get("action", "")
                created = e.get("created_at", "")[:16]
                uid = e.get("user_id", "")
                tid = e.get("target_id", "")
                line = f"• `{action}` — {created}"
                if tid:
                    line += f" | هدف: `{tid}`"
                lines.append(line)
            await msg.reply_text(
                f"📋 **آخر أحداث المجموعة:**\n\n" + "\n".join(lines),
                parse_mode="Markdown"
            )
        return True

    # ===== تحذيرات عضو =====
    if intent == "user_warnings":
        target_id = None
        target_name = "المستخدم"

        if msg.reply_to_message:
            target_id = msg.reply_to_message.from_user.id
            target_name = msg.reply_to_message.from_user.first_name
        elif intent_data.get("target"):
            target = intent_data["target"].lstrip("@")
            try:
                member = await context.bot.get_chat_member(chat.id, target)
                target_id = member.user.id
                target_name = member.user.first_name
            except:
                await msg.reply_text(f"❌ لم أجد المستخدم: {target}")
                return True
        else:
            await msg.reply_text("⚠️ حدد الشخص برد على رسالته أو اذكر يوزره.")
            return True

        from config import MAX_WARNINGS
        count = await db.get_warnings(target_id, chat.id)
        await msg.reply_text(
            f"⚠️ **تحذيرات {target_name}:**\n{count}/{MAX_WARNINGS}",
            parse_mode="Markdown"
        )
        return True

    # ===== الكلمات المحظورة =====
    if intent == "banned_words":
        if not await is_admin(update, context):
            await msg.reply_text("⛔ هذا الأمر للمشرفين فقط.")
            return True
        words = await db.get_banned_words(chat.id)
        if not words:
            await msg.reply_text("✅ لا توجد كلمات محظورة في هذه المجموعة.")
        else:
            await msg.reply_text(
                f"🚫 **الكلمات المحظورة ({len(words)}):**\n\n" + "\n".join(f"• `{w}`" for w in words),
                parse_mode="Markdown"
            )
        return True

    # ===== تفعيل/تعطيل نظام الأزمات =====
    if intent == "crisis_toggle":
        if not await is_admin(update, context):
            await msg.reply_text("⛔ هذا الأمر للمشرفين فقط.")
            return True
        enabled = intent_data.get("enabled")
        if enabled is None:
            current = await db.get_crisis_enabled(chat.id)
            status = "مفعّل ✅" if current else "معطّل ❌"
            await msg.reply_text(f"🚨 نظام الأزمات حالياً: {status}")
            return True
        await db.set_crisis_enabled(chat.id, enabled)
        status = "✅ تم تفعيل" if enabled else "🔴 تم تعطيل"
        await msg.reply_text(f"{status} نظام الأزمات\n👤 بأمر: {user.first_name}")
        return True

    return False


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
    else:
        return

    if not user_input:
        await msg.reply_text("⚠️ اكتب شيئًا بعد 'شفق'.")
        return

    # ===== Rate Limiting =====
    if _check_rate_limit(user.id):
        await msg.reply_text("⏱️ أرسلت أوامر كثيرة، انتظر دقيقة ثم حاول.")
        return

    model_key = context.user_data.get("ai_model", "llama")

    # ===== كشف النية أولاً =====
    if not is_continuation:
        thinking_msg = await msg.reply_text("⏳ جاري التفكير...")
        intent_data = await _detect_intent(user_input, model_key)
        logger.info(f"Intent detected: {intent_data}")

        try:
            await thinking_msg.delete()
        except:
            pass

        intent = intent_data.get("intent", "none")

        # ===== تسجيل محاولات غير المشرفين =====
        admin_intents = ["ban", "unban", "mute", "unmute", "warn", "pin", "unpin",
                         "event_log", "banned_words", "crisis_toggle"]
        if intent in admin_intents and not await is_admin(update, context):
            await db.log_event(
                chat.id, "shafaq_unauthorized_attempt",
                user_id=user.id,
                detail=f"tried: {intent} | msg: {user_input[:80]}"
            )
            await msg.reply_text("⛔ هذا الأمر للمشرفين فقط.")
            return

        # ===== تسجيل الأوامر التنفيذية =====
        executive_intents = ["ban", "unban", "mute", "unmute", "warn", "pin", "unpin"]
        if intent in executive_intents:
            await db.log_event(
                chat.id, f"shafaq_{intent}",
                user_id=user.id,
                detail=f"via shafaq: {user_input[:100]}"
            )

        # ===== السؤال لما المعلومة ناقصة =====
        if intent == "reminder" and not intent_data.get("minutes"):
            context.user_data["pending_intent"] = intent_data
            await msg.reply_text("⏰ كم دقيقة؟")
            return

        if intent == "reminder" and not intent_data.get("text"):
            context.user_data["pending_intent"] = intent_data
            await msg.reply_text("📝 وش أذكّرك فيه؟")
            return

        if intent == "daily_reminder" and not intent_data.get("time"):
            context.user_data["pending_intent"] = intent_data
            await msg.reply_text("⏰ أي ساعة؟ (مثال: 09:00)")
            return

        if intent == "daily_reminder" and not intent_data.get("text"):
            context.user_data["pending_intent"] = intent_data
            await msg.reply_text("📝 وش أذكّرك فيه؟")
            return

        executed = await _execute_intent(intent_data, update, context)
        if executed:
            context.user_data["last_intent"] = intent_data
            return

        if intent != "none":
            await msg.reply_text(
                "⚠️ لم أفهم الأمر جيداً.\n"
                "جرب تكتبه بشكل مختلف، أو استخدم الأمر المباشر.\n"
                "مثال: `شفق احظر @فلان` أو `شفق ذكرني بعد 5 دقائق بكذا`",
                parse_mode="Markdown"
            )
            return

    # ===== إكمال السياق =====
    pending = context.user_data.pop("pending_intent", None)
    if pending and not is_continuation:
        intent = pending.get("intent")
        if intent == "reminder":
            if not pending.get("minutes"):
                arabic_minutes = _parse_arabic_time(user_input)
                pending["minutes"] = arabic_minutes or (int(user_input) if user_input.isdigit() else None)
            elif not pending.get("text"):
                pending["text"] = user_input
            if pending.get("minutes") and pending.get("text"):
                await _execute_intent(pending, update, context)
                context.user_data["last_intent"] = pending
                return

        if intent == "daily_reminder":
            if not pending.get("time"):
                pending["time"] = user_input
            elif not pending.get("text"):
                pending["text"] = user_input
            if pending.get("time") and pending.get("text"):
                await _execute_intent(pending, update, context)
                context.user_data["last_intent"] = pending
                return

        context.user_data["pending_intent"] = pending

    # ===== محادثة عادية =====
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


# ========== أوامر أخرى ==========
async def cmd_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ai_model"] = "gemini"
    await update.message.reply_text("✅ تم اختيار Gemini")

async def cmd_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("الحدود غير مفعلة حاليًا.")
