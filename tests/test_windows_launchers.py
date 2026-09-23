"""Guard the Windows launchers against line endings that cmd.exe misreads."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class WindowsLauncherTests(unittest.TestCase):
    def test_batch_files_use_windows_line_endings(self):
        for name in ("Start Jarvis.bat", "Setup Jarvis.bat"):
            with self.subTest(name=name):
                content = (ROOT / name).read_bytes()
                self.assertIn(b"\r\n", content)
                self.assertNotIn(b"\n", content.replace(b"\r\n", b""))


if __name__ == "__main__":
    unittest.main()
