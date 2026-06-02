import logging
from telegram import Update, ChatPermissions
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes
import database as db
from helpers import is_admin

logger = logging.getLogger(__name__)

# ================================================
# دوال القفل والفتح لجميع الأنواع (28 نوعاً)
# ================================================

async def cmd_lock_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "links", True)
    await update.message.reply_text("🔒 تم قفل الروابط.")
async def cmd_unlock_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "links", False)
    await update.message.reply_text("🔓 تم فتح الروابط.")

async def cmd_lock_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "tags", True)
    await update.message.reply_text("🔒 تم قفل التاك.")
async def cmd_unlock_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "tags", False)
    await update.message.reply_text("🔓 تم فتح التاك.")

async def cmd_lock_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "media", True)
    await update.message.reply_text("🔒 تم قفل الميديا.")
async def cmd_unlock_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "media", False)
    await update.message.reply_text("🔓 تم فتح الميديا.")

async def cmd_lock_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "files", True)
    await update.message.reply_text("🔒 تم قفل الملفات.")
async def cmd_unlock_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "files", False)
    await update.message.reply_text("🔓 تم فتح الملفات.")

async def cmd_lock_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "video", True)
    await update.message.reply_text("🔒 تم قفل الفيديو.")
async def cmd_unlock_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "video", False)
    await update.message.reply_text("🔓 تم فتح الفيديو.")

async def cmd_lock_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "voice", True)
    await update.message.reply_text("🔒 تم قفل الفويسات.")
async def cmd_unlock_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "voice", False)
    await update.message.reply_text("🔓 تم فتح الفويسات.")

async def cmd_lock_gifs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "gifs", True)
    await update.message.reply_text("🔒 تم قفل المتحركات.")
async def cmd_unlock_gifs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "gifs", False)
    await update.message.reply_text("🔓 تم فتح المتحركات.")

async def cmd_lock_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "edit", True)
    await update.message.reply_text("🔒 تم قفل التعديل.")
async def cmd_unlock_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "edit", False)
    await update.message.reply_text("🔓 تم فتح التعديل.")

async def cmd_lock_editmedia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "editmedia", True)
    await update.message.reply_text("🔒 تم قفل تعديل الميديا.")
async def cmd_unlock_editmedia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "editmedia", False)
    await update.message.reply_text("🔓 تم فتح تعديل الميديا.")

async def cmd_lock_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "repeat", True)
    await update.message.reply_text("🔒 تم قفل التكرار.")
async def cmd_unlock_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "repeat", False)
    await update.message.reply_text("🔓 تم فتح التكرار.")

async def cmd_lock_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "join", True)
    await update.message.reply_text("🔒 تم قفل الدخول.")
async def cmd_unlock_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "join", False)
    await update.message.reply_text("🔓 تم فتح الدخول.")

async def cmd_lock_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "forward", True)
    await update.message.reply_text("🔒 تم قفل التوجيه.")
async def cmd_unlock_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "forward", False)
    await update.message.reply_text("🔓 تم فتح التوجيه.")

async def cmd_lock_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "id", True)
    await update.message.reply_text("🔒 تم قفل ايدي.")
async def cmd_unlock_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "id", False)
    await update.message.reply_text("🔓 تم فتح ايدي.")

async def cmd_lock_badwords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "badwords", True)
    await update.message.reply_text("🔒 تم قفل السب.")
async def cmd_unlock_badwords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "badwords", False)
    await update.message.reply_text("🔓 تم فتح السب.")

async def cmd_lock_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "spam", True)
    await update.message.reply_text("🔒 تم قفل السبام.")
async def cmd_unlock_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "spam", False)
    await update.message.reply_text("🔓 تم فتح السبام.")

async def cmd_lock_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "replies", True)
    await update.message.reply_text("🔒 تم قفل الردود.")
async def cmd_unlock_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "replies", False)
    await update.message.reply_text("🔓 تم فتح الردود.")

async def cmd_lock_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "notifications", True)
    await update.message.reply_text("🔒 تم قفل الاشعارات.")
async def cmd_unlock_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "notifications", False)
    await update.message.reply_text("🔓 تم فتح الاشعارات.")

async def cmd_lock_persian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "persian", True)
    await update.message.reply_text("🔒 تم قفل الفارسيه.")
async def cmd_unlock_persian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "persian", False)
    await update.message.reply_text("🔓 تم فتح الفارسيه.")

async def cmd_lock_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "bots", True)
    await update.message.reply_text("🔒 تم قفل البوتات.")
async def cmd_unlock_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "bots", False)
    await update.message.reply_text("🔓 تم فتح البوتات.")

async def cmd_lock_iranian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "iranian", True)
    await update.message.reply_text("🔒 تم قفل دخول الايراني.")
async def cmd_unlock_iranian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "iranian", False)
    await update.message.reply_text("🔓 تم فتح دخول الايراني.")

async def cmd_lock_longtext(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "longtext", True)
    await update.message.reply_text("🔒 تم قفل الكلام الكثير.")
async def cmd_unlock_longtext(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "longtext", False)
    await update.message.reply_text("🔓 تم فتح الكلام الكثير.")

async def cmd_lock_quran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "quran", True)
    await update.message.reply_text("🔒 تم قفل القران.")
async def cmd_unlock_quran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "quran", False)
    await update.message.reply_text("🔓 تم فتح القران.")

async def cmd_lock_porn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "porn", True)
    await update.message.reply_text("🔒 تم قفل الاباحي.")
async def cmd_unlock_porn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "porn", False)
    await update.message.reply_text("🔓 تم فتح الاباحي.")

async def cmd_lock_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "ai", True)
    await update.message.reply_text("🔒 تم قفل الذكاء.")
async def cmd_unlock_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "ai", False)
    await update.message.reply_text("🔓 تم فتح الذكاء.")

async def cmd_lock_autoreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "autoreply", True)
    await update.message.reply_text("🔒 تم قفل الرد التلقائي.")
async def cmd_unlock_autoreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "autoreply", False)
    await update.message.reply_text("🔓 تم فتح الرد التلقائي.")

async def cmd_lock_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "games", True)
    await update.message.reply_text("🔒 تم قفل الالعاب.")
async def cmd_unlock_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "games", False)
    await update.message.reply_text("🔓 تم فتح الالعاب.")

async def cmd_lock_marketnews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "marketnews", True)
    await update.message.reply_text("🔒 تم قفل اخبار السوق.")
async def cmd_unlock_marketnews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "marketnews", False)
    await update.message.reply_text("🔓 تم فتح اخبار السوق.")

async def cmd_lock_whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "whisper", True)
    await update.message.reply_text("🔒 تم قفل الهمسه.")
async def cmd_unlock_whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    await db.set_lock(update.effective_chat.id, "whisper", False)
    await update.message.reply_text("🔓 تم فتح الهمسه.")

# ================================================
# قفل وفتح الكل
# ================================================
async def cmd_lock_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    types = ["links","tags","media","files","video","voice","gifs","edit","editmedia","repeat","join","forward","id","badwords","spam","replies","notifications","persian","bots","iranian","longtext","quran","porn","ai","autoreply","games","marketnews","whisper"]
    for lt in types:
        await db.set_lock(update.effective_chat.id, lt, True)
    await update.message.reply_text("🔒 تم قفل جميع الحمايات.")

async def cmd_unlock_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ للمشرفين فقط.")
    types = ["links","tags","media","files","video","voice","gifs","edit","editmedia","repeat","join","forward","id","badwords","spam","replies","notifications","persian","bots","iranian","longtext","quran","porn","ai","autoreply","games","marketnews","whisper"]
    for lt in types:
        await db.set_lock(update.effective_chat.id, lt, False)
    await update.message.reply_text("🔓 تم فتح جميع الحمايات.")

# ================================================
# فلترة المحتوى الشاملة (تمنع كل شيء حسب القفل)
# ================================================
async def filter_locked_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    chat_id = msg.chat.id
    user = msg.from_user

    # تجاهل البوتات والمشرفين
    if user and user.is_bot:
        return
    try:
        member = await context.bot.get_chat_member(chat_id, user.id)
        if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
            return
    except:
        pass

    # --- نصوص ---
    if msg.text:
        text = msg.text.lower()
        # الروابط
        if ("http://" in text or "https://" in text or "www." in text or ".com" in text):
            if await db.is_locked(chat_id, "links"):
                await msg.delete()
                await msg.reply_text("🚫 الروابط مقفلة.")
                return
        # التاك
        if "@" in text and await db.is_locked(chat_id, "tags"):
            await msg.delete()
            await msg.reply_text("🚫 التاك مقفل.")
            return
        # الكلمات المحظورة
        banned_words = await db.get_banned_words(chat_id)
        if any(word in text for word in banned_words) and await db.is_locked(chat_id, "badwords"):
            await msg.delete()
            await msg.reply_text("🚫 كلمات ممنوعة.")
            return
        # النص الطويل
        if len(text) > 300 and await db.is_locked(chat_id, "longtext"):
            await msg.delete()
            await msg.reply_text("🚫 الكلام الكثير مقفل.")
            return
        # الفارسية
        if any("\u0600" <= c <= "\u06FF" for c in text) and await db.is_locked(chat_id, "persian"):
            await msg.delete()
            await msg.reply_text("🚫 الكتابة بالفارسية مقفلة.")
            return

    # --- صور ---
    if msg.photo and await db.is_locked(chat_id, "media"):
        await msg.delete()
        await msg.reply_text("🚫 الصور مقفلة.")
        return

    # --- فيديو ---
    if msg.video and await db.is_locked(chat_id, "video"):
        await msg.delete()
        await msg.reply_text("🚫 الفيديو مقفل.")
        return

    # --- صوت ---
    if msg.audio and await db.is_locked(chat_id, "voice"):
        await msg.delete()
        await msg.reply_text("🚫 الصوتيات مقفلة.")
        return

    # --- ملفات ---
    if msg.document and await db.is_locked(chat_id, "files"):
        await msg.delete()
        await msg.reply_text("🚫 الملفات مقفلة.")
        return

    # --- ملصقات / متحركات ---
    if msg.sticker and await db.is_locked(chat_id, "gifs"):
        await msg.delete()
        await msg.reply_text("🚫 الملصقات والمتحركات مقفلة.")
        return

    # --- توجيه (إعادة إرسال) ---
    if msg.forward_date and await db.is_locked(chat_id, "forward"):
        await msg.delete()
        await msg.reply_text("🚫 التوجيه مقفل.")
        return

    # --- ألعاب ---
    if msg.game and await db.is_locked(chat_id, "games"):
        await msg.delete()
        await msg.reply_text("🚫 الألعاب مقفلة.")
        return