import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# دوال وهمية فقط للتوافق مع الاستيرادات في commands.py و app.py
async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ أرسل رابطاً مباشراً.")

async def cmd_sc_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ أرسل رابطاً مباشراً.")

async def cmd_yt_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ أرسل رابطاً مباشراً.")

async def handle_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

async def callback_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

async def callback_sc_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

async def callback_yt_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

async def callback_sc_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass