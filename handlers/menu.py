from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👮 أوامر المشرفين", callback_data="menu_admin"),
         InlineKeyboardButton("👥 للجميع", callback_data="menu_user")],
        [InlineKeyboardButton("🎵 الميديا", callback_data="menu_media"),
         InlineKeyboardButton("📚 الموارد", callback_data="menu_resources")],
        [InlineKeyboardButton("📋 الأوامر المتقدمة", callback_data="menu_commands"),
         InlineKeyboardButton("🎮 ألعاب", callback_data="menu_games")],
        [InlineKeyboardButton("🔍 بحث جوجل", callback_data="menu_google"),
         InlineKeyboardButton("📞 تواصل", callback_data="menu_contact")],
        [InlineKeyboardButton("🤫 الهمس", callback_data="menu_whisper")],
        [InlineKeyboardButton("🆘 طوارئ — أحتاج أحد", callback_data="menu_emergency")],
        [InlineKeyboardButton("📢 قناة تحديثات شفق", url="https://t.me/shafaqmeqdad")],
        [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
    ]
    await update.message.reply_text(
        "🌅 بوت شفق — القائمة الرئيسية\nاختر القسم:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
