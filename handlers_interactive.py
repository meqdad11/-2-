import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from helpers import is_admin

async def handle_interactive_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    text = msg.text.strip()
    chat_id = msg.chat.id

    if context.user_data.get('waiting_google') == chat_id:
        del context.user_data['waiting_google']
        query = text.replace(' ', '+')
        link = f"https://www.google.com/search?q={query}"
        await msg.reply_text(f"🔍 **نتائج البحث:**\n[اضغط هنا]({link})", parse_mode="Markdown", disable_web_page_preview=True)
        return

    if context.user_data.get('purge_mode') == chat_id:
        del context.user_data['purge_mode']
        # حذف رسالة واحدة بالرد
        if msg.reply_to_message and text == "حذف":
            try:
                await context.bot.delete_message(chat_id, msg.reply_to_message.message_id)
                temp = await msg.reply_text("🗑️ تم حذف الرسالة.")
                await asyncio.sleep(1)
                await temp.delete()
            except:
                await msg.reply_text("❌ لا يمكن حذف هذه الرسالة.")
            return
        if text.isdigit():
            count = int(text)
            if count > 100:
                await msg.reply_text("لا يمكن مسح أكثر من 100 رسالة.")
                return
            try:
                for i in range(count):
                    await context.bot.delete_message(chat_id, msg.message_id - i - 1)
                await msg.reply_text(f"🗑️ تم مسح {count} رسالة.")
            except:
                await msg.reply_text("فشل المسح، ربما الرسائل قديمة.")
        elif msg.reply_to_message:
            start_id = msg.reply_to_message.message_id
            deleted = 0
            for mid in range(start_id, msg.message_id):
                try:
                    await context.bot.delete_message(chat_id, mid)
                    deleted += 1
                except:
                    pass
            await msg.reply_text(f"🗑️ تم مسح {deleted} رسالة.")
        else:
            await msg.reply_text("أرسل عددًا أو رد على رسالة لمسح ما بعدها.")
        return

    if context.user_data.get('waiting_remind') == chat_id:
        del context.user_data['waiting_remind']
        parts = text.split(maxsplit=1)
        if len(parts) != 2 or not parts[0].isdigit():
            await msg.reply_text("❌ الصيغة: عدد الدقائق ثم النص (مثال: 5 تذكير بالاجتماع)")
            return
        minutes = int(parts[0])
        reminder_text = parts[1]
        delay = minutes * 60
        if delay > 86400:
            await msg.reply_text("لا يمكن ضبط تذكير لأكثر من يوم.")
            return
        context.job_queue.run_once(lambda ctx: ctx.bot.send_message(chat_id, f"⏰ تذكير: {reminder_text}"), delay)
        await msg.reply_text(f"✅ تم ضبط تذكير بعد {minutes} دقيقة.")
        return

    if context.user_data.get('waiting_translate') == chat_id:
        del context.user_data['waiting_translate']
        await msg.reply_text("🌐 خدمة الترجمة غير متاحة حالياً بسبب القيود التقنية. جرب يدوياً عبر Google Translate.")
        return

    if context.user_data.get('waiting_broadcast') == chat_id:
        del context.user_data['waiting_broadcast']
        if not await is_admin(update, context):
            await msg.reply_text("⛔ ليس لديك صلاحية.")
            return
        await context.bot.send_message(chat_id, f"📢 **بث من المشرف:**\n{text}", parse_mode="Markdown")
        await msg.reply_text("✅ تم إرسال البث.")
        return