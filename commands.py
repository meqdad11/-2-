from handlers_user import (
    cmd_reminder, cmd_daily_reminder, cmd_my_reminders, cmd_cancel_daily_reminder,
    cmd_whisper, cmd_get_invite, cmd_surah, cmd_quran_page,
    cmd_speak, cmd_voice_to_text, cmd_kickme,
    cmd_enable_welcome, cmd_disable_welcome, cmd_bio, cmd_owner,
    cmd_create_anon_link, cmd_my_messages,
    cmd_start, cmd_id, cmd_rules, cmd_translate,
)
from handlers_admin import (
    cmd_ban, cmd_unban, cmd_warn, cmd_clearwarn, cmd_warnings,
    cmd_banlist, cmd_baninfo, cmd_checkban, cmd_eventlog,
    cmd_setrules, cmd_mute, cmd_unmute, cmd_lock, cmd_unlock,
    cmd_promote_admin, cmd_demote_admin, cmd_list_admins,
    cmd_demote_all, cmd_purge_bans, cmd_purge_muted,
    cmd_tag_all, cmd_my_rank, cmd_his_rank,
)
from handlers_moderation import (
    cmd_add_word, cmd_remove_word, cmd_list_words,
    cmd_add_reply, cmd_remove_reply, cmd_list_replies,
    cmd_add_command, cmd_remove_command, cmd_list_commands,
)
from handlers_resources import (
    cmd_add_resource, cmd_list_resources, cmd_delete_resource,
)
from handlers_ai import (
    cmd_shafaq, cmd_gemini, cmd_limit, cmd_choose_model,
)
from handlers_dev import (
    cmd_add_dev, cmd_remove_dev, cmd_broadcast, cmd_bot_stats,
)
from handlers_jobs import cmd_report, cmd_deep_report
from music import cmd_download, cmd_sc_search, cmd_yt_search
from handlers_menu import cmd_menu

ARABIC_COMMANDS = {
    # أوامر المستخدمين
    "تذكر": cmd_reminder,
    "تذكير": cmd_reminder,
    "تذكير يومي": cmd_daily_reminder,
    "تذكيراتي": cmd_my_reminders,
    "إلغاء تذكير يومي": cmd_cancel_daily_reminder,
    "ايدي": cmd_id,
    "معرفي": cmd_id,
    "القوانين": cmd_rules,
    "قوانين": cmd_rules,
    "بايو": cmd_bio,
    "البايو": cmd_bio,
    "المطور": cmd_owner,
    "انطقي": cmd_speak,
    "كتم صوت": cmd_voice_to_text,
    "صوت لنص": cmd_voice_to_text,
    "طردني": cmd_kickme,
    "همسة": cmd_whisper,
    "اهمس": cmd_whisper,
    "رابط المجموعة": cmd_get_invite,
    "رابط دعوة": cmd_get_invite,
    "تفعيل الترحيب": cmd_enable_welcome,
    "تعطيل الترحيب": cmd_disable_welcome,
    "سورة": cmd_surah,
    "قران": cmd_quran_page,
    "صارحني": cmd_create_anon_link,
    "رسائلي": cmd_my_messages,
    "ترجمة": cmd_translate,

    # أوامر المشرفين
    "حظر": cmd_ban,
    "فك الحظر": cmd_unban,
    "تحذير": cmd_warn,
    "مسح التحذيرات": cmd_clearwarn,
    "التحذيرات": cmd_warnings,
    "قائمة الحظر": cmd_banlist,
    "معلومات الحظر": cmd_baninfo,
    "فحص الحظر": cmd_checkban,
    "سجل الاحداث": cmd_eventlog,
    "تعيين القوانين": cmd_setrules,
    "كتم": cmd_mute,
    "فك الكتم": cmd_unmute,
    "قفل": cmd_lock,
    "فتح": cmd_unlock,
    "تقرير": cmd_report,
    "تقرير متقدم": cmd_deep_report,
    "رفع مشرف": cmd_promote_admin,
    "تنزيل مشرف": cmd_demote_admin,
    "قائمة المشرفين": cmd_list_admins,
    "تنزيل الكل": cmd_demote_all,
    "مسح المحظورين": cmd_purge_bans,
    "مسح المكتومين": cmd_purge_muted,
    "منشن الكل": cmd_tag_all,
    "رتبتي": cmd_my_rank,
    "رتبته": cmd_his_rank,
    "اضافة كلمة": cmd_add_word,
    "حذف كلمة": cmd_remove_word,
    "قائمة الكلمات": cmd_list_words,
    "اضافة رد": cmd_add_reply,
    "حذف رد": cmd_remove_reply,
    "قائمة الردود": cmd_list_replies,
    "اضافة اختصار": cmd_add_command,
    "حذف اختصار": cmd_remove_command,
    "قائمة الاختصارات": cmd_list_commands,
    "اضافة مورد": cmd_add_resource,
    "قائمة الموارد": cmd_list_resources,
    "حذف مورد": cmd_delete_resource,

    # الذكاء الاصطناعي
    "شفق": cmd_shafaq,
    "جوجل": cmd_gemini,
    "استعمال": cmd_limit,
    "نموذج": cmd_choose_model,

    # أوامر المطور
    "رفع مطور": cmd_add_dev,
    "تنزيل مطور": cmd_remove_dev,
    "اذاعة": cmd_broadcast,
    "احصائيات البوت": cmd_bot_stats,

    # وسائط
    "تحميل": cmd_download,
    "بحث ساوند": cmd_sc_search,
    "بحث يوتيوب": cmd_yt_search,

    # قائمة
    "القائمة": cmd_menu,
}