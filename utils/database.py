"""
Async SQLite database layer using aiosqlite.
Tracks users, guilds, requests, and audit logs.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import aiosqlite

log = logging.getLogger("MangaBot.DB")


class Database:
    def __init__(self, path: str = "data/manga_bot.db"):
        self.path = path
        self._db: aiosqlite.Connection = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    async def init(self):
        """Create tables if they don't exist."""
        self._db = await aiosqlite.connect(self.path)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._create_tables()
        await self._db.commit()
        log.info(f"Database ready at {self.path}")

    async def close(self):
        if self._db:
            await self._db.close()

    async def _create_tables(self):
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                joined_at   TEXT DEFAULT (datetime('now')),
                is_banned   INTEGER DEFAULT 0,
                is_premium  INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS guilds (
                guild_id    INTEGER PRIMARY KEY,
                guild_name  TEXT,
                joined_at   TEXT DEFAULT (datetime('now')),
                is_active   INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS requests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                guild_id    INTEGER,
                command     TEXT NOT NULL,
                status      TEXT DEFAULT 'success',
                details     TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id    INTEGER,
                action      TEXT NOT NULL,
                target_id   INTEGER,
                details     TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS bot_settings (
                key         TEXT PRIMARY KEY,
                value       TEXT,
                updated_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_requests_user ON requests(user_id);
            CREATE INDEX IF NOT EXISTS idx_requests_cmd  ON requests(command);
            CREATE INDEX IF NOT EXISTS idx_audit_actor   ON audit_logs(actor_id);
        """)

    # ── Users ─────────────────────────────────────────────────────────────────
    async def get_or_create_user(self, user_id: int, username: str) -> Dict:
        async with self._db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()

        if row is None:
            await self._db.execute(
                "INSERT INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username),
            )
            await self._db.commit()
            return {"user_id": user_id, "username": username, "is_banned": 0,
                    "is_premium": 0, "total_requests": 0}

        cols = [d[0] for d in cur.description] if cur.description else [
            "user_id","username","joined_at","is_banned","is_premium","total_requests"
        ]
        return dict(zip(cols, row))

    async def is_banned(self, user_id: int) -> bool:
        async with self._db.execute(
            "SELECT is_banned FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        return bool(row and row[0])

    async def ban_user(self, user_id: int, actor_id: int):
        await self._db.execute(
            "UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,)
        )
        await self._log_audit(actor_id, "ban_user", user_id)
        await self._db.commit()

    async def unban_user(self, user_id: int, actor_id: int):
        await self._db.execute(
            "UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,)
        )
        await self._log_audit(actor_id, "unban_user", user_id)
        await self._db.commit()

    async def set_premium(self, user_id: int, value: bool, actor_id: int):
        await self._db.execute(
            "UPDATE users SET is_premium = ? WHERE user_id = ?", (int(value), user_id)
        )
        await self._log_audit(actor_id, f"set_premium_{value}", user_id)
        await self._db.commit()

    # ── Guilds ────────────────────────────────────────────────────────────────
    async def register_guild(self, guild_id: int, guild_name: str):
        await self._db.execute(
            """INSERT INTO guilds (guild_id, guild_name) VALUES (?, ?)
               ON CONFLICT(guild_id) DO UPDATE SET guild_name=excluded.guild_name, is_active=1""",
            (guild_id, guild_name),
        )
        await self._db.commit()

    # ── Requests ──────────────────────────────────────────────────────────────
    async def log_request(
        self,
        user_id: int,
        command: str,
        guild_id: Optional[int] = None,
        status: str = "success",
        details: str = "",
    ):
        await self._db.execute(
            "INSERT INTO requests (user_id, guild_id, command, status, details) VALUES (?,?,?,?,?)",
            (user_id, guild_id, command, status, details),
        )
        await self._db.execute(
            "UPDATE users SET total_requests = total_requests + 1 WHERE user_id = ?",
            (user_id,),
        )
        await self._db.commit()

    # ── Stats ─────────────────────────────────────────────────────────────────
    async def get_global_stats(self) -> Dict:
        stats = {}
        queries = {
            "total_users":    "SELECT COUNT(*) FROM users",
            "banned_users":   "SELECT COUNT(*) FROM users WHERE is_banned=1",
            "premium_users":  "SELECT COUNT(*) FROM users WHERE is_premium=1",
            "total_requests": "SELECT COUNT(*) FROM requests",
            "total_guilds":   "SELECT COUNT(*) FROM guilds WHERE is_active=1",
            "ocr_requests":   "SELECT COUNT(*) FROM requests WHERE command='manga_ocr'",
            "colorize_reqs":  "SELECT COUNT(*) FROM requests WHERE command='colorize'",
            "translate_reqs": "SELECT COUNT(*) FROM requests WHERE command='translate_file'",
        }
        for key, query in queries.items():
            async with self._db.execute(query) as cur:
                row = await cur.fetchone()
            stats[key] = row[0] if row else 0
        return stats

    async def get_top_users(self, limit: int = 10) -> List[Tuple]:
        async with self._db.execute(
            "SELECT user_id, username, total_requests FROM users ORDER BY total_requests DESC LIMIT ?",
            (limit,),
        ) as cur:
            return await cur.fetchall()

    async def get_recent_requests(self, limit: int = 20) -> List[Tuple]:
        async with self._db.execute(
            """SELECT r.user_id, u.username, r.command, r.status, r.created_at
               FROM requests r LEFT JOIN users u ON r.user_id=u.user_id
               ORDER BY r.created_at DESC LIMIT ?""",
            (limit,),
        ) as cur:
            return await cur.fetchall()

    # ── Audit ─────────────────────────────────────────────────────────────────
    async def _log_audit(self, actor_id: int, action: str, target_id: int = None, details: str = ""):
        await self._db.execute(
            "INSERT INTO audit_logs (actor_id, action, target_id, details) VALUES (?,?,?,?)",
            (actor_id, action, target_id, details),
        )

    async def get_audit_logs(self, limit: int = 20) -> List[Tuple]:
        async with self._db.execute(
            "SELECT actor_id, action, target_id, details, created_at FROM audit_logs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cur:
            return await cur.fetchall()

    # ── Settings ──────────────────────────────────────────────────────────────
    async def get_setting(self, key: str, default: str = "") -> str:
        async with self._db.execute(
            "SELECT value FROM bot_settings WHERE key=?", (key,)
        ) as cur:
            row = await cur.fetchone()
        return row[0] if row else default

    async def set_setting(self, key: str, value: str):
        await self._db.execute(
            """INSERT INTO bot_settings (key, value) VALUES (?,?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')""",
            (key, value),
        )
        await self._db.commit()
