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

    # عضو دخل فعلاً من خارج المجموعة
    is_new_member = old_member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED)

    # تجاهل تغييرات الكتم أو القيود — نتحقق أن العضو كان خارج المجموعة فعلاً
    if not is_new_member:
        return

    # العضو دخل وحالته الجديدة عضو أو مقيد (مثلاً قيود افتراضية)
    if new_member.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED):
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
            # التحقق من إعداد الترحيب
            welcome_enabled = await db.get_setting(chat_id, "welcome_enabled")
            if welcome_enabled == "no":
                return

            try:
                bio = "غير محدد"
                try:
                    full_chat = await context.bot.get_chat(user.id)
                    if full_chat.bio:
                        bio = full_chat.bio
                except:
                    pass

                photos = await context.bot.get_user_profile_photos(user.id, limit=1)
                username = f"@{user.username}" if user.username else "بدون يوزر"
                welcome = (
                    f"👋 أهلاً وسهلاً {user.first_name}!\n"
                    f"🆔 المعرف: {user.id}\n"
                    f"📎 اليوزر: {username}\n"
                    f"📝 البايو: {bio}\n\n"
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
 