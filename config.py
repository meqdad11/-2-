import os
from zoneinfo import ZoneInfo

# ========== التوكن والمعرفات الأساسية ==========
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = 729970974

# ========== إعدادات التحذيرات ==========
MAX_WARNINGS = 3

# ========== المنطقة الزمنية ==========
TIMEZONE = ZoneInfo("Asia/Riyadh")
