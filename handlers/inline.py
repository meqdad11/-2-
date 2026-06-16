import uuid

from telegram import (
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes

# تخزين مؤقت للهمسات: secret_id -> { text, target_username, sender_id, sender_name }
WHISPERS: dict[str, dict] = {}


async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inline_query = update.inline_query
    query_text = inline_query.query.strip()
    user = inline_query.from_user

    # الحالة 1: ما كتب شي بعد يوزر البوت
    if not query_text:
        results = [
            InlineQueryResultArticle(
                id="help_empty",
                title="✏️ اكتب: يوزر_المستلم ثم نص الرسالة",
                description="مثال: ahmed سرك بأمان معي",
                input_message_content=InputTextMessageContent(
                    "اكتب يوزر المستلم متبوعًا بمسافة ثم نص الرسالة."
                ),
            )
        ]
        await inline_query.answer(results, cache_time=1, is_personal=True)
        return

    parts = query_text.split(maxsplit=1)
    target_username = parts[0].lstrip("@")
    message_text = parts[1].strip() if len(parts) > 1 else ""

    # الحالة 2: كتب اليوزر بس مو الرسالة
    if not message_text:
        results = [
            InlineQueryResultArticle(
                id="help_no_message",
                title=f"✏️ اكتب نص الرسالة بعد @{target_username}",
                description=f"مثال: {target_username} مرحبا كيف حالك",
                input_message_content=InputTextMessageContent(
                    f"اكمل كتابة الرسالة بعد @{target_username}."
                ),
            )
        ]
        await inline_query.answer(results, cache_time=1, is_personal=True)
        return

    # الحالة 3: جاهز يوزر + رسالة → جهّز همسة فعلية
    secret_id = str(uuid.uuid4())
    WHISPERS[secret_id] = {
        "text": message_text,
        "target_username": target_username.lower(),
        "sender_id": user.id,
        "sender_name": user.first_name,
    }

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("👁 اضغط لعرض الرسالة", callback_data=f"reveal:{secret_id}")]]
    )

    results = [
        InlineQueryResultArticle(
            id=secret_id,
            title=f"🤫 إرسال همسة إلى @{target_username}",
            description=message_text[:60],
            input_message_content=InputTextMessageContent(
                f"🤫 همسة من {user.first_name} إلى @{target_username}\n"
                "اضغط الزر بالأسفل لعرضها 👇"
            ),
            reply_markup=keyboard,
        )
    ]
    await inline_query.answer(results, cache_time=1, is_personal=True)


async def handle_chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختياري حاليًا — مفيد لو تبي تسجل لاحقًا أي همسة تم إرسالها فعليًا."""
    pass


async def handle_reveal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يتنفذ لما أي شخص يضغط زر (اضغط لعرض الرسالة)."""
    query = update.callback_query
    data = query.data or ""

    if not data.startswith("reveal:"):
        return

    secret_id = data.split(":", 1)[1]
    secret = WHISPERS.get(secret_id)

    if not secret:
        await query.answer("⚠️ الرسالة غير موجودة أو انتهت صلاحيتها.", show_alert=True)
        return

    clicker = query.from_user
    is_target = (clicker.username or "").lower() == secret["target_username"]
    is_sender = clicker.id == secret["sender_id"]

    if is_target or is_sender:
        await query.answer(secret["text"], show_alert=True)
    else:
        await query.answer("🚫 هذه الهمسة ليست لك.", show_alert=True)
