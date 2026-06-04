import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from utils import database as db
from config import ADMIN_CHAT_ID

logger = logging.getLogger(__name__)

async def on_chat_member_updated(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return
    new_member = result.new_chat_member
    old_member = result.old_chat_member
    chat_id = result.chat.id
    user = new_member.user

    if new_member.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED):
        if old_member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
            ban = await db.get_ban(user.id, chat_id)
            if ban:
                try:
                    await context.bot.ban_chat_member(chat_id, user.id)
                except Exception as e:
                    logger.warning("تعذّر طرد المحظور: %s", e)
                reason = ban.get('reason') or 'لم يُحدد سبب'
                notice = (
                    f"⚠️ تنبيه للمشرفين!\n"
                    f"المستخدم {user.full_name} (ID: {user.id})\n"
                    f"حاول الدخول وهو محظور مسبقاً.\n"
                    f"سبب الحظر: {reason}\n"
                    f"تم طرده تلقائياً. 🚫"
                )
                await context.bot.send_message(chat_id, "⚠️ تم طرد عضو محظور تلقائياً.")
                try:
                    await context.bot.send_message(ADMIN_CHAT_ID, notice)
                except Exception:
                    pass
                await db.log_bot_action(chat_id, "auto_kick_banned", user_id=user.id, detail=reason)
            else:
                try:
                    photos = await context.bot.get_user_profile_photos(user.id, limit=1)
                    username = f"@{user.username}" if user.username else "بدون يوزر"
                    welcome = (
                        f"👋 أهلاً وسهلاً {user.first_name}!\n"
                        f"اليوزر: {username}\n"
                        f"نرحب بك في مجموعتنا. 😊\n"
                        f"يرجى الالتزام بالقواعد واحترام الجميع."
                    )
                    if photos.total_count > 0:
                        await context.bot.send_photo(
                            chat_id,
                            photo=photos.photos[0][-1].file_id,
                            caption=welcome
                        )
                    else:
                        await context.bot.send_message(chat_id, welcome)
                except Exception:
                    await context.bot.send_message(
                        chat_id,
                        f"👋 أهلاً {user.first_name}! نرحب بك في مجموعتنا. 😊"
                    )