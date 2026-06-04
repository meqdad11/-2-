import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes
from utils import database as db
from utils.helpers import require_admin

# ================================================

logger = logging.getLogger(__name__)
TIMEZONE = ZoneInfo("Asia/Riyadh")

# ================================================

async def cmd_add_resource(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text(
            "الاستخدام:\n"
            "أضف مورد العنوان | المحتوى أو الرابط\n\n"
            "مثال:\n"
            "أضف مورد تمارين التنفس | https://example.com\n"
            "أضف مورد نصيحة يومية | خذ نفساً عميقاً وتذكر أنك لست وحدك"
        )
        return

    full_text = " ".join(context.args)

    if "|" not in full_text:
        await update.message.reply_text(
            "❌ يرجى الفصل بين العنوان والمحتوى بـ |\n"
            "مثال: أضف مورد العنوان | المحتوى"
        )
        return

    parts = full_text.split("|", 1)
    title = parts[0].strip()
    content = parts[1].strip()

    if not title or not content:
        await update.message.reply_text("❌ العنوان والمحتوى لا يمكن أن يكونا فارغَين.")
        return

    chat_id = update.effective_chat.id
    added_by = update.effective_user.id
    added_by_name = update.effective_user.first_name or str(added_by)
    created_at = datetime.now(TIMEZONE).isoformat()

    # تحميل القائمة الحالية
    resources = await _get_resources(chat_id)

    # التحقق من عدم التكرار
    for r in resources:
        if r["title"].lower() == title.lower():
            await update.message.reply_text(f"⚠️ يوجد مورد بنفس العنوان: {title}")
            return

    resources.append({
        "title": title,
        "content": content,
        "added_by": added_by,
        "added_by_name": added_by_name,
        "created_at": created_at,
    })

    await _save_resources(chat_id, resources)
    await update.message.reply_text(f"✅ تمت إضافة المورد:\n📌 {title}")
    await db.log_event(chat_id, "add_resource", user_id=added_by, detail=title)

# ================================================

async def cmd_list_resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    resources = await _get_resources(chat_id)

    if not resources:
        await update.message.reply_text("📂 لا توجد موارد مضافة بعد.")
        return

    # تصفية اختيارية بكلمة مفتاحية
    keyword = " ".join(context.args).strip().lower() if context.args else None
    if keyword:
        filtered = [r for r in resources if keyword in r["title"].lower() or keyword in r["content"].lower()]
        if not filtered:
            await update.message.reply_text(f"🔍 لا توجد موارد تحتوي على: {keyword}")
            return
        resources = filtered

    lines = []
    for i, r in enumerate(resources, 1):
        lines.append(f"{i}. 📌 {r['title']}\n   {r['content']}")

    header = f"📚 الموارد ({len(resources)}):\n\n" if not keyword else f"🔍 نتائج '{keyword}':\n\n"
    full_text = header + "\n\n".join(lines)

    # تقسيم الرسالة إذا كانت طويلة
    if len(full_text) > 4000:
        chunks = []
        current = header
        for line in lines:
            if len(current) + len(line) + 2 > 4000:
                chunks.append(current)
                current = line + "\n\n"
            else:
                current += line + "\n\n"
        if current:
            chunks.append(current)
        for chunk in chunks:
            await update.message.reply_text(chunk.strip())
    else:
        await update.message.reply_text(full_text)

# ================================================

async def cmd_delete_resource(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: احذف مورد <رقم المورد>\nاستخدم 'الموارد' لمعرفة الأرقام.")
        return
    try:
        index = int(context.args[0]) - 1
    except ValueError:
        await update.message.reply_text("❌ أرسل رقم المورد. مثال: احذف مورد 2")
        return

    chat_id = update.effective_chat.id
    resources = await _get_resources(chat_id)

    if index < 0 or index >= len(resources):
        await update.message.reply_text(f"❌ رقم غير صحيح. يوجد {len(resources)} موارد فقط.")
        return

    removed = resources.pop(index)
    await _save_resources(chat_id, resources)
    await update.message.reply_text(f"✅ تم حذف المورد: {removed['title']}")
    await db.log_event(chat_id, "delete_resource", user_id=update.effective_user.id, detail=removed["title"])

# ================================================
# دوال مساعدة داخلية
# ================================================

async def _get_resources(chat_id: int) -> list:
    raw = await db.get_setting(chat_id, "resources")
    if not raw:
        return []
    try:
        import json
        return json.loads(raw)
    except Exception:
        return []

async def _save_resources(chat_id: int, resources: list):
    import json
    await db.set_setting(chat_id, "resources", json.dumps(resources, ensure_ascii=False))