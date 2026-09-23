"""Personal Jarvis desktop HUD and local voice conversation loop."""

from __future__ import annotations

import argparse
import ctypes
import html
import re
import socket
import sys
import time
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

import keyboard
import psutil
import shiboken6
from PySide6.QtCore import QObject, QLocale, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTextToSpeech import QTextToSpeech
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from core.assistant_tools import AssistantTools
from core.memory_store import MemoryStore
from llm.ollama_worker import OllamaWorker
from runtime_paths import resource_root, user_root, wake_model_ready
from voice.stt_listener import SttListener
from voice.wake_listener import WakeListener


class JarvisBridge(QObject):
    toggleHud = Signal()
    showHudRequested = Signal()
    hideHudRequested = Signal()
    wakeDetected = Signal(str, arguments=["keyword"])
    listeningStarted = Signal()
    transcribingStarted = Signal()
    transcriptReady = Signal(str, arguments=["text"])
    noSpeech = Signal()
    startListeningRequested = Signal()

    llmRequested = Signal(str, arguments=["text"])
    llmStarted = Signal()
    llmChunk = Signal(str, arguments=["chunk"])
    llmFinished = Signal(str, arguments=["text"])
    llmError = Signal(str, arguments=["message"])

    ttsStarted = Signal()
    ttsFinished = Signal()
    ttsError = Signal(str, arguments=["message"])

    audioLevelChanged = Signal(float, arguments=["level"])
    systemMetrics = Signal(
        float,
        float,
        float,
        str,
        str,
        arguments=["cpu", "memory", "disk", "network", "uptime"],
    )
    llmStatusChanged = Signal(bool, str, arguments=["online", "model"])
    toolStarted = Signal(str, str, arguments=["tool", "detail"])
    toolFinished = Signal(str, bool, str, arguments=["tool", "success", "message"])
    activityChanged = Signal(str, str, arguments=["app", "title"])
    nextReminderChanged = Signal(str, str, arguments=["time", "message"])
    reminderTriggered = Signal(str, str, arguments=["time", "message"])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._awaiting_ack = False

    def arm_ack(self):
        self._awaiting_ack = True

    @Slot()
    def ackFinished(self):
        if not self._awaiting_ack:
            return
        self._awaiting_ack = False
        self.startListeningRequested.emit()

    @Slot(str)
    def handle_transcript(self, text):
        text = text.strip()
        print(f"[Jarvis] 最终文本: {text}")
        self.transcriptReady.emit(text)
        if text:
            self.llmRequested.emit(text)
        else:
            self.noSpeech.emit()


class SystemMonitor(QThread):
    metrics = Signal(float, float, float, str, str, bool)

    @staticmethod
    def _rate_text(bytes_per_second: float) -> str:
        if bytes_per_second >= 1024 * 1024:
            return f"{bytes_per_second / 1024 / 1024:.1f} MB/s"
        if bytes_per_second >= 1024:
            return f"{bytes_per_second / 1024:.0f} KB/s"
        return f"{bytes_per_second:.0f} B/s"

    @staticmethod
    def _uptime_text() -> str:
        seconds = max(0, int(time.time() - psutil.boot_time()))
        days, remainder = divmod(seconds, 86400)
        hours, minutes = divmod(remainder, 3600)
        minutes //= 60
        return f"{days}D {hours:02d}H {minutes:02d}M"

    @staticmethod
    def _ollama_online() -> bool:
        try:
            with socket.create_connection(("127.0.0.1", 11434), timeout=0.2):
                return True
        except OSError:
            return False

    def run(self):
        previous_net = psutil.net_io_counters()
        previous_time = time.monotonic()
        while not self.isInterruptionRequested():
            cpu = psutil.cpu_percent(interval=0.45)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage(Path.home().anchor).percent
            current_net = psutil.net_io_counters()
            current_time = time.monotonic()
            elapsed = max(0.1, current_time - previous_time)
            down_rate = (current_net.bytes_recv - previous_net.bytes_recv) / elapsed
            previous_net = current_net
            previous_time = current_time

            self.metrics.emit(
                float(cpu),
                float(memory),
                float(disk),
                self._rate_text(max(0.0, down_rate)),
                self._uptime_text(),
                self._ollama_online(),
            )

            for _ in range(6):
                if self.isInterruptionRequested():
                    return
                self.msleep(100)


class ActivityTracker(QThread):
    """Remember foreground Windows activity locally without capturing contents."""

    activity = Signal(str, str)

    def run(self):
        user32 = ctypes.windll.user32
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        last_key = None
        while not self.isInterruptionRequested():
            try:
                window = user32.GetForegroundWindow()
                length = user32.GetWindowTextLengthW(window)
                if window and length:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(window, buffer, length + 1)
                    title = buffer.value.strip()
                    process_id = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(window, ctypes.byref(process_id))
                    try:
                        app_name = psutil.Process(process_id.value).name()
                    except (psutil.Error, OSError):
                        app_name = "Windows"

                    key = (app_name.lower(), title)
                    if (
                        title
                        and key != last_key
                        and "personal jarvis" not in title.lower()
                    ):
                        last_key = key
                        self.activity.emit(app_name, title)
            except Exception as exc:
                print(f"[Memory] 活动跟踪暂时不可用: {exc}")

            for _ in range(50):
                if self.isInterruptionRequested():
                    return
                self.msleep(100)


class JarvisController(QObject):
    def __init__(self, bridge: JarvisBridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.root = user_root()
        self.memory = MemoryStore(self.root)
        self.tools = AssistantTools(self.root, self.memory)
        self.wake_listener = WakeListener()
        self.stt_listener = None
        self.llm_worker = None
        self.monitor = SystemMonitor()
        self.activity_tracker = ActivityTracker()
        self.history = self.memory.recent_conversation(10)
        self._interaction_active = False
        self._current_user_text = ""
        self._tts_active = False
        self._tts_mode = None
        self._speech_queue = []
        self._last_llm_online = None

        self.tts = QTextToSpeech("sapi", self)
        self.tts.setLocale(QLocale("zh_CN"))
        voices = self.tts.availableVoices()
        if voices:
            preferred = next(
                (voice for voice in voices if "Huihui" in voice.name()),
                voices[0],
            )
            self.tts.setVoice(preferred)
        self.tts.setRate(-0.08)
        self.tts.setPitch(-0.12)
        self.tts.setVolume(1.0)
        self.tts.stateChanged.connect(self._on_tts_state_changed)

        self.bridge.startListeningRequested.connect(self.start_stt)
        self.bridge.llmRequested.connect(self.start_llm)
        self.bridge.noSpeech.connect(self._on_no_speech)
        self.wake_listener.wake_detected.connect(self._on_wake)
        self.monitor.metrics.connect(self._on_metrics)
        self.activity_tracker.activity.connect(self._on_activity)

        self.reminder_timer = QTimer(self)
        self.reminder_timer.setInterval(1000)
        self.reminder_timer.timeout.connect(self._check_reminders)

        self.context_timer = QTimer(self)
        self.context_timer.setInterval(30000)
        self.context_timer.timeout.connect(self._refresh_next_reminder)

    def start(self):
        self.monitor.start()
        self.activity_tracker.start()
        if wake_model_ready():
            self.wake_listener.start()
        else:
            print("[Jarvis] 唤醒模型尚未安装；可按 F9 对话，或运行首次设置。")
        self.reminder_timer.start()
        self.context_timer.start()
        self._refresh_next_reminder()
        recent = self.memory.recent_activity(1)
        if recent:
            self.bridge.activityChanged.emit(
                recent[0]["app_name"], recent[0]["window_title"]
            )
        keyboard.add_hotkey("f8", self.bridge.toggleHud.emit, suppress=False)
        keyboard.add_hotkey("f9", self._manual_activate, suppress=False)
        print(
            "[Jarvis] AI 助理已启动。说“贾维斯”或按 F9 开始，"
            "F8 显示/隐藏 HUD；最小化后仍会聆听并触发提醒。"
        )

    @Slot(str)
    def _on_wake(self, keyword):
        self._activate(keyword)

    def _manual_activate(self):
        self._activate("PUSH TO TALK")

    def _activate(self, keyword):
        if self._interaction_active:
            print("[Jarvis] 当前对话尚未结束，忽略重复激活。")
            return

        print(f"[Jarvis] 收到激活信号: {keyword}")
        self._interaction_active = True
        self.wake_listener.pause()
        self.bridge.arm_ack()
        self.bridge.wakeDetected.emit(keyword)

    @Slot()
    def start_stt(self):
        if not self._interaction_active:
            return
        if self.stt_listener is not None and self.stt_listener.isRunning():
            return

        print("[Jarvis] 启动语音识别")
        self.stt_listener = SttListener()
        self.stt_listener.listening_started.connect(self.bridge.listeningStarted.emit)
        self.stt_listener.transcribing_started.connect(
            self.bridge.transcribingStarted.emit
        )
        self.stt_listener.audio_level.connect(self.bridge.audioLevelChanged.emit)
        self.stt_listener.text_ready.connect(self.bridge.handle_transcript)
        self.stt_listener.no_speech.connect(self.bridge.noSpeech.emit)
        self.stt_listener.error_occurred.connect(self._on_stt_error)
        self.stt_listener.start()

    @Slot()
    def _on_no_speech(self):
        print("[Jarvis] 未检测到有效语音")
        self._finish_interaction(delay_ms=900)

    @Slot(str)
    def _on_stt_error(self, message):
        print(f"[Jarvis] 语音识别失败: {message}")
        self.bridge.llmError.emit(f"语音输入失败：{message}")
        self._finish_interaction(delay_ms=1200)

    @Slot(str)
    def start_llm(self, text):
        if self.llm_worker is not None and self.llm_worker.isRunning():
            return

        self._current_user_text = text
        self.bridge.llmStarted.emit()
        self.llm_worker = OllamaWorker(
            text,
            self.history,
            self.tools,
            self.memory.context_snapshot(),
        )
        self.llm_worker.chunk_ready.connect(self.bridge.llmChunk.emit)
        self.llm_worker.finished_text.connect(self._on_llm_finished)
        self.llm_worker.error_occurred.connect(self._on_llm_error)
        self.llm_worker.tool_started.connect(self._on_tool_started)
        self.llm_worker.tool_finished.connect(self._on_tool_finished)
        self.llm_worker.server_ready.connect(
            lambda model: self.bridge.llmStatusChanged.emit(True, model)
        )
        self.llm_worker.start()

    @Slot(str)
    def _on_llm_finished(self, text):
        self.history.extend(
            [
                {"role": "user", "content": self._current_user_text},
                {"role": "assistant", "content": text},
            ]
        )
        self.history = self.history[-8:]
        self.memory.record_conversation("user", self._current_user_text)
        self.memory.record_conversation("assistant", text)
        self.bridge.llmFinished.emit(text)
        self._speak_reply(text)

    @Slot(str, str)
    def _on_tool_started(self, tool_name, detail):
        print(f"[Tool] 执行 {tool_name}: {detail}")
        self.bridge.toolStarted.emit(tool_name, detail)

    @Slot(str, bool, str)
    def _on_tool_finished(self, tool_name, success, message):
        print(f"[Tool] {tool_name}: {'成功' if success else '失败'} - {message}")
        self.bridge.toolFinished.emit(tool_name, success, message)
        if tool_name in {"create_reminder", "cancel_reminder", "list_reminders"}:
            self._refresh_next_reminder()

    @Slot(str)
    def _on_llm_error(self, message):
        self.bridge.llmStatusChanged.emit(False, "qwen3.5:0.8b")
        self.bridge.llmError.emit(message)
        self._finish_interaction(delay_ms=1500)

    @staticmethod
    def _speech_text(text: str) -> str:
        result = html.unescape(text)
        result = re.sub(r"```.*?```", "代码内容已显示在屏幕上。", result, flags=re.S)
        result = re.sub(r"https?://\S+", "链接", result)
        result = re.sub(r"[*_#>`~|]", "", result)
        result = re.sub(r"\s+", " ", result)
        return result.strip()

    def _speak_reply(self, text):
        spoken = self._speech_text(text)
        if not spoken or self.tts.state() == QTextToSpeech.State.Error:
            self.bridge.ttsError.emit("本地语音引擎不可用。")
            self._finish_interaction(delay_ms=900)
            return
        self._enqueue_speech(spoken, "reply")

    def _enqueue_speech(self, text: str, mode: str):
        text = self._speech_text(text)
        if not text:
            return
        if self._tts_active:
            self._speech_queue.append((text, mode))
            return
        self._start_speech(text, mode)

    def _start_speech(self, text: str, mode: str):
        self.wake_listener.pause()
        self._tts_active = True
        self._tts_mode = mode
        if mode == "reply":
            self.bridge.ttsStarted.emit()
        self.tts.say(text)

    def _play_next_speech(self):
        if self._tts_active:
            return
        if self._speech_queue:
            text, mode = self._speech_queue.pop(0)
            self._start_speech(text, mode)
        elif not self._interaction_active:
            self.wake_listener.resume()

    @Slot(QTextToSpeech.State)
    def _on_tts_state_changed(self, state):
        if not self._tts_active:
            return
        if state == QTextToSpeech.State.Ready:
            mode = self._tts_mode
            self._tts_active = False
            self._tts_mode = None
            if mode == "reply":
                self.bridge.ttsFinished.emit()
                self._interaction_active = False
                self.bridge.audioLevelChanged.emit(0.0)
            QTimer.singleShot(180, self._play_next_speech)
        elif state == QTextToSpeech.State.Error:
            self._tts_active = False
            self._tts_mode = None
            self.bridge.ttsError.emit(self.tts.errorString() or "语音合成失败。")
            self._finish_interaction(delay_ms=900)

    @Slot(str, str)
    def _on_activity(self, app_name, title):
        self.memory.record_activity(app_name, title)
        self.bridge.activityChanged.emit(app_name, title)

    @Slot()
    def _check_reminders(self):
        triggered = False
        for reminder in self.memory.due_reminders():
            triggered = True
            self.memory.mark_reminder_fired(reminder["id"])
            stamp = datetime.fromtimestamp(reminder["due_at"]).strftime("%H:%M")
            message = reminder["message"]
            print(f"[Reminder] {stamp} {message}")
            self.bridge.reminderTriggered.emit(stamp, message)
            self._enqueue_speech(f"提醒你，{message}。", "reminder")
        if triggered:
            self._refresh_next_reminder()

    @Slot()
    def _refresh_next_reminder(self):
        reminders = self.memory.pending_reminders(1)
        if not reminders:
            self.bridge.nextReminderChanged.emit("--:--", "暂无待处理提醒")
            return
        reminder = reminders[0]
        due = datetime.fromtimestamp(reminder["due_at"])
        self.bridge.nextReminderChanged.emit(
            due.strftime("%m-%d %H:%M"), reminder["message"]
        )

    @Slot(float, float, float, str, str, bool)
    def _on_metrics(self, cpu, memory, disk, network, uptime, llm_online):
        self.bridge.systemMetrics.emit(cpu, memory, disk, network, uptime)
        if llm_online != self._last_llm_online:
            self._last_llm_online = llm_online
            self.bridge.llmStatusChanged.emit(llm_online, "qwen3.5:0.8b")

    def _finish_interaction(self, delay_ms=0):
        def finish():
            self._interaction_active = False
            self.bridge.audioLevelChanged.emit(0.0)
            if not self._tts_active and not self._speech_queue:
                self.wake_listener.resume()

        if delay_ms:
            QTimer.singleShot(delay_ms, finish)
        else:
            finish()

    @Slot()
    def cleanup(self):
        print("[Jarvis] 正在安全退出...")
        keyboard.unhook_all_hotkeys()
        self.reminder_timer.stop()
        self.context_timer.stop()
        self.tts.stop()

        for thread in (
            self.wake_listener,
            self.stt_listener,
            self.llm_worker,
            self.monitor,
            self.activity_tracker,
        ):
            if thread is not None and thread.isRunning():
                thread.requestInterruption()
                thread.wait(2000)


def parse_args():
    parser = argparse.ArgumentParser(description="Personal Jarvis")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="只预览 HUD，不启动麦克风与模型",
    )
    parser.add_argument(
        "--screenshot",
        type=Path,
        help="预览模式下保存界面截图并退出",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="重新打开首次运行设置",
    )
    return parser.parse_args()


def make_tray_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#0A1722"))
    painter.setPen(QPen(QColor("#38E8FF"), 3))
    painter.drawEllipse(3, 3, 58, 58)
    painter.setPen(QColor("#E7FBFF"))
    painter.setFont(QFont("Bahnschrift", 27, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "J")
    painter.end()
    return QIcon(pixmap)


def main():
    args = parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("Personal Jarvis")
    app.setOrganizationName("Personal AI Systems")
    if not (args.preview or args.screenshot):
        app.setQuitOnLastWindowClosed(False)
        from setup_wizard import SetupDialog, setup_completed

        if args.setup or (getattr(sys, "frozen", False) and not setup_completed()):
            if SetupDialog().exec() != SetupDialog.DialogCode.Accepted:
                return 1

    engine = QQmlApplicationEngine()
    bridge = JarvisBridge()
    engine.rootContext().setContextProperty("jarvisBridge", bridge)
    engine.rootContext().setContextProperty(
        "jarvisPreview", bool(args.preview or args.screenshot)
    )

    qml_file = resource_root() / "ui" / "Main.qml"
    engine.load(qml_file)
    if not engine.rootObjects():
        print("[ERROR] QML 加载失败")
        return 1

    root_window = engine.rootObjects()[0]
    if not (args.preview or args.screenshot):
        # The HUD is display-only: Windows sends every click to the application
        # underneath it, even while Jarvis is full-screen and visible.
        root_window.setFlag(Qt.WindowType.WindowTransparentForInput, True)
        root_window.setFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)

    controller = None
    tray = None
    if not (args.preview or args.screenshot):
        if QSystemTrayIcon.isSystemTrayAvailable():
            tray = QSystemTrayIcon(make_tray_icon(), app)
            tray.setToolTip("Jarvis 正在后台聆听 · F8 显示/隐藏")
            tray_menu = QMenu()
            show_action = tray_menu.addAction("显示 Jarvis")
            hide_action = tray_menu.addAction("隐藏 Jarvis（继续聆听）")
            tray_menu.addSeparator()
            setup_action = tray_menu.addAction("设置 / 环境检查")
            quit_action = tray_menu.addAction("退出 Jarvis")
            show_action.triggered.connect(lambda checked=False: bridge.showHudRequested.emit())
            hide_action.triggered.connect(lambda checked=False: bridge.hideHudRequested.emit())
            def open_setup(checked=False):
                if SetupDialog().exec() == SetupDialog.DialogCode.Accepted:
                    if not controller.wake_listener.isRunning() and wake_model_ready():
                        controller.wake_listener.start()

            setup_action.triggered.connect(open_setup)
            quit_action.triggered.connect(lambda checked=False: app.quit())
            tray.setContextMenu(tray_menu)

            def on_tray_activated(reason):
                if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
                    bridge.toggleHud.emit()

            tray.activated.connect(on_tray_activated)
            tray.show()
        else:
            print("[Jarvis] 当前系统未提供托盘；仍可用 F8 显示或隐藏界面。")

        controller = JarvisController(bridge)
        controller.start()
        app.aboutToQuit.connect(controller.cleanup)

    if args.screenshot:
        output = args.screenshot.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        window = root_window
        quick_window = shiboken6.wrapInstance(
            shiboken6.getCppPointer(window)[0], QQuickWindow
        )

        def save_screenshot():
            try:
                image = quick_window.grabWindow()
                if image.save(str(output)):
                    print(f"[Preview] 已保存：{output}")
                else:
                    print(f"[Preview] 截图保存失败：{output}")
            finally:
                app.quit()

        QTimer.singleShot(1800, save_screenshot)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
