import logging
import hashlib
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, InlineQueryHandler, CallbackQueryHandler

logger = logging.getLogger(__name__)
whisper_storage = {}

def generate_whisper_id(sender_id: int, target_username: str, text: str) -> str:
    raw = f"{sender_id}_{target_username}_{text}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

async def handle_inline_whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if not query:
        return
    parts = query.split(maxsplit=1)
    if len(parts) < 2:
        return
    target_username = parts[0].lstrip("@").lower()
    whisper_text = parts[1]
    if not whisper_text:
        return
    sender = update.inline_query.from_user
    whisper_id = generate_whisper_id(sender.id, target_username, whisper_text)
    whisper_storage[whisper_id] = {
        "sender_id": sender.id,
        "target_username": target_username,
        "text": whisper_text
    }
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 همسة خاصة", callback_data=f"whisper_{whisper_id}")]
    ])
    result = InlineQueryResultArticle(
        id=whisper_id,
        title=f"همسة إلى @{target_username}",
        description="اضغط على الزر لعرض الهمسة",
        input_message_content=InputTextMessageContent(f"💌 همسة خاصة من {sender.first_name}"),
        reply_markup=keyboard
    )
    await update.inline_query.answer([result], cache_time=0)

async def handle_whisper_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    whisper_id = query.data.replace("whisper_", "")
    data = whisper_storage.get(whisper_id)
    if not data:
        await query.answer("❌ انتهت صلاحية الهمسة.", show_alert=True)
        return
    presser = query.from_user
    if presser.id == data["sender_id"] or presser.username.lower() == data["target_username"]:
        await query.answer(f"💬 الهمسة:\n\n{data['text']}", show_alert=True)
    else:
        await query.answer("🔒 هذه الهمسة ليست لك.", show_alert=True)

def register_whisper_handlers(app):
    app.add_handler(InlineQueryHandler(handle_inline_whisper))
    app.add_handler(CallbackQueryHandler(handle_whisper_callback, pattern=r"^whisper_"))