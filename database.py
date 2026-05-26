# ── NEW FUNCTIONS ADDED FOR REPORTS & GAMES ─────────────────────────────────

async def get_new_bans(chat_id: int, days: int = 7) -> list:
    """Return bans created in the last N days."""
    from datetime import datetime, timezone, timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM banned_users WHERE chat_id=? AND banned_at>? ORDER BY banned_at DESC",
            (chat_id, since),
        )
        return [dict(r) for r in await cursor.fetchall()]

async def get_all_warnings(chat_id: int) -> int:
    """Return total warning count for a chat."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT SUM(count) FROM warnings WHERE chat_id=?",
            (chat_id,),
        )
        row = await cursor.fetchone()
        return row[0] or 0

async def get_message_stats(chat_id: int, days: int = 7) -> int:
    """Return total messages in last N days."""
    from datetime import datetime, timezone, timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT SUM(message_count) FROM user_stats WHERE chat_id=? AND first_seen>?",
            (chat_id, since),
        )
        row = await cursor.fetchone()
        return row[0] or 0

async def get_top_users(chat_id: int, limit: int = 10) -> list:
    """Return top users by message count."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id, message_count FROM user_stats WHERE chat_id=? ORDER BY message_count DESC LIMIT ?",
            (chat_id, limit),
        )
        return await cursor.fetchall()

async def get_bot_events(chat_id: int, days: int = 1) -> list:
    """Return events for daily report."""
    from datetime import datetime, timezone, timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM event_log WHERE chat_id=? AND created_at>? ORDER BY created_at DESC",
            (chat_id, since),
        )
        return [dict(r) for r in await cursor.fetchall()]

async def add_game_score(user_id: int, chat_id: int, game_type: str, score: int):
    """Add or update game score."""
    from datetime import datetime, timezone
    import json
    now = datetime.now(timezone.utc).isoformat()
    key = f"game_score_{user_id}_{game_type}"
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM chat_settings WHERE chat_id=? AND key=?",
            (chat_id, key),
        )
        row = await cursor.fetchone()
        if row:
            data = json.loads(row[0])
            data["score"] += score
            data["count"] += 1
            await db.execute(
                "UPDATE chat_settings SET value=? WHERE chat_id=? AND key=?",
                (json.dumps(data), chat_id, key),
            )
        else:
            data = {"score": score, "count": 1}
            await db.execute(
                "INSERT INTO chat_settings (chat_id, key, value) VALUES (?, ?, ?)",
                (chat_id, key, json.dumps(data)),
            )
        await db.commit()

async def get_game_scores(user_id: int, chat_id: int) -> list:
    """Return game scores for a user."""
    import json
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT key, value FROM chat_settings WHERE chat_id=? AND key LIKE ?",
            (chat_id, f"game_score_{user_id}_%"),
        )
        results = []
        for row in await cursor.fetchall():
            game_type = row[0].split("_")[-1]
            data = json.loads(row[1])
            results.append((game_type, data["score"], data["count"]))
        return results

async def add_chat(chat_id: int):
    """Track a chat for reports."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO chat_settings (chat_id, key, value) VALUES (?, 'tracked', '1')",
            (chat_id,),
        )
        await db.commit()

async def get_all_chats() -> list:
    """Return all tracked chat IDs."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT DISTINCT chat_id FROM chat_settings WHERE key='tracked'"
        )
        return [row[0] for row in await cursor.fetchall()]
