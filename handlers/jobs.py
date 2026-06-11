
# ========== التقرير الأسبوعي التلقائي ==========
async def job_weekly_report(context: ContextTypes.DEFAULT_TYPE):
    """إرسال تقرير أسبوعي لجميع المجموعات النشطة كل جمعة"""
    chats = await db.get_all_active_chats()
    week_start = (dt.now(TIMEZONE) - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    week_end = dt.now(TIMEZONE).strftime("%Y-%m-%d")

    for chat_id in chats:
        try:
            # ===== جمع البيانات =====
            top_members = await db.get_top_members(chat_id, limit=10)
            total_msgs = sum(m["message_count"] for m in top_members) if top_members else 0
            active_count = len(top_members)

            # أحداث الأسبوع
            events = await db.get_event_log(chat_id, 50)
            warns = sum(1 for e in events if e.get("action") == "warn")
            bans = sum(1 for e in events if e.get("action") == "ban")
            mutes = sum(1 for e in events if e.get("action") == "mute")

            # ===== الرسالة الأولى: التقرير العام =====
            report = (
                f"📊 **التقرير الأسبوعي**\n"
                f"📅 {week_start} — {week_end}\n\n"
                f"**👥 النشاط:**\n"
                f"• إجمالي الرسائل: {total_msgs}\n"
                f"• الأعضاء النشطين: {active_count}\n"
            )

            if top_members:
                report += f"• أكثر عضو نشيط: {top_members[0]['full_name']} ({top_members[0]['message_count']} رسالة) 🏆\n"

            report += (
                f"\n**⚠️ الإدارة:**\n"
                f"• تحذيرات: {warns}\n"
                f"• حظر: {bans}\n"
                f"• كتم: {mutes}\n\n"
                f"_تقرير تلقائي من شفق 🌅_"
            )

            await context.bot.send_message(chat_id, report, parse_mode="Markdown")

            # ===== الرسالة الثانية: ترتيب الأعضاء =====
            if top_members:
                medals = ["🥇", "🥈", "🥉"]
                lines = []
                for i, m in enumerate(top_members):
                    prefix = medals[i] if i < 3 else f"{i+1}."
                    lines.append(f"{prefix} {m['full_name']} — {m['message_count']} رسالة")

                ranking = "🏅 **ترتيب الأعضاء هذا الأسبوع:**\n\n" + "\n".join(lines)
                await context.bot.send_message(chat_id, ranking, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"فشل إرسال التقرير الأسبوعي للمجموعة {chat_id}: {e}")
