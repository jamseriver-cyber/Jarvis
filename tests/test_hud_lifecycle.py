"""The HUD must not occupy the desktop while Jarvis listens in the background."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from main import JarvisBridge


ROOT = Path(__file__).resolve().parent.parent


class HudLifecycleTests(unittest.TestCase):
    def test_hidden_listening_wake_and_app_handoff(self):
        app = QApplication.instance() or QApplication([])
        app.setQuitOnLastWindowClosed(False)
        bridge = JarvisBridge()
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("jarvisBridge", bridge)
        engine.rootContext().setContextProperty("jarvisPreview", False)
        engine.load(ROOT / "ui" / "Main.qml")
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]

        self.assertFalse(window.property("visible"), "Jarvis should start hidden")

        bridge.toggleHud.emit()
        QTest.qWait(380)
        self.assertTrue(window.property("visible"), "F8 should show the HUD")

        bridge.toggleHud.emit()
        QTest.qWait(380)
        self.assertFalse(window.property("visible"), "F8 should hide the window")

        bridge.wakeDetected.emit("贾维斯")
        QTest.qWait(380)
        self.assertTrue(window.property("visible"), "wake should show the HUD")

        bridge.toolStarted.emit("open_application", '{"name":"vs code"}')
        QTest.qWait(380)
        self.assertFalse(window.property("visible"), "the HUD should hide before app launch")
        bridge.toolFinished.emit("open_application", True, "已打开 Visual Studio Code")
        QTest.qWait(50)
        self.assertFalse(window.property("visible"), "successful launch should keep it hidden")

        bridge.toolFinished.emit("open_application", False, "找不到应用")
        QTest.qWait(380)
        self.assertTrue(window.property("visible"), "launch errors should remain visible")
        bridge.hideHudRequested.emit()
        QTest.qWait(380)
        self.assertFalse(window.property("visible"))

        bridge.showHudRequested.emit()
        QTest.qWait(380)
        self.assertTrue(window.property("visible"), "tray Show should work")
        bridge.toolFinished.emit("hide_hud", True, "界面已收起")
        QTest.qWait(380)
        self.assertFalse(window.property("visible"), "voice Hide should keep the app running")

        bridge.showHudRequested.emit()
        QTest.qWait(380)
        self.assertTrue(window.property("visible"), "the HUD can return after voice Hide")
        bridge.hideHudRequested.emit()
        QTest.qWait(380)
        self.assertFalse(window.property("visible"), "tray Hide should work")


if __name__ == "__main__":
    unittest.main()
