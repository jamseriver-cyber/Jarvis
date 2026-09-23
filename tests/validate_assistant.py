"""One-off live validation used while upgrading Personal Jarvis."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTimer

from core.assistant_tools import AssistantTools
from core.memory_store import MemoryStore
from main import ActivityTracker


def main():
    root = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix="jarvis-validation-") as temp:
        memory = MemoryStore(Path(temp))
        tools = AssistantTools(root, memory)

        app = QCoreApplication(sys.argv)
        activity = []
        tracker = ActivityTracker()
        tracker.activity.connect(lambda name, title: activity.append((name, title)))
        tracker.start()

        results = {}

        def perform_live_checks():
            today = datetime.now().astimezone().date().isoformat()
            results["application"] = tools.open_application("Visual Studio Code")
            results["calendar"] = tools.open_calendar()
            results["scores"] = tools.premier_league_scores(today, True)
            QTimer.singleShot(7500, app.quit)

        QTimer.singleShot(300, perform_live_checks)
        app.exec()
        tracker.requestInterruption()
        tracker.wait(2000)

        payload = {
            key: {"success": value.success, "message": value.message, "data": value.data}
            for key, value in results.items()
        }
        payload["activity"] = activity
        print(json.dumps(payload, ensure_ascii=False, indent=2))

        assert results["application"].success
        assert results["calendar"].success
        assert results["scores"].success
        assert activity
        print("LIVE_ASSISTANT_VALIDATION=PASS")


if __name__ == "__main__":
    main()
