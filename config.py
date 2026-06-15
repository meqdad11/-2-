import os
from zoneinfo import ZoneInfo

# ========== التوكن والمعرفات الأساسية ==========
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = 729970974

# ========== إعدادات التحذيرات ==========
MAX_WARNINGS = 3

# ========== المنطقة الزمنية ==========
TIMEZONE = ZoneInfo("Asia/Riyadh")

# نظام الرتب
STAFF_ROLES = {
    "مطور": 5,
    "مدير": 4,
    "مشرف أول": 3,
    "مشرف": 2,
    "مساعد": 1,
    "عضو": 0
}
ROLE_NAMES = {v: k for k, v in STAFF_ROLES.items()}  # عكس القاموس