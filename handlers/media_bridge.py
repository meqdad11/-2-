import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def handle_media_from_userbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تستقبل الملفات من اليوزربوت وتُرسلها للمستخدم النهائي باسم البوت"""
    msg = update.message
    
    # 1. التأكد من أن المرسل هو اليوزربوت (حسابك الشخصي)
    if not msg or not msg.from_user or msg.from_user.id != 729970974:
        return

    # 2. استخراج معرف الدردشة الهدف من تعليق الملف
    target_chat_id = None
    if msg.caption and "__chat_id:" in msg.caption:
        try:
            target_chat_id = int(msg.caption.split("__chat_id:")[1].split("__")[0])
        except:
            pass

    if not target_chat_id:
        await msg.reply_text("❌ خطأ: لا يمكن تحديد وجهة الملف.")
        return

    # 3. إعادة إرسال الملف إلى المستخدم النهائي باسم شفق
    try:
        if msg.video:
            await context.bot.send_video(
                chat_id=target_chat_id,
                video=msg.video.file_id,
                caption=msg.caption.replace(f"__chat_id:{target_chat_id}__", "").strip()
            )
        elif msg.audio:
            await context.bot.send_audio(
                chat_id=target_chat_id,
                audio=msg.audio.file_id,
                title=msg.audio.title,
                performer=msg.audio.performer
            )
        elif msg.document:
            await context.bot.send_document(
                chat_id=target_chat_id,
                document=msg.document.file_id
            )
        else:
            await context.bot.send_message(chat_id=target_chat_id, text="📦 تم استلام ملف غير مدعوم.")
        
        # 4. حذف الرسالة الأصلية من الخاص (حتى يبقى نظيفاً)
        await msg.delete()
    except Exception as e:
        logger.error(f"فشل إرسال الملف للمستخدم: {e}")
        await context.bot.send_message(chat_id=target_chat_id, text="❌ فشل إرسال الملف.")