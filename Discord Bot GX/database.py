import aiosqlite
import logging
from typing import Optional, Dict, Any, List
from config import DATABASE_PATH

logger = logging.getLogger("discord_bot.database")

class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Initialize database tables if they do not exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    welcome_channel_id INTEGER,
                    welcome_message TEXT,
                    log_channel_id INTEGER,
                    autorole_id INTEGER
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    user_id INTEGER,
                    moderator_id INTEGER,
                    reason TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS license_keys (
                    key TEXT PRIMARY KEY,
                    guild_id INTEGER,
                    duration_days INTEGER,
                    created_by INTEGER,
                    used_by INTEGER DEFAULT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    used_at DATETIME DEFAULT NULL
                )
            """)
            await db.commit()
        logger.info("Database initialized successfully.")

    async def get_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        """Fetch settings for a specific guild."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return {
                    "guild_id": guild_id,
                    "welcome_channel_id": None,
                    "welcome_message": None,
                    "log_channel_id": None,
                    "autorole_id": None,
                }

    async def update_guild_setting(self, guild_id: int, key: str, value: Any):
        """Update a specific setting for a guild."""
        allowed_keys = {
            "welcome_channel_id",
            "welcome_message",
            "log_channel_id",
            "autorole_id",
        }
        if key not in allowed_keys:
            raise ValueError(f"Invalid setting key: {key}")

        async with aiosqlite.connect(self.db_path) as db:
            # Ensure guild record exists
            await db.execute(
                "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
            )
            await db.execute(
                f"UPDATE guild_settings SET {key} = ? WHERE guild_id = ?",
                (value, guild_id),
            )
            await db.commit()

    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
        """Add a warning entry for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, moderator_id, reason),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_warnings(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Retrieve warnings for a user in a specific guild."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY timestamp DESC",
                (guild_id, user_id),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        """Clear all warnings for a user in a specific guild."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
            await db.commit()
            return cursor.rowcount

    async def add_license_key(self, guild_id: int, key: str, duration_days: int, created_by: int):
        """Add a generated license key to database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO license_keys (key, guild_id, duration_days, created_by) VALUES (?, ?, ?, ?)",
                (key, guild_id, duration_days, created_by),
            )
            await db.commit()

    async def redeem_license_key(self, guild_id: int, key: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Attempt to redeem a key. Returns key dict if successful, None if invalid or used."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM license_keys WHERE key = ? AND guild_id = ?", (key, guild_id)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                data = dict(row)
                if data["used_by"] is not None:
                    return None # Already used

                await db.execute(
                    "UPDATE license_keys SET used_by = ?, used_at = CURRENT_TIMESTAMP WHERE key = ?",
                    (user_id, key),
                )
                await db.commit()
                return data

    async def get_license_keys(self, guild_id: int) -> List[Dict[str, Any]]:
        """Retrieve all keys generated for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM license_keys WHERE guild_id = ? ORDER BY created_at DESC", (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_key_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve details of a single license key by key string."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM license_keys WHERE LOWER(key) = LOWER(?)", (key.strip(),)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
