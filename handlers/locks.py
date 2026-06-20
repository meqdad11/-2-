import logging
import re
from telegram import Update, ChatPermissions
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes, ApplicationHandlerStop
from utils import database as db
from utils.helpers import check_permission

logger = logging.getLogger(__name__)

# ================================================
# دوال القفل والفتح (24 نوعاً — حُذف: id, notifications, iranian, porn)
# ================================================

async def cmd_lock_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "links", True)
    await update.message.reply_text("🔒 تم قفل الروابط.")
async def cmd_unlock_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "links", False)
    await update.message.reply_text("🔓 تم فتح الروابط.")

async def cmd_lock_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "tags", True)
    await update.message.reply_text("🔒 تم قفل التاك.")
async def cmd_unlock_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "tags", False)
    await update.message.reply_text("🔓 تم فتح التاك.")

async def cmd_lock_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "media", True)
    await update.message.reply_text("🔒 تم قفل الميديا.")
async def cmd_unlock_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "media", False)
    await update.message.reply_text("🔓 تم فتح الميديا.")

async def cmd_lock_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "files", True)
    await update.message.reply_text("🔒 تم قفل الملفات.")
async def cmd_unlock_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "files", False)
    await update.message.reply_text("🔓 تم فتح الملفات.")

async def cmd_lock_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "video", True)
    await update.message.reply_text("🔒 تم قفل الفيديو.")
async def cmd_unlock_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "video", False)
    await update.message.reply_text("🔓 تم فتح الفيديو.")

async def cmd_lock_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "voice", True)
    await update.message.reply_text("🔒 تم قفل الفويسات.")
async def cmd_unlock_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "voice", False)
    await update.message.reply_text("🔓 تم فتح الفويسات.")

async def cmd_lock_gifs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "gifs", True)
    await update.message.reply_text("🔒 تم قفل الملصقات والمتحركات.")
async def cmd_unlock_gifs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "gifs", False)
    await update.message.reply_text("🔓 تم فتح الملصقات والمتحركات.")

async def cmd_lock_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "edit", True)
    await update.message.reply_text("🔒 تم قفل تعديل الرسائل.")
async def cmd_unlock_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "edit", False)
    await update.message.reply_text("🔓 تم فتح تعديل الرسائل.")

async def cmd_lock_editmedia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "editmedia", True)
    await update.message.reply_text("🔒 تم قفل تعديل الميديا.")
async def cmd_unlock_editmedia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "editmedia", False)
    await update.message.reply_text("🔓 تم فتح تعديل الميديا.")

async def cmd_lock_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "repeat", True)
    await update.message.reply_text("🔒 تم قفل التكرار.")
async def cmd_unlock_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "repeat", False)
    await update.message.reply_text("🔓 تم فتح التكرار.")

async def cmd_lock_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "join", True)
    await update.message.reply_text("🔒 تم قفل الدخول — سيتم طرد الأعضاء الجدد تلقائياً.")
async def cmd_unlock_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "join", False)
    await update.message.reply_text("🔓 تم فتح الدخول.")

async def cmd_lock_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "forward", True)
    await update.message.reply_text("🔒 تم قفل التوجيه.")
async def cmd_unlock_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "forward", False)
    await update.message.reply_text("🔓 تم فتح التوجيه.")

async def cmd_lock_badwords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "badwords", True)
    await update.message.reply_text("🔒 تم قفل السب.")
async def cmd_unlock_badwords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "badwords", False)
    await update.message.reply_text("🔓 تم فتح السب.")

async def cmd_lock_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "spam", True)
    await update.message.reply_text("🔒 تم قفل السبام (5 رسائل/10 ثوان).")
async def cmd_unlock_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "spam", False)
    await update.message.reply_text("🔓 تم فتح السبام.")

async def cmd_lock_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "replies", True)
    await update.message.reply_text("🔒 تم قفل الردود.")
async def cmd_unlock_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "replies", False)
    await update.message.reply_text("🔓 تم فتح الردود.")

async def cmd_lock_persian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "persian", True)
    await update.message.reply_text("🔒 تم قفل الفارسية.")
async def cmd_unlock_persian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "persian", False)
    await update.message.reply_text("🔓 تم فتح الفارسية.")

async def cmd_lock_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "bots", True)
    await update.message.reply_text("🔒 تم قفل دخول البوتات.")
async def cmd_unlock_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "bots", False)
    await update.message.reply_text("🔓 تم فتح دخول البوتات.")

async def cmd_lock_longtext(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "longtext", True)
    await update.message.reply_text("🔒 تم قفل الكلام الكثير (+300 حرف).")
async def cmd_unlock_longtext(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "longtext", False)
    await update.message.reply_text("🔓 تم فتح الكلام الكثير.")

async def cmd_lock_quran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ هذا القفل غير مدعوم.")
async def cmd_unlock_quran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ هذا القفل غير مدعوم.")

async def cmd_lock_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "ai", True)
    await update.message.reply_text("🔒 تم قفل الذكاء الاصطناعي.")
async def cmd_unlock_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "ai", False)
    await update.message.reply_text("🔓 تم فتح الذكاء الاصطناعي.")

async def cmd_lock_autoreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "autoreply", True)
    await update.message.reply_text("🔒 تم قفل الرد التلقائي.")
async def cmd_unlock_autoreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "autoreply", False)
    await update.message.reply_text("🔓 تم فتح الرد التلقائي.")

async def cmd_lock_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "games", True)
    await update.message.reply_text("🔒 تم قفل الألعاب.")
async def cmd_unlock_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "games", False)
    await update.message.reply_text("🔓 تم فتح الألعاب.")

async def cmd_lock_marketnews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "marketnews", True)
    await update.message.reply_text("🔒 تم قفل أخبار السوق.")
async def cmd_unlock_marketnews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "marketnews", False)
    await update.message.reply_text("🔓 تم فتح أخبار السوق.")

async def cmd_lock_whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "whisper", True)
    await update.message.reply_text("🔒 تم قفل الهمسة.")
async def cmd_unlock_whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    await db.set_lock(update.effective_chat.id, "whisper", False)
    await update.message.reply_text("🔓 تم فتح الهمسة.")

# ---- دوال محذوفة (موجودة للتوافق فقط — لا تفعل شيئاً) ----
async def cmd_lock_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ هذا القفل غير مدعوم.")
async def cmd_unlock_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ هذا القفل غير مدعوم.")
async def cmd_lock_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ هذا القفل غير مدعوم.")
async def cmd_unlock_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ هذا القفل غير مدعوم.")
async def cmd_lock_iranian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ هذا القفل غير مدعوم.")
async def cmd_unlock_iranian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ هذا القفل غير مدعوم.")
async def cmd_lock_porn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ هذا القفل غير مدعوم.")
async def cmd_unlock_porn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ هذا القفل غير مدعوم.")

# ================================================
# قفل وفتح الكل
# ================================================
LOCK_TYPES = [
    "links", "tags", "media", "files", "video", "voice", "gifs",
    "edit", "editmedia", "repeat", "join", "forward", "badwords",
    "spam", "replies", "persian", "bots", "longtext",
    "ai", "autoreply", "games", "marketnews", "whisper"
]

async def cmd_lock_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    for lt in LOCK_TYPES:
        await db.set_lock(update.effective_chat.id, lt, True)
    await update.message.reply_text("🔒 تم قفل جميع الحمايات.")

async def cmd_unlock_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update, context, required_rank=3): return
    for lt in LOCK_TYPES:
        await db.set_lock(update.effective_chat.id, lt, False)
    await update.message.reply_text("🔓 تم فتح جميع الحمايات.")


# ================================================
# كلمات أخبار السوق والقرآن (للكشف)
# ================================================
MARKET_KEYWORDS = [
    "سهم", "أسهم", "اسهم", "سوق المال", "تداول", "بورصة", "ناسداك",
    "داو جونز", "نيكاي", "بيتكوين", "عملة رقمية", "crypto", "bitcoin",
    "forex", "فوركس", "مؤشر", "صندوق", "etf", "ربح", "خسارة", "استثمار"
]

QURAN_PATTERN = re.compile(
    r'(بِسْمِ اللَّهِ|قُلْ هُوَ اللَّهُ|إِنَّا أَعْطَيْنَاكَ|الْحَمْدُ لِلَّهِ رَبِّ|'
    r'وَالْعَصْرِ|قُلْ أَعُوذُ|سورة|آية \d+|\d+:\d+)'
)


# ================================================
# تتبع السبام (ذاكرة مؤقتة)
# ================================================
# { (user_id, chat_id): [timestamps] }
_spam_tracker: dict = {}


def _check_spam(user_id: int, chat_id: int) -> bool:
    """يرجع True لو العضو أرسل 5 رسائل أو أكثر خلال 10 ثوان."""
    import time
    key = (user_id, chat_id)
    now = time.time()
    timestamps = _spam_tracker.get(key, [])
    # احتفظ بالرسائل اللي خلال آخر 10 ثوان فقط
    timestamps = [t for t in timestamps if now - t < 10]
    timestamps.append(now)
    _spam_tracker[key] = timestamps
    return len(timestamps) >= 5


# ================================================
# تتبع التكرار (ذاكرة مؤقتة)
# ================================================
# { (user_id, chat_id): last_message_text }
_last_message: dict = {}


# ================================================
# فلترة المحتوى الشاملة
# ================================================
async def filter_locked_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    chat_id = msg.chat.id
    user = msg.from_user
    is_edit = update.edited_message is not None

    if not user or user.is_bot:
        return

    # ⚠️ وضع اختبار مؤقت: تم تعطيل استثناء المشرفين، الأقفال تطبّق على الجميع.
    # لرجوع استثناء المشرفين، أزل علامة التعليق عن الكتلة التالية:
    # try:
    #     member = await context.bot.get_chat_member(chat_id, user.id)
    #     if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
    #         return
    # except:
    #     pass

    async def remove(reason: str, violation_type: str, detail: str = ""):
        try:
            await msg.delete()
        except:
            pass
        await db.add_violation(user.id, chat_id, violation_type, detail[:200])
        try:
            await context.bot.send_message(chat_id, reason)
        except:
            pass
        raise ApplicationHandlerStop

    # ==================== تعديل الرسائل ====================
    if is_edit:
        if msg.text and await db.is_locked(chat_id, "edit"):
            await remove("🚫 تعديل الرسائل مقفل.", "edit")
            return
        if (msg.photo or msg.video or msg.document) and await db.is_locked(chat_id, "editmedia"):
            await remove("🚫 تعديل الميديا مقفل.", "editmedia")
            return
        return  # الرسائل المعدّلة لا تخضع لبقية الفلاتر

    # ==================== نصوص ====================
    if msg.text:
        text = msg.text

        # السبام
        if await db.is_locked(chat_id, "spam") and _check_spam(user.id, chat_id):
            await remove("🚫 السبام مقفل.", "spam", text)
            return

        # التكرار
        if await db.is_locked(chat_id, "repeat"):
            key = (user.id, chat_id)
            last = _last_message.get(key, "")
            if text.strip() == last.strip() and text.strip():
                await remove("🚫 التكرار مقفل.", "repeat", text)
                return
            _last_message[key] = text

        # الردود
        if msg.reply_to_message and await db.is_locked(chat_id, "replies"):
            await remove("🚫 الردود مقفلة.", "replies", text)
            return

        text_lower = text.lower()

        # الروابط
        if await db.is_locked(chat_id, "links"):
            if re.search(r'https?://|www\.|t\.me/|\.com|\.net|\.org', text_lower):
                await remove("🚫 الروابط مقفلة.", "link", text)
                return

        # التاك
        if "@" in text and await db.is_locked(chat_id, "tags"):
            await remove("🚫 التاك مقفل.", "tag", text)
            return

        # الكلمات المحظورة
        if await db.is_locked(chat_id, "badwords"):
            banned_words = await db.get_banned_words(chat_id)
            if any(word in text_lower for word in banned_words):
                await remove("🚫 كلمات ممنوعة.", "banned_word", text)
                return

        # النص الطويل
        if len(text) > 300 and await db.is_locked(chat_id, "longtext"):
            await remove("🚫 الكلام الكثير مقفل (+300 حرف).", "longtext", text[:200])
            return

        # الفارسية
        if await db.is_locked(chat_id, "persian"):
            if any("\u0600" <= c <= "\u06FF" for c in text):
                await remove("🚫 الكتابة بالفارسية مقفلة.", "persian", text)
                return

        # أخبار السوق
        if await db.is_locked(chat_id, "marketnews"):
            if any(kw in text_lower for kw in MARKET_KEYWORDS):
                await remove("🚫 أخبار السوق مقفلة.", "marketnews", text)
                return

        # آيات القرآن (تم إلغاؤه)

        # الهمس (أمر اهمس)
        if await db.is_locked(chat_id, "whisper"):
            if text.strip().startswith("اهمس"):
                await remove("🚫 الهمسة مقفلة.", "whisper", text)
                return

    # ==================== ميديا ====================
    if msg.photo and await db.is_locked(chat_id, "media"):
        await remove("🚫 الصور مقفلة.", "media")
        return

    if msg.video and await db.is_locked(chat_id, "video"):
        await remove("🚫 الفيديو مقفل.", "video")
        return

    # فويس نوت (مُصحَّح — كان msg.audio بالخطأ)
    if msg.voice and await db.is_locked(chat_id, "voice"):
        await remove("🚫 الفويسات مقفلة.", "voice")
        return

    # صوتيات عادية (audio)
    if msg.audio and await db.is_locked(chat_id, "voice"):
        await remove("🚫 الصوتيات مقفلة.", "audio")
        return

    if msg.document and await db.is_locked(chat_id, "files"):
        await remove("🚫 الملفات مقفلة.", "file")
        return

    if (msg.sticker or msg.animation) and await db.is_locked(chat_id, "gifs"):
        await remove("🚫 الملصقات والمتحركات مقفلة.", "sticker")
        return

    # ==================== توجيه ====================
    if getattr(msg, 'forward_date', None) and await db.is_locked(chat_id, "forward"):
        await remove("🚫 التوجيه مقفل.", "forward")
        return

    # ==================== ألعاب ====================
    if msg.game and await db.is_locked(chat_id, "games"):
        await remove("🚫 الألعاب مقفلة.", "game")
        return


# ================================================
# هاندلر الأعضاء الجدد (قفل الدخول + قفل البوتات)
# ================================================
async def filter_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يتنفذ عند دخول أي عضو جديد — يطرد لو الدخول أو البوتات مقفلة."""
    msg = update.message
    if not msg or not msg.new_chat_members:
        return
    chat_id = msg.chat.id

    join_locked = await db.is_locked(chat_id, "join")
    bots_locked = await db.is_locked(chat_id, "bots")

    for new_member in msg.new_chat_members:
        should_kick = False
        reason = ""

        if new_member.is_bot and bots_locked:
            should_kick = True
            reason = "🚫 دخول البوتات مقفل."
        elif not new_member.is_bot and join_locked:
            should_kick = True
            reason = "🚫 الدخول مقفل حالياً."

        if should_kick:
            try:
                await context.bot.ban_chat_member(chat_id, new_member.id)
                await context.bot.unban_chat_member(chat_id, new_member.id)
                await context.bot.send_message(chat_id, reason)
            except Exception as e:
                logger.error(f"فشل طرد العضو {new_member.id}: {e}")
