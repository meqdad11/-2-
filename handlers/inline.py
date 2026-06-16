from telegram import Update
from telegram.ext import ContextTypes

async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

async def handle_chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass