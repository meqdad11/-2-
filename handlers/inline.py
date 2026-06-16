import logging
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters

logger = logging.getLogger(__name__)
whisper_storage = {}

def generate_whisper_id(sender_id: int, target_id: int, text: str) -> str:
    raw = f"{sender_id}_{target_id}_{text}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

async def handle_text_whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """همسة بالرد على الشخص: اكتب 'اهمس النص' ورد على رسالة الشخص"""
    msg = update.message
    if not msg or not msg.text or not msg.reply_to_message:
        return

    text = msg.text.strip()
    if not text.startswith("اهمس "):
        return

    whisper_text = text[5:].strip()
    if not whisper_text:
        await msg.reply_text("❌ اكتب الهمسة بعد 'اهمس'. مثال: اهمس مرحبا بك")
        return

    target = msg.reply_to_message.from_user
    sender = msg.from_user

    if target.is_bot:
        await msg.reply_text("❌ لا يمكن إرسال همسة لبوت.")
        return

    if target.id == sender.id:
        await msg.reply_text("❌ لا يمكنك إرسال همسة لنفسك.")
        return

    whisper_id = generate_whisper_id(sender.id, target.id, whisper_text)
    whisper_storage[whisper_id] = {
        "sender_id": sender.id,
        "sender_name": sender.first_name,
        "target_id": target.id,
        "text": whisper_text
    }

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 همسة خاصة", callback_data=f"whisper_{whisper_id}")]
    ])

    await msg.reply_text(
        f"💌 همسة خاصة من {sender.first_name} إلى {target.first_name}",
        reply_markup=keyboard
    )

    # حذف رسالة المرسل (اختياري)
    try:
        await msg.delete()
    except:
        pass

async def handle_whisper_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    whisper_id = query.data.replace("whisper_", "")
    data = whisper_storage.get(whisper_id)

    if not data:
        await query.answer("❌ انتهت صلاحية الهمسة.", show_alert=True)
        return

    presser = query.from_user

    if presser.id == data["sender_id"] or presser.id == data["target_id"]:
        await query.answer(
            f"💬 همسة من {data['sender_name']}:\n\n{data['text']}",
            show_alert=True
        )
    else:
        await query.answer("🔒 هذه الهمسة ليست لك.", show_alert=True)

def register_whisper_handlers(app):
    app.add_handler(MessageHandler(
        filters.TEXT & filters.REPLY & filters.ChatType.GROUPS,
        handle_text_whisper
    ))
    app.add_handler(CallbackQueryHandler(handle_whisper_callback, pattern=r"^whisper_"))