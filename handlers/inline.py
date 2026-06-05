import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query
    if not query or not query.query:
        return

    user_id = query.from_user.id
    whisper_text = query.query.strip()

    # استرجاع بيانات الجلسة
    target_id = context.user_data.get('whisper_target_id')
    target_name = context.user_data.get('whisper_target_name', 'مجهول')
    sender_name = context.user_data.get('whisper_sender_name', query.from_user.first_name)
    chat_id = context.user_data.get('whisper_chat_id')

    if not target_id or not chat_id:
        # إذا لم تكن هناك جلسة، لا تفعل شيئاً (أو أرسل نتيجة فارغة)
        return

    # تنظيف الجلسة
    context.user_data.pop('whisper_target_id', None)
    context.user_data.pop('whisper_target_name', None)
    context.user_data.pop('whisper_sender_name', None)
    context.user_data.pop('whisper_chat_id', None)

    # إنشاء معرف فريد للهمسة
    whisper_id = str(uuid.uuid4())[:12]

    # تخزين الهمسة في bot_data
    context.bot_data[f'whisper_{whisper_id}'] = {
        'sender_id': user_id,
        'sender_name': sender_name,
        'target_id': target_id,
        'target_name': target_name,
        'text': whisper_text,
        'created_at': datetime.now().isoformat()
    }

    # إرسال رسالة إلى القروب تحتوي على زر "عرض الهمسة"
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("👁️ عرض الهمسة", callback_data=f"show_whisper_{whisper_id}")
    ]])
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"💌 **همسة خاصة** من {sender_name} إلى {target_name}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )