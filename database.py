import aiosqlite
import os
from datetime import datetime, date

DB_PATH = "kinobot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Foydalanuvchilar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                joined_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Kinolar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                thumbnail_file_id TEXT,
                added_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Majburiy kanallar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL,
                channel_name TEXT NOT NULL,
                channel_link TEXT NOT NULL
            )
        """)

        # Statistika jadvali (kino ko'rishlar)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movie_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_code TEXT NOT NULL,
                movie_title TEXT NOT NULL,
                viewed_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Kunlik foydalanuvchilar (faol)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                visit_date TEXT NOT NULL,
                UNIQUE(user_id, visit_date)
            )
        """)

        await db.commit()


# ==================== USERS ====================

async def add_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
        """, (user_id, username, full_name))
        await db.commit()


async def update_daily_visit(user_id: int):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO daily_users (user_id, visit_date)
            VALUES (?, ?)
        """, (user_id, today))
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, username, full_name, joined_at FROM users ORDER BY joined_at DESC") as cursor:
            return await cursor.fetchall()


async def get_users_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_today_users_count():
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM daily_users WHERE visit_date = ?", (today,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


# ==================== MOVIES ====================

async def add_movie(code: str, title: str, description: str, file_id: str, file_type: str, thumbnail_file_id: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO movies (code, title, description, file_id, file_type, thumbnail_file_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (code, title, description, file_id, file_type, thumbnail_file_id))
        await db.commit()


async def get_movie_by_code(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT code, title, description, file_id, file_type, thumbnail_file_id FROM movies WHERE code = ?", (code,)
        ) as cursor:
            return await cursor.fetchone()


async def delete_movie(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM movies WHERE code = ?", (code,))
        await db.commit()


async def get_all_movies():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT code, title, description, file_id, file_type, added_at FROM movies ORDER BY added_at DESC") as cursor:
            return await cursor.fetchall()


async def get_movies_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM movies") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def movie_exists(code: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM movies WHERE code = ?", (code,)) as cursor:
            return await cursor.fetchone() is not None


# ==================== CHANNELS ====================

async def add_channel(channel_id: str, channel_name: str, channel_link: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO channels (channel_id, channel_name, channel_link)
            VALUES (?, ?, ?)
        """, (channel_id, channel_name, channel_link))
        await db.commit()


async def remove_channel(channel_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        await db.commit()


async def get_all_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channel_id, channel_name, channel_link FROM channels") as cursor:
            return await cursor.fetchall()


# ==================== STATISTICS ====================

async def log_movie_view(user_id: int, movie_code: str, movie_title: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO movie_views (user_id, movie_code, movie_title)
            VALUES (?, ?, ?)
        """, (user_id, movie_code, movie_title))
        await db.commit()


async def get_today_views_count():
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM movie_views WHERE DATE(viewed_at) = ?", (today,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_total_views_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM movie_views") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_today_popular_movies():
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT movie_title, movie_code, COUNT(*) as views
            FROM movie_views
            WHERE DATE(viewed_at) = ?
            GROUP BY movie_code
            ORDER BY views DESC
            LIMIT 10
        """, (today,)) as cursor:
            return await cursor.fetchall()


async def get_all_popular_movies():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT movie_title, movie_code, COUNT(*) as views
            FROM movie_views
            GROUP BY movie_code
            ORDER BY views DESC
            LIMIT 10
        """) as cursor:
            return await cursor.fetchall()
