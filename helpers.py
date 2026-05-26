import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def require_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not await is_admin(update, context):
        await update.message.reply_text("يجب أن تكون مشرفاً في المجموعة لاستخدام هذا الأمر.")
        return False
    return True


def get_reply_user(update: Update):
    if update.message and update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    return None


async def get_admin_ids(bot, chat_id: int) -> list:
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return [a.user.id for a in admins if not a.user.is_bot]
    except Exception:
        return []


async def notify_admins(bot, chat_id: int, text: str):
    try:
        admin_ids = await get_admin_ids(bot, chat_id)
        for admin_id in admin_ids:
            try:
                await bot.send_message(admin_id, text)
            except Exception:
                pass
    except Exception:
        pass
def parse_duration(duration_str: str) -> Optional[timedelta]:
    if not duration_str:
        return None
    try:
        if duration_str.endswith("h"):
            return timedelta(hours=int(duration_str[:-1]))
        elif duration_str.endswith("d"):
            return timedelta(days=int(duration_str[:-1]))
        elif duration_str.endswith("m"):
            return timedelta(minutes=int(duration_str[:-1]))
        elif duration_str.endswith("w"):
            return timedelta(weeks=int(duration_str[:-1]))
    except ValueError:
        pass
    return None


def expires_at_from_duration(duration: Optional[timedelta]) -> Optional[datetime]:
    if not duration:
        return None
    return datetime.now(timezone.utc) + duration


def fmt_duration(duration: Optional[timedelta]) -> str:
    if not duration:
        return "دائم"
    total = int(duration.total_seconds())
    if total >= 86400:
        return f"{total // 86400} يوم"
    elif total >= 3600:
        return f"{total // 3600} ساعة"
    elif total >= 60:
        return f"{total // 60} دقيقة"
    return f"{total} ثانية"


def fmt_user(user) -> str:
    if user.username:
        return f"@{user.username}"
    return f"{user.first_name} ({user.id})"


def parse_ban_args(args: list, reply_user=None):
    user_id = None
    duration = None
    reason = None
    err = None

    if reply_user:
        user_id = reply_user.id
        if args:
            dur = parse_duration(args[0])
            if dur:
                duration = dur
                reason = " ".join(args[1:]) or None
            else:
                reason = " ".join(args) or None
    elif args:
        try:
            user_id = int(args[0])
            remaining = args[1:]
            if remaining:
                dur = parse_duration(remaining[0])
                if dur:
                    duration = dur
                    reason = " ".join(remaining[1:]) or None
                else:
                    reason = " ".join(remaining) or None
        except ValueError:
            err = "الاستخدام: حظر <معرف> [مدة مثل 1d أو 7d] [سبب]"
    else:
        err = "قم بالرد على رسالة المستخدم أو أرسل: حظر <معرف>"

    return user_id, duration, reason, err


def estimate_telegram_registration(user_id: int) -> str:
    ranges = [
        (100000000,  "2013 أو قبل"),
        (200000000,  "2014"),
        (300000000,  "2015"),
        (400000000,  "2016-2017"),
        (500000000,  "2017-2018"),
        (600000000,  "2018-2019"),
        (700000000,  "2019-2020"),
        (800000000,  "2020-2021"),
        (900000000,  "2021"),
        (1000000000, "2021-2022"),
        (1500000000, "2022"),
        (2000000000, "2022-2023"),
        (5000000000, "2023-2024"),
    ]
    for limit, label in ranges:
        if user_id < limit:
            return label
    return "2024 أو أحدث"