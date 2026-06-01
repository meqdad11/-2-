from handlers_admin import (
    cmd_ban,
    cmd_unban,
    cmd_warn,
    cmd_clearwarn,
    cmd_warnings,
    cmd_banlist,
    cmd_baninfo,
    cmd_checkban,
    cmd_eventlog,
    cmd_setrules,
    cmd_mute,
    cmd_unmute,
    cmd_lock,
    cmd_unlock,
)
from handlers_user import (
    cmd_id,
    cmd_rules,
)
from handlers_moderation import (
    cmd_add_word,
    cmd_remove_word,
    cmd_list_words,
)
from handlers_jobs import (
    cmd_report,
)
from handlers_ai import (
    cmd_shafaq,
)
from handlers_resources import (
    cmd_add_resource,
    cmd_list_resources,
    cmd_delete_resource,

from handlers_menu import cmd_menu, callback_menu
)
from music import (
    cmd_sc_search,
    cmd_yt_search,
    cmd_download,
)
from handlers_menu import cmd_menu

# ========== قاموس الأوامر العربية ==========
ARABIC_COMMANDS = {
    # ── إدارة الحظر ──────────────────────────
    "حظر":                  cmd_ban,
    "رفع الحظر":            cmd_unban,
    "رفع_الحظر":            cmd_unban,
    "قائمة":                cmd_banlist,
    "معلومات":              cmd_baninfo,
    "تحقق":                 cmd_checkban,

    # ── التحذيرات ────────────────────────────
    "تحذير":                cmd_warn,
    "مسح التحذير":          cmd_clearwarn,
    "التحذيرات":            cmd_warnings,

    # ── الكتم ────────────────────────────────
    "كتم":                  cmd_mute,
    "رفع الكتم":            cmd_unmute,

    # ── إدارة المجموعة ───────────────────────
    "أغلق المجموعة":        cmd_lock,
    "افتح المجموعة":        cmd_unlock,
    "سجل":                  cmd_eventlog,
    "تقرير":                cmd_report,

    # ── الكلمات المحظورة ─────────────────────
    "أضف كلمة":             cmd_add_word,
    "احذف كلمة":            cmd_remove_word,
    "الكلمات المحظورة":     cmd_list_words,

    # ── الموارد ──────────────────────────────
    "أضف مورد":             cmd_add_resource,
    "الموارد":              cmd_list_resources,
    "احذف مورد":            cmd_delete_resource,

    # ── للجميع ───────────────────────────────
    "ايدي":                 cmd_id,
    "القواعد":              cmd_rules,
    "شفق":                  cmd_shafaq,

    # ── الميديا ──────────────────────────────
    "تحميل":                cmd_download,
    "بحث":                  cmd_sc_search,
    "يوتيوب":               cmd_yt_search,
    "ابدأ":                  cmd_menu,
}
