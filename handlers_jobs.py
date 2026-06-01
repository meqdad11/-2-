import logging
import random
from datetime import datetime, timezone, timedelta
from telegram import Update
from telegram.ext import ContextTypes
import database as db
# ================================================

logger = logging.getLogger(__name__)
from config import ADMIN_CHAT_ID

DAILY_QUOTES = [
    "كل يوم جديد فرصة لبداية جديدة. 🌅",
    "خذ الأمور خطوة بخطوة. 🌱",
    "من حقك أن ترتاح عندما تحتاج لذلك. 🌿",
    "التقدم البسيط ما زال تقدماً. 👣",
    "طلب المساعدة دليل وعي وشجاعة. 🤝",
    "ليس عليك أن تحمل كل شيء وحدك. 🤍",
    "العواصف لا تدوم إلى الأبد. ☀️",
    "امنح نفسك بعض اللطف اليوم. 🌸",
    "الراحة جزء مهم من التعافي. 🌷",
    "حتى أصغر إنجاز يستحق التقدير. ⭐",
    "الأيام الصعبة تمر مهما طالت. 🌤️",
    "تنفس بعمق وركز على اللحظة الحالية. 🍃",
    "لا بأس إن لم يكن يومك مثالياً. 🌱",
    "كل خطوة للأمام لها قيمتها. 🚶",
    "امنح نفسك الوقت الذي تحتاجه. ⏳",
    "وجودك مهم وله قيمة. 🤍",
    "من الطبيعي أن تحتاج إلى الدعم أحياناً. 🌿",
    "الأمل قد يبدأ بفكرة صغيرة. ✨",
    "التعافي رحلة وليس سباقاً. 🛤️",
    "اهتم بنفسك كما تهتم بمن تحب. 🌸",
    "يمكنك البدء من جديد في أي وقت. 🌅",
    "ليس مطلوباً منك أن تكون قوياً دائماً. 🍀",
    "كل يوم فرصة جديدة للتعلم والنمو. 🌱",
    "بعض الراحة اليوم قد تصنع فرقاً غداً. 🌼",
    "ما تشعر به يستحق الإنصات. 👂",
    "الأمور العظيمة تبدأ بخطوات صغيرة. 🌟",
    "خذ وقتك، لا حاجة للاستعجال. ⏳",
    "الصبر يساعد على تجاوز الكثير. 🌿",
    "قد يكون اليوم أفضل مما تتوقع. ☀️",
    "أنت تستحق معاملة نفسك بلطف. 🌸",
    "الهدوء أحياناً إنجاز بحد ذاته. 🕊️",
    "التغيير يحتاج إلى وقت، وهذا طبيعي. 🌱",
    "كل محاولة للعناية بنفسك مهمة. 🌷",
    "الغد يحمل فرصاً جديدة. 🌄",
    "التعثر لا يلغي التقدم الذي حققته. 🌿",
    "خطوة واحدة تكفي لهذا اليوم. 👣",
    "لا بأس أن تطلب المساندة. 🤝",
    "يمكن للأمل أن ينمو حتى في الأيام الصعبة. 🌱",
    "اعتنِ بنفسك دون شعور بالذنب. 🤍",
    "كل يوم يمنحك فرصة أخرى للمحاولة. 🌅",
    "التقدم لا يُقاس بالسرعة فقط. 🛤️",
    "امنح نفسك فرصة للهدوء. 🍃",
    "لا تحكم على نفسك بقسوة. 🌸",
    "يوماً بعد يوم تتغير الأمور. 🌤️",
    "وجود من يستمع يحدث فرقاً. 💙",
    "يكفي أنك ما زلت تحاول. ⭐",
    "لا بأس أن تأخذ استراحة قصيرة. 🌼",
    "كن صبوراً مع نفسك. 🌿",
    "كل صباح بداية جديدة. ☀️",
    "الأمل لا يحتاج إلى ظروف مثالية لينمو. ✨",
    "الأيام المختلفة جزء طبيعي من الحياة. 🍂",
    "خذ ما تحتاجه من وقت للتعافي. 🌱",
    "التقدم الهادئ ما زال تقدماً حقيقياً. 🚶",
    "أحياناً تكون الراحة أفضل قرار. 🌷",
    "مشوار الألف ميل يبدأ بخطوة. 👣",
    "الحياة تتغير باستمرار، وكذلك الصعوبات. 🌤️",
    "الاعتناء بنفسك أمر مهم. 🌸",
    "هناك دائماً فرصة لبداية جديدة. 🌅",
    "الأوقات الصعبة لا تدوم للأبد. ☀️",
    "يوجد دائماً ما يستحق التمسك بالأمل من أجله. 🤍",
]

# ================================================

async def job_daily_quote(context: ContextTypes.DEFAULT_TYPE):
    chats = await db.get_all_active_chats()
    quote = random.choice(DAILY_QUOTES)
    for chat_id in chats:
        try:
            await context.bot.send_message(
                chat_id,
                f"🌅 اقتباس اليوم:\n\n{quote}"
            )
        except Exception as e:
            logger.warning("خطأ في إرسال اقتباس اليوم للمجموعة %s: %s", chat_id, e)

# ================================================




async def job_expire_bans(context: ContextTypes.DEFAULT_TYPE):
    expired = await db.get_expired_bans()
    for ban in expired:
        user_id = ban["user_id"]
        chat_id = ban["chat_id"]
        await db.remove_ban(user_id, chat_id)
        try:
            await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
            await context.bot.send_message(
                chat_id,
                f"انتهت مدة حظر المستخدم {user_id}. يمكنه الانضمام مجدداً."
            )
            await context.bot.send_message(
                user_id,
                "✅ انتهت مدة حظرك. يمكنك الانضمام للمجموعة مجدداً."
            )
        except Exception as e:
            logger.warning("خطأ في رفع الحظر: %s", e)

# ================================================

async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import Update, Chat as TGChat
    is_private = update.effective_chat.type == TGChat.PRIVATE
    if not is_private:
        from helpers import require_admin
        if not await require_admin(update, context):
            return
        if update.effective_user.id != ADMIN_CHAT_ID:
            await update.message.reply_text("غير مصرح لك.")
            return
    if is_private:
        chats = await db.get_all_active_chats()
        if not chats:
            await update.message.reply_text("لا توجد مجموعات مسجلة بعد.")
            return
        for chat_id in chats:
            now = datetime.now(timezone.utc)
            day_ago = (now - timedelta(days=1)).isoformat()
            actions = await db.get_bot_actions_since(chat_id, day_ago)
            bans = await db.get_ban_list(chat_id)
            top = await db.get_top_members(chat_id, 999)
            chat_name = await db.get_chat_name(chat_id)
            lines = []
            for a in actions[:10]:
                name = await db.get_user_name(chat_id, a['user_id'])
                detail = f" — {a['detail']}" if a.get('detail') else ""
                lines.append(f"\u200F• {a['action']} | \u202B{name}\u202C ({a['user_id']}){detail}")
            top_text = ""
            for i, m in enumerate(top, 1):
                name = await db.get_user_name(chat_id, m['user_id'])
                top_text += f"\u200F{i}. \u202B{name}\u202C — {m['message_count']} رسالة\n"
            report = (
                f"📊 تقرير — {chat_name}\n"
                f"{'━'*20}\n"
                f"🚫 محظورون: {len(bans)}\n"
                f"{'━'*20}\n"
                f"📋 آخر الإجراءات:\n"
                + ("\n".join(lines) if lines else "لا توجد إجراءات") +
                f"\n{'━'*20}\n"
                f"🏆 الأعضاء حسب النشاط:\n{top_text}"
            )
            await update.message.reply_text(report)
    else:
        now = datetime.now(timezone.utc)
        day_ago = (now - timedelta(days=1)).isoformat()
        chat_id = update.effective_chat.id
        actions = await db.get_bot_actions_since(chat_id, day_ago)
        bans = await db.get_ban_list(chat_id)
        top = await db.get_top_members(chat_id, 999)
        lines = []
        for a in actions[:20]:
            name = await db.get_user_name(chat_id, a['user_id'])
            detail = f" — {a['detail']}" if a.get('detail') else ""
            lines.append(f"\u200F• {a['action']} | \u202B{name}\u202C ({a['user_id']}){detail}")
        top_text = ""
        for i, m in enumerate(top, 1):
            name = await db.get_user_name(chat_id, m['user_id'])
            top_text += f"\u200F{i}. \u202B{name}\u202C — {m['message_count']} رسالة\n"
        report = (
            f"📊 تقرير المجموعة\n"
            f"{'━'*20}\n"
            f"🚫 محظورون: {len(bans)}\n"
            f"{'━'*20}\n"
            f"📋 آخر الإجراءات:\n"
            + ("\n".join(lines) if lines else "لا توجد إجراءات") +
            f"\n{'━'*20}\n"
            f"🏆 الأعضاء حسب النشاط:\n{top_text}"
        )
        await update.message.reply_text(report)