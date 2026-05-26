import re
from datetime import timedelta, datetime, timezone

from telegram import Update, Chat, User
from telegram.ext import ContextTypes


# ── Admin checks ───────────────────────────────────────────────────────────────

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int | None = None) -> bool:
    uid = user_id or update.effective_user.id
    chat = update.effective_chat
    if chat.type == Chat.PRIVATE:
        return False
    member = await context.bot.get_chat_member(chat.id, uid)
    return member.status in ("administrator", "creator")


async def require_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not await is_admin(update, context):
        await update.message.reply_text("يجب أن تكون مشرفًا في المجموعة لاستخدام هذا الأمر.")
        return False
    return True


async def get_admin_ids(bot, chat_id: int) -> list[int]:
    """Return user IDs of all human admins in the chat."""
    admins = await bot.get_chat_administrators(chat_id)
    return [a.user.id for a in admins if not a.user.is_bot]


async def notify_admins(bot, chat_id: int, message: str):
    """Send a private DM to every admin who has a private chat with the bot."""
    admin_ids = await get_admin_ids(bot, chat_id)
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, message)
        except Exception:
            pass


# ── Target resolution ──────────────────────────────────────────────────────────

def get_reply_user(update: Update) -> User | None:
    """Return the User the admin replied to, or None."""
    if update.message and update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    return None


# ── Duration parsing ───────────────────────────────────────────────────────────

_DURATION_RE = re.compile(r"^(\d+)(s|m|h|d|w)$", re.IGNORECASE)

_UNIT_SECONDS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
    "w": 604800,
}


def parse_duration(token: str) -> timedelta | None:
    """Parse a duration string like '7d', '2h', '30m' into a timedelta.
    Returns None if the token is not a duration."""
    m = _DURATION_RE.match(token)
    if not m:
        return None
    amount = int(m.group(1))
    unit = m.group(2).lower()
    return timedelta(seconds=amount * _UNIT_SECONDS[unit])


def fmt_duration(td: timedelta) -> str:
    total = int(td.total_seconds())
    if total >= 86400:
        days = total // 86400
        return f"{days} يوم"
    if total >= 3600:
        hours = total // 3600
        return f"{hours} ساعة"
    if total >= 60:
        mins = total // 60
        return f"{mins} دقيقة"
    return f"{total} ثانية"


def parse_ban_args(args: list[str], reply_user: User | None) -> tuple[int | None, timedelta | None, str | None, str | None]:
    """Parse /ban arguments.

    Forms:
      /ban (reply)                     → reply user, no duration, no reason
      /ban (reply) [duration] [reason] → reply user, optional duration + reason
      /ban <id> [duration] [reason]    → explicit user ID

    Returns: (user_id, duration, reason, error_message)
    """
    if reply_user and not args:
        return reply_user.id, None, None, None

    if reply_user:
        remaining = list(args)
        duration = None
        if remaining:
            dur = parse_duration(remaining[0])
            if dur:
                duration = dur
                remaining = remaining[1:]
        reason = " ".join(remaining) or None
        return reply_user.id, duration, reason, None

    if not args:
        return None, None, None, "قم بالرد على رسالة المستخدم أو أرسل /ban <معرف> [مدة] [سبب]"

    try:
        user_id = int(args[0])
    except ValueError:
        return None, None, None, "معرف المستخدم غير صالح. الاستخدام: /ban <معرف> [مدة] [سبب]"

    remaining = list(args[1:])
    duration = None
    if remaining:
        dur = parse_duration(remaining[0])
        if dur:
            duration = dur
            remaining = remaining[1:]
    reason = " ".join(remaining) or None
    return user_id, duration, reason, None


def expires_at_from_duration(duration: timedelta | None) -> datetime | None:
    if duration is None:
        return None
    return datetime.now(timezone.utc) + duration


def fmt_user(user: User) -> str:
    name = user.full_name
    if user.username:
        return f"{name} (@{user.username})"
    return f"{name} [المعرف: {user.id}]"


# ── Telegram registration date estimation ───────────────────────────────────────

# Known approximate (user_id, year, month) milestones
_ID_MILESTONES = [
    (10_000_000,    2013, 11),
    (50_000_000,    2014,  9),
    (100_000_000,   2015,  6),
    (200_000_000,   2017,  1),
    (300_000_000,   2018,  1),
    (400_000_000,   2018,  7),
    (500_000_000,   2019,  1),
    (600_000_000,   2019,  5),
    (700_000_000,   2019,  9),
    (800_000_000,   2020,  1),
    (900_000_000,   2020,  5),
    (1_000_000_000, 2020,  8),
    (1_100_000_000, 2021,  1),
    (1_300_000_000, 2021,  7),
    (1_500_000_000, 2021, 10),
    (1_700_000_000, 2022,  2),
    (2_000_000_000, 2022,  6),
    (2_500_000_000, 2022, 12),
    (3_000_000_000, 2023,  4),
    (4_000_000_000, 2023,  9),
    (5_000_000_000, 2024,  1),
    (6_000_000_000, 2024,  7),
    (7_000_000_000, 2025,  1),
]

_MONTH_AR = [
    "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]


def estimate_telegram_registration(user_id: int) -> str:
    """Return an approximate Telegram registration month/year in Arabic."""
    if user_id < 10_000_000:
        return "2013 (تقريبي)"

    prev_id, prev_y, prev_m = 10_000_000, 2013, 11
    for (next_id, next_y, next_m) in _ID_MILESTONES[1:]:
        if user_id <= next_id:
            # Linear interpolation between two milestones
            ratio = (user_id - prev_id) / (next_id - prev_id)
            prev_months = prev_y * 12 + prev_m - 1
            next_months = next_y * 12 + next_m - 1
            total_months = round(prev_months + ratio * (next_months - prev_months))
            year  = total_months // 12
            month = total_months % 12 + 1
            return f"{_MONTH_AR[month]} {year} (تقريبي)"
        prev_id, prev_y, prev_m = next_id, next_y, next_m

    return "2025+ (تقريبي)"
