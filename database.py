import aiosqlite
import os

DB_PATH = "bot_data.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                free_downloads INTEGER DEFAULT 1,
                is_whitelisted BOOLEAN DEFAULT FALSE
            )
        """)
        await db.commit()

async def get_user(user_id: int, username: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            
        if not user:
            # Check whitelist
            is_whitelisted = username in ["exsslx", "polya_poela"]
            await db.execute(
                "INSERT INTO users (user_id, username, is_whitelisted) VALUES (?, ?, ?)",
                (user_id, username, is_whitelisted)
            )
            await db.commit()
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
        
        return user

async def add_free_downloads_by_username(username: str, count: int):
    # Remove @ if present
    username = username.lstrip('@')
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET free_downloads = free_downloads + ? WHERE username = ?",
            (count, username)
        )
        await db.commit()
