import logging
import random
import datetime
import pytz
from datetime import datetime as dt
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from quotes import DAILY_QUOTES
from config import TIMEZONE

logger = logging.getLogger(__name__)

# ========== دالة الاقتباس اليومي ==========
async def job_daily_quote(context: ContextTypes.DEFAULT_TYPE):
    """إرسال اقتباس يومي لجميع المجموعات النشطة"""
    quote = random.choice(DAILY_QUOTES)
    chats = await db.get_all_active_chats()
    for chat_id in chats:
        try:
            await context.bot.send_message(chat_id, f"💬 **اقتباس اليوم:**\n\n{quote}", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"فشل إرسال الاقتباس للمجموعة {chat_id}: {e}")

# ========== دالة التقرير البسيط ==========
async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال تقرير بسيط للمشرفين (سري - يتم حذف رسالة المستخدم)"""
    user = update.effective_user
    chat = update.effective_chat
    msg = update.message
    if not msg:
        return
    
    report_text = msg.text.replace("/report", "").replace("تقرير", "").strip() if msg.text else ""
    if not report_text:
        # إرسال رسالة خطأ في الخاص (بدون ظهور في المجموعة)
        try:
            await context.bot.send_message(
                user.id,
                "❌ اكتب سبب التقرير بعد الأمر.\nمثال: تقرير شخص يخالف القواعد"
            )
        except:
            pass
        # حذف رسالة المستخدم الخاطئة
        try:
            await msg.delete()
        except:
            pass
        return
    
    # الرد على رسالة العضو
    if not msg.reply_to_message:
        try:
            await context.bot.send_message(
                user.id,
                "❌ قم بالرد على رسالة العضو المخالف ثم اكتب التقرير."
            )
        except:
            pass
        try:
            await msg.delete()
        except:
            pass
        return
    
    target = msg.reply_to_message.from_user
    
    # حذف رسالة المستخدم (للسرية)
    try:
        await msg.delete()
    except Exception as e:
        logger.error(f"فشل حذف رسالة التقرير: {e}")
    
    reporter_name = user.full_name or user.first_name
    target_name = target.full_name or target.first_name
    
    report_msg = (
        f"📢 **تقرير جديد**\n\n"
        f"👤 مقدم التقرير: {reporter_name}\n"
        f"🚨 العضو المبلغ عنه: {target_name} (`{target.id}`)\n"
        f"📋 السبب: {report_text}\n"
        f"🕒 الوقت: {dt.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    admins = await context.bot.get_chat_administrators(chat.id)
    sent = 0
    for admin in admins:
        if not admin.user.is_bot:
            try:
                await context.bot.send_message(admin.user.id, report_msg, parse_mode="Markdown")
                sent += 1
            except:
                pass
    
    # إرسال تأكيد في الخاص فقط (بدون رسالة في المجموعة)
    if sent > 0:
        try:
            await context.bot.send_message(
                user.id,
                f"✅ تم إرسال تقريرك إلى {sent} من المشرفين (بشكل سري)."
            )
        except:
            pass
    else:
        try:
            await context.bot.send_message(
                user.id,
                "❌ لم يتم إرسال التقرير لأي مشرف (تأكد من صلاحيات البوت)."
            )
        except:
            pass
    
    # تسجيل في سجل الأحداث
    await db.log_event(chat.id, "report", user_id=user.id, target_id=target.id, detail=report_text[:100])

# ========== دالة انتهاء صلاحية الحظر ==========
async def job_expire_bans(context: ContextTypes.DEFAULT_TYPE):
    """فحص الحظر المؤقت وانتهاء صلاحيته"""
    expired = await db.get_expired_bans()
    for ban in expired:
        user_id = ban["user_id"]
        chat_id = ban["chat_id"]
        try:
            await context.bot.unban_chat_member(chat_id, user_id)
            await db.remove_ban(user_id, chat_id)
            logger.info(f"تم رفع الحظر عن {user_id} في مجموعة {chat_id}")
        except Exception as e:
            logger.error(f"فشل رفع الحظر: {e}")

# ========== تقرير متقدم (عميق) ==========
async def cmd_deep_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تقرير متقدم عن عضو مع عرض معلوماته التفصيلية (سري - يتم حذف رسالة المستخدم)"""
    msg = update.message
    user = update.effective_user
    chat = update.effective_chat
    
    # التأكد من وجود رد على رسالة عضو
    if not msg.reply_to_message:
        try:
            await context.bot.send_message(
                user.id,
                "❌ قم بالرد على رسالة العضو الذي تريد الإبلاغ عنه ثم اكتب: تقرير متقدم السبب"
            )
        except:
            pass
        try:
            await msg.delete()
        except:
            pass
        return
    
    target = msg.reply_to_message.from_user
    if target.is_bot:
        try:
            await context.bot.send_message(
                user.id,
                "❌ لا يمكن الإبلاغ عن بوت."
            )
        except:
            pass
        try:
            await msg.delete()
        except:
            pass
        return
    
    # سبب التقرير
    reason = " ".join(context.args) if context.args else "لم يحدد سبب"
    
    # حذف رسالة المستخدم (للسرية)
    try:
        await msg.delete()
    except Exception as e:
        logger.error(f"فشل حذف رسالة التقرير المتقدم: {e}")
    
    # ========== جلب المعلومات ==========
    
    # 1. التحذيرات
    warnings_count = await db.get_warnings(target.id, chat.id)
    
    # 2. الحظر السابق
    old_ban = await db.get_ban(target.id, chat.id)
    was_banned = "✅ نعم" if old_ban else "❌ لا"
    
    # 3. أول ظهور
    first_seen = await db.get_user_first_seen(target.id, chat.id)
    first_seen_str = first_seen[:10] if first_seen else "غير معروف"
    
    # 4. عدد الرسائل
    msg_count = await db.get_message_count(target.id, chat.id)
    
    # 5. حالة الكتم الحالية
    is_muted = "❌ لا"
    try:
        member = await context.bot.get_chat_member(chat.id, target.id)
        if member.status == 'restricted' and not member.can_send_messages:
            is_muted = "✅ نعم"
    except:
        pass
    
    # 6. معرفة إذا كان مشرفاً
    is_admin_user = "❌ لا"
    try:
        member = await context.bot.get_chat_member(chat.id, target.id)
        if member.status == 'creator':
            is_admin_user = "👑 المالك"
        elif member.status == 'administrator':
            is_admin_user = "👮 مشرف"
    except:
        pass
    
    # 7. آخر المخالفات
    violations = await db.get_user_violations(target.id, chat.id, limit=5)
    violations_text = ""
    if violations:
        violations_lines = []
        v_type_map = {
            "banned_word": "🚫 كلمة محظورة",
            "link": "🔗 رابط",
            "tag": "📌 تاك",
            "longtext": "📝 نص طويل",
            "persian": "🇮🇷 كتابة فارسية",
            "media": "🖼️ صورة",
            "video": "🎥 فيديو",
            "audio": "🎵 صوت",
            "file": "📁 ملف",
            "sticker": "🏷️ ملصق",
            "forward": "↪️ إعادة توجيه",
            "game": "🎮 لعبة"
        }
        for i, v in enumerate(violations, 1):
            v_type = v_type_map.get(v.get("violation_type"), v.get("violation_type"))
            v_time = v.get("created_at", "")[:16] if v.get("created_at") else ""
            v_text = v.get("message_text", "")[:50] if v.get("message_text") else ""
            violations_lines.append(f"{i}. {v_type} - {v_time}\n   {v_text}")
        violations_text = "\n".join(violations_lines)
    else:
        violations_text = "✅ لا توجد مخالفات مسجلة"
    
    # ========== إنشاء التقرير ==========
    
    # معلومات العضو الأساسية
    target_name = target.full_name or target.first_name
    target_username = f"@{target.username}" if target.username else "لا يوجد يوزر"
    
    report_text = (
        f"📊 **تقرير متقدم عن العضو**\n\n"
        f"👤 **المعلومات الأساسية:**\n"
        f"• الاسم: {target_name}\n"
        f"• اليوزر: {target_username}\n"
        f"• المعرف: `{target.id}`\n"
        f"• أول ظهور: {first_seen_str}\n\n"
        
        f"🚨 **المخالفات:**\n"
        f"• التحذيرات: {warnings_count} من 3\n"
        f"• محظور سابقاً: {was_banned}\n"
        f"• مكتوم حالياً: {is_muted}\n"
        f"• الرتبة: {is_admin_user}\n\n"
        
        f"📊 **النشاط:**\n"
        f"• عدد الرسائل: {msg_count} رسالة\n\n"
        
        f"⚠️ **آخر المخالفات (5 الأخيرة):**\n"
        f"{violations_text}\n\n"
        
        f"📝 **سبب التقرير:**\n"
        f"{reason}\n\n"
        
        f"🕒 **وقت التقرير:**\n"
        f"{dt.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        f"📌 **مقدم التقرير:**\n"
        f"{user.full_name or user.first_name} (`{user.id}`)"
    )
    
    # ========== إرسال التقرير للمشرفين ==========
    try:
        admins = await context.bot.get_chat_administrators(chat.id)
        sent_count = 0
        
        for admin in admins:
            if not admin.user.is_bot:
                try:
                    await context.bot.send_message(
                        admin.user.id,
                        report_text,
                        parse_mode="Markdown"
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"فشل إرسال التقرير للمشرف {admin.user.id}: {e}")
        
        # إرسال تأكيد في الخاص فقط (بدون رسالة في المجموعة)
        if sent_count > 0:
            try:
                await context.bot.send_message(
                    user.id,
                    f"✅ تم إرسال التقرير المتقدم إلى {sent_count} من المشرفين (بشكل سري)."
                )
            except:
                pass
        else:
            try:
                await context.bot.send_message(
                    user.id,
                    "❌ لم يتم إرسال التقرير لأي مشرف (تأكد من صلاحيات البوت)."
                )
            except:
                pass
            
    except Exception as e:
        logger.error(f"خطأ في إرسال التقرير المتقدم: {e}")
        try:
            await context.bot.send_message(
                user.id,
                "❌ حدث خطأ أثناء إرسال التقرير."
            )
        except:
            pass
    
    # تسجيل في سجل الأحداث
    await db.log_event(chat.id, "deep_report", user_id=user.id, target_id=target.id, detail=reason[:100])