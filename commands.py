from handlers_admin import (
    cmd_ban, cmd_unban, cmd_warn, cmd_clearwarn, cmd_warnings,
    cmd_banlist, cmd_baninfo, cmd_checkban, cmd_eventlog,
    cmd_setrules, cmd_mute, cmd_unmute, cmd_lock, cmd_unlock,
)
from handlers_user import cmd_id, cmd_rules
from handlers_moderation import (
    cmd_add_word, cmd_remove_word, cmd_list_words,
    cmd_add_reply, cmd_remove_reply, cmd_list_replies,
    cmd_add_command, cmd_remove_command, cmd_list_commands,
)
from handlers_jobs import cmd_report
from handlers_ai import cmd_shafaq, cmd_gemini, cmd_limit
from handlers_resources import cmd_add_resource, cmd_list_resources, cmd_delete_resource
from handlers_menu import cmd_menu, callback_menu
from music import cmd_sc_search, cmd_yt_search, cmd_download

# دوال القفل
from handlers_locks import (
    cmd_lock_links, cmd_unlock_links,
    cmd_lock_tags, cmd_unlock_tags,
    cmd_lock_media, cmd_unlock_media,
    cmd_lock_files, cmd_unlock_files,
    cmd_lock_video, cmd_unlock_video,
    cmd_lock_voice, cmd_unlock_voice,
    cmd_lock_gifs, cmd_unlock_gifs,
    cmd_lock_edit, cmd_unlock_edit,
    cmd_lock_editmedia, cmd_unlock_editmedia,
    cmd_lock_repeat, cmd_unlock_repeat,
    cmd_lock_join, cmd_unlock_join,
    cmd_lock_forward, cmd_unlock_forward,
    cmd_lock_id, cmd_unlock_id,
    cmd_lock_badwords, cmd_unlock_badwords,
    cmd_lock_spam, cmd_unlock_spam,
    cmd_lock_replies, cmd_unlock_replies,
    cmd_lock_notifications, cmd_unlock_notifications,
    cmd_lock_persian, cmd_unlock_persian,
    cmd_lock_bots, cmd_unlock_bots,
    cmd_lock_iranian, cmd_unlock_iranian,
    cmd_lock_longtext, cmd_unlock_longtext,
    cmd_lock_quran, cmd_unlock_quran,
    cmd_lock_porn, cmd_unlock_porn,
    cmd_lock_ai, cmd_unlock_ai,
    cmd_lock_autoreply, cmd_unlock_autoreply,
    cmd_lock_games, cmd_unlock_games,
    cmd_lock_marketnews, cmd_unlock_marketnews,
    cmd_lock_whisper, cmd_unlock_whisper,
    cmd_lock_all, cmd_unlock_all,
)

# دوال المطور
from handlers_dev import cmd_add_dev, cmd_remove_dev, cmd_broadcast, cmd_bot_stats

# دوال إدارة المشرفين الجديدة
from handlers_admin import (
    cmd_promote_admin, cmd_demote_admin, cmd_list_admins,
    cmd_demote_all, cmd_purge_bans, cmd_purge_muted,
    cmd_tag_all, cmd_my_rank, cmd_his_rank,
)

# دوال المستخدم الجديدة
from handlers_user import (
    cmd_whisper, cmd_get_invite, cmd_surah, cmd_quran_page,
    cmd_speak, cmd_voice_to_text, cmd_kickme,
    cmd_enable_welcome, cmd_disable_welcome, cmd_bio, cmd_owner,
)

ARABIC_COMMANDS = {
    # ──── الأوامر القديمة ────
    "حظر": cmd_ban, "رفع الحظر": cmd_unban, "رفع_الحظر": cmd_unban,
    "قائمة": cmd_banlist, "معلومات": cmd_baninfo, "تحقق": cmd_checkban,
    "تحذير": cmd_warn, "مسح التحذير": cmd_clearwarn, "التحذيرات": cmd_warnings,
    "كتم": cmd_mute, "رفع الكتم": cmd_unmute,
    "أغلق المجموعة": cmd_lock, "افتح المجموعة": cmd_unlock,
    "سجل": cmd_eventlog, "تقرير": cmd_report,
    "أضف كلمة": cmd_add_word, "احذف كلمة": cmd_remove_word, "الكلمات المحظورة": cmd_list_words,
    "أضف مورد": cmd_add_resource, "الموارد": cmd_list_resources, "احذف مورد": cmd_delete_resource,
    "ايدي": cmd_id, "القواعد": cmd_rules, "شفق": cmd_shafaq,
    "تحميل": cmd_download, "بحث": cmd_sc_search, "يوتيوب": cmd_yt_search,
    "ابدا": cmd_menu, "ابدأ": cmd_menu, "أبدا": cmd_menu,

    # ──── أوامر القفل والفتح ────
    "قفل الروابط": cmd_lock_links, "فتح الروابط": cmd_unlock_links,
    "قفل التاك": cmd_lock_tags, "فتح التاك": cmd_unlock_tags,
    "قفل الميديا": cmd_lock_media, "فتح الميديا": cmd_unlock_media,
    "قفل الملفات": cmd_lock_files, "فتح الملفات": cmd_unlock_files,
    "قفل الفيديو": cmd_lock_video, "فتح الفيديو": cmd_unlock_video,
    "قفل الفويسات": cmd_lock_voice, "فتح الفويسات": cmd_unlock_voice,
    "قفل المتحركات": cmd_lock_gifs, "فتح المتحركات": cmd_unlock_gifs,
    "قفل التعديل": cmd_lock_edit, "فتح التعديل": cmd_unlock_edit,
    "قفل تعديل الميديا": cmd_lock_editmedia, "فتح تعديل الميديا": cmd_unlock_editmedia,
    "قفل التكرار": cmd_lock_repeat, "فتح التكرار": cmd_unlock_repeat,
    "قفل الدخول": cmd_lock_join, "فتح الدخول": cmd_unlock_join,
    "قفل التوجيه": cmd_lock_forward, "فتح التوجيه": cmd_unlock_forward,
    "قفل ايدي": cmd_lock_id, "فتح ايدي": cmd_unlock_id,
    "قفل السب": cmd_lock_badwords, "فتح السب": cmd_unlock_badwords,
    "قفل السبام": cmd_lock_spam, "فتح السبام": cmd_unlock_spam,
    "قفل الردود": cmd_lock_replies, "فتح الردود": cmd_unlock_replies,
    "قفل الاشعارات": cmd_lock_notifications, "فتح الاشعارات": cmd_unlock_notifications,
    "قفل الفارسيه": cmd_lock_persian, "فتح الفارسيه": cmd_unlock_persian,
    "قفل البوتات": cmd_lock_bots, "فتح البوتات": cmd_unlock_bots,
    "قفل دخول الايراني": cmd_lock_iranian, "فتح دخول الايراني": cmd_unlock_iranian,
    "قفل الكلام الكثير": cmd_lock_longtext, "فتح الكلام الكثير": cmd_unlock_longtext,
    "قفل القران": cmd_lock_quran, "فتح القران": cmd_unlock_quran,
    "قفل الاباحي": cmd_lock_porn, "فتح الاباحي": cmd_unlock_porn,
    "قفل الذكاء": cmd_lock_ai, "فتح الذكاء": cmd_unlock_ai,
    "قفل الرد التلقائي": cmd_lock_autoreply, "فتح الرد التلقائي": cmd_unlock_autoreply,
    "قفل الالعاب": cmd_lock_games, "فتح الالعاب": cmd_unlock_games,
    "قفل اخبار السوق": cmd_lock_marketnews, "فتح اخبار السوق": cmd_unlock_marketnews,
    "قفل الهمسه": cmd_lock_whisper, "فتح الهمسه": cmd_unlock_whisper,
    "قفل الكل": cmd_lock_all, "فتح الكل": cmd_unlock_all,

    # ──── أوامر المطور ────
    "رفع مطور": cmd_add_dev, "تنزيل مطور": cmd_remove_dev,
    "اذاعه": cmd_broadcast,
    "احصائيات": cmd_bot_stats,   # ✅ تم التصحيح

    # ──── أوامر المشرفين الإضافية ────
    "رفع مشرف": cmd_promote_admin, "تنزيل مشرف": cmd_demote_admin,
    "المشرفين": cmd_list_admins, "تنزيل الكل": cmd_demote_all,
    "مسح المحظورين": cmd_purge_bans, "مسح المكتومين": cmd_purge_muted,
    "تاك للكل": cmd_tag_all, "رتبتي": cmd_my_rank, "رتبته": cmd_his_rank,

    # ──── أوامر المستخدم الإضافية ────
    "اهمس": cmd_whisper, "افتاري": cmd_get_invite,
    "سورة": cmd_surah, "قران": cmd_quran_page,
    "انطقي": cmd_speak, "وش يقول": cmd_voice_to_text,
    "جيمناي": cmd_gemini, "الحد": cmd_limit,
    "اطردني": cmd_kickme,
    "تفعيل الترحيب": cmd_enable_welcome, "تعطيل الترحيب": cmd_disable_welcome,
    "بايـو": cmd_bio, "المالك": cmd_owner,

    # ──── أوامر الردود والاختصارات ────
    "اضف رد": cmd_add_reply, "حذف رد": cmd_remove_reply, "الردود المضافه": cmd_list_replies,
    "اضف امر": cmd_add_command, "حذف امر": cmd_remove_command, "الاوامر المضافه": cmd_list_commands,
}