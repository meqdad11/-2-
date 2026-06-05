import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes

async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query
    if not query:
        return
    # نافذة الكتابة
    results = [
        InlineQueryResultArticle(
            id="whisper_input",
            title="اكتب همستك هنا...",
            description="اضغط إرسال بعد كتابة الهمسة",
            input_message_content=InputTextMessageContent(
                message_text="✍️ جاري إرسال الهمسة..."
            )
        )
    ]
    await query.answer(results, cache_time=0, is_personal=True)

async def handle_chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chosen = update.chosen_inline_result
    if not chosen:
        return
    user_id = chosen.from_user.id
    whisper_text = chosen.query.strip()

    target_id = context.user_data.get('whisper_target_id')
    target_name = context.user_data.get('whisper_target_name', 'مجهول')
    sender_name = context.user_data.get('whisper_sender_name', chosen.from_user.first_name)
    chat_id = context.user_data.get('whisper_chat_id')

    if not target_id or not chat_id or not whisper_text:
        return

    context.user_data.pop('whisper_target_id', None)
    context.user_data.pop('whisper_target_name', None)
    context.user_data.pop('whisper_sender_name', None)
    context.user_data.pop('whisper_chat_id', None)

    whisper_id = str(uuid.uuid4())[:12]
    context.bot_data[f'whisper_{whisper_id}'] = {
        'sender_id': user_id,
        'sender_name': sender_name,
        'target_id': target_id,
        'target_name': target_name,
        'text': whisper_text,
        'created_at': datetime.now().isoformat()
    }

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("👁️ عرض الهمسة", callback_data=f"show_whisper_{whisper_id}")
    ]])
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"💌 **همسة خاصة** من {sender_name} إلى {target_name}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )