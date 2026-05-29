async def cmd_lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    from telegram import ChatPermissions
    chat_id = update.effective_chat.id
    try:
        await context.bot.set_chat_permissions(
            chat_id, 
            permissions=ChatPermissions(
                can_send_messages=False,
            )
        )
        await update.message.reply_text("🔒 تم إغلاق المجموعة.")
        await db.log_event(chat_id, "lock", user_id=update.effective_user.id)
    except Exception as e:
        logger.error("خطأ الإغلاق: %s", e)
        await update.message.reply_text(f"❌ تعذّر الإغلاق: {e}")


async def cmd_unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    from telegram import ChatPermissions
    chat_id = update.effective_chat.id
    try:
        # إعادة تفعيل جميع الصلاحيات
        await context.bot.set_chat_permissions(
            chat_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
            ),
        )
        await update.message.reply_text("🔓 تم فتح المجموعة بنجاح ✅")
        await db.log_event(chat_id, "unlock", user_id=update.effective_user.id)
    except Exception as e:
        logger.error("خطأ الفتح: %s", e)
        await update.message.reply_text(f"❌ تعذّر الفتح: {e}")
