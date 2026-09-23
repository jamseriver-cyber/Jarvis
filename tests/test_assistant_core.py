"""Small, side-effect-free checks for the assistant's public behavior."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from core.assistant_tools import AssistantTools
from core.memory_store import MemoryStore
from scripts.install_kws_model import verify_archive


CHINA_TIME = timezone(timedelta(hours=8))


class MemoryStoreTests(unittest.TestCase):
    def test_reminder_survives_store_reopen_and_fires_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            due = datetime(2026, 9, 24, 17, 0, tzinfo=CHINA_TIME)
            reminder_id = MemoryStore(root).create_reminder(due, "开会")

            reopened = MemoryStore(root)
            self.assertEqual(reopened.pending_reminders()[0]["id"], reminder_id)
            self.assertEqual(len(reopened.due_reminders(due)), 1)
            reopened.mark_reminder_fired(reminder_id)
            self.assertEqual(reopened.due_reminders(due), [])

    def test_cancel_reminder_does_not_remove_other_reminders(self):
        with tempfile.TemporaryDirectory() as temporary:
            memory = MemoryStore(Path(temporary))
            due = datetime(2026, 9, 24, 17, 0, tzinfo=CHINA_TIME)
            memory.create_reminder(due, "开会")
            memory.create_reminder(due + timedelta(hours=1), "喝水")

            cancelled = memory.cancel_reminder("开会")
            self.assertEqual(cancelled["message"], "开会")
            self.assertEqual([item["message"] for item in memory.pending_reminders()], ["喝水"])

    def test_duplicate_activity_is_not_saved_twice(self):
        with tempfile.TemporaryDirectory() as temporary:
            memory = MemoryStore(Path(temporary))
            memory.record_activity("Browser", "Project page")
            memory.record_activity("Browser", "Project page")
            self.assertEqual(len(memory.recent_activity()), 1)


class AssistantToolsTests(unittest.TestCase):
    def test_chinese_reminder_time(self):
        now = datetime(2026, 9, 23, 15, 0, tzinfo=CHINA_TIME)
        due, message = AssistantTools.parse_reminder("下午五点提醒我开会", now)
        self.assertEqual(due, datetime(2026, 9, 23, 17, 0, tzinfo=CHINA_TIME))
        self.assertEqual(message, "开会")

    def test_relative_reminder_time(self):
        now = datetime(2026, 9, 23, 15, 0, tzinfo=CHINA_TIME)
        due, message = AssistantTools.parse_reminder("十分钟后提醒我喝水", now)
        self.assertEqual(due, now + timedelta(minutes=10))
        self.assertEqual(message, "喝水")

    def test_unsafe_url_and_unknown_tool_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(AssistantTools, "_discover_shortcuts", return_value=[]):
                tools = AssistantTools(Path(temporary), MemoryStore(Path(temporary)))
            self.assertFalse(tools.open_browser("file:///C:/secret.txt").success)
            self.assertFalse(tools.execute("run_shell", {"command": "whoami"}).success)
            self.assertEqual(tools.direct_route("打开日历"), ("open_calendar", {}))

    def test_hide_command_only_targets_jarvis_hud(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(AssistantTools, "_discover_shortcuts", return_value=[]):
                tools = AssistantTools(Path(temporary), MemoryStore(Path(temporary)))
            for command in ("关闭", "贾维斯，隐藏界面", "收起 Jarvis"):
                with self.subTest(command=command):
                    self.assertEqual(tools.direct_route(command), ("hide_hud", {}))
            self.assertEqual(
                tools.direct_route("关闭 VS Code"), None,
                "closing another app must not hide Jarvis by mistake",
            )
            self.assertTrue(tools.execute("hide_hud", {}).success)


class ModelInstallerTests(unittest.TestCase):
    def test_modified_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "model.tar.bz2"
            archive.write_bytes(b"not the official model")
            with self.assertRaises(ValueError):
                verify_archive(archive)


if __name__ == "__main__":
    unittest.main()
