"""Small, thread-safe SQLite memory for Personal Jarvis."""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


class MemoryStore:
    def __init__(self, root: Path):
        self.data_dir = Path(root) / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "jarvis_memory.db"
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=8.0)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=5000")
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_conversations_created
                    ON conversations(created_at DESC);

                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    tool_name TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    success INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_actions_created
                    ON actions(created_at DESC);

                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    app_name TEXT NOT NULL,
                    window_title TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_activities_created
                    ON activities(created_at DESC);

                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    due_at REAL NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                );
                CREATE INDEX IF NOT EXISTS idx_reminders_due
                    ON reminders(status, due_at);
                """
            )

    def record_conversation(self, role: str, content: str):
        content = (content or "").strip()
        if not content:
            return
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO conversations(created_at, role, content) VALUES (?, ?, ?)",
                (time.time(), role, content[:8000]),
            )

    def recent_conversation(self, limit: int = 8):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content FROM conversations
                WHERE created_at >= ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (time.time() - 30 * 86400, max(1, limit)),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def record_action(self, tool_name: str, summary: str, success: bool):
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO actions(created_at, tool_name, summary, success)
                VALUES (?, ?, ?, ?)
                """,
                (time.time(), tool_name, summary[:1000], int(success)),
            )

    def record_activity(self, app_name: str, window_title: str):
        app_name = (app_name or "unknown").strip()[:160]
        window_title = (window_title or "").strip()[:500]
        if not window_title:
            return

        now = time.time()
        with self._connect() as connection:
            previous = connection.execute(
                """
                SELECT app_name, window_title, created_at FROM activities
                ORDER BY created_at DESC LIMIT 1
                """
            ).fetchone()
            if (
                previous
                and previous["app_name"] == app_name
                and previous["window_title"] == window_title
                and now - previous["created_at"] < 180
            ):
                return
            connection.execute(
                """
                INSERT INTO activities(created_at, app_name, window_title)
                VALUES (?, ?, ?)
                """,
                (now, app_name, window_title),
            )
            connection.execute(
                "DELETE FROM activities WHERE created_at < ?",
                (now - 14 * 86400,),
            )

    def recent_activity(self, limit: int = 8):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT created_at, app_name, window_title FROM activities
                ORDER BY created_at DESC LIMIT ?
                """,
                (max(limit * 3, limit),),
            ).fetchall()

        result = []
        seen = set()
        for row in rows:
            key = (row["app_name"].lower(), row["window_title"].lower())
            if key in seen:
                continue
            seen.add(key)
            result.append(dict(row))
            if len(result) >= limit:
                break
        return result

    def activity_summary(self, limit: int = 6):
        rows = self.recent_activity(limit)
        if not rows:
            return "暂时还没有记录到最近使用的窗口。"

        parts = []
        for row in rows:
            stamp = datetime.fromtimestamp(row["created_at"]).strftime("%H:%M")
            title = row["window_title"].replace("\n", " ")[:90]
            parts.append(f"{stamp} 使用 {row['app_name']}：{title}")
        return "；".join(parts)

    def create_reminder(self, due_at: datetime, message: str):
        message = message.strip()[:500]
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO reminders(created_at, due_at, message, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (time.time(), due_at.timestamp(), message),
            )
            return int(cursor.lastrowid)

    def due_reminders(self, now: datetime | None = None):
        timestamp = (now or datetime.now().astimezone()).timestamp()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, due_at, message FROM reminders
                WHERE status = 'pending' AND due_at <= ?
                ORDER BY due_at ASC
                """,
                (timestamp,),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_reminder_fired(self, reminder_id: int):
        with self._connect() as connection:
            connection.execute(
                "UPDATE reminders SET status = 'fired' WHERE id = ?",
                (reminder_id,),
            )

    def pending_reminders(self, limit: int = 10):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, due_at, message FROM reminders
                WHERE status = 'pending'
                ORDER BY due_at ASC LIMIT ?
                """,
                (max(1, limit),),
            ).fetchall()
        return [dict(row) for row in rows]

    def cancel_reminder(self, keyword: str | None = None):
        keyword = (keyword or "").strip()
        with self._connect() as connection:
            if keyword:
                row = connection.execute(
                    """
                    SELECT id, message FROM reminders
                    WHERE status = 'pending' AND message LIKE ?
                    ORDER BY due_at ASC LIMIT 1
                    """,
                    (f"%{keyword}%",),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT id, message FROM reminders
                    WHERE status = 'pending'
                    ORDER BY due_at ASC LIMIT 1
                    """
                ).fetchone()

            if not row:
                return None
            connection.execute(
                "UPDATE reminders SET status = 'cancelled' WHERE id = ?",
                (row["id"],),
            )
            return dict(row)

    def context_snapshot(self):
        sections = []
        activities = self.activity_summary(4)
        if activities:
            sections.append("最近电脑活动：" + activities)

        reminders = self.pending_reminders(4)
        if reminders:
            rendered = [
                datetime.fromtimestamp(item["due_at"]).strftime("%m-%d %H:%M")
                + " "
                + item["message"]
                for item in reminders
            ]
            sections.append("待办提醒：" + "；".join(rendered))

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT tool_name, summary FROM actions
                WHERE success = 1 ORDER BY created_at DESC LIMIT 4
                """
            ).fetchall()
        if rows:
            sections.append("最近执行：" + "；".join(row["summary"] for row in rows))

        return "\n".join(sections)[:3000]
