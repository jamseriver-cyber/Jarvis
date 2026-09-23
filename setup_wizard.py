"""First-run checks and explicit model downloads for the installed edition."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import ollama
import sounddevice as sd
from faster_whisper import WhisperModel
from huggingface_hub import try_to_load_from_cache
from PySide6.QtCore import QThread, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from llm.ollama_worker import OllamaWorker
from runtime_paths import user_root, wake_model_dir, wake_model_ready
from scripts.install_kws_model import import_model_folder, install_model


MODEL_NAME = "qwen3.5:0.8b"
WHISPER_REPO = "Systran/faster-whisper-small"
WHISPER_FILES = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")


def whisper_ready() -> bool:
    return all(
        isinstance(found := try_to_load_from_cache(WHISPER_REPO, name), str)
        and Path(found).is_file()
        for name in WHISPER_FILES
    )


def setup_marker() -> Path:
    return user_root() / "setup.json"


def setup_completed() -> bool:
    return (
        setup_marker().is_file()
        and wake_model_ready()
        and whisper_ready()
        and OllamaWorker._ollama_executable() is not None
    )


@dataclass
class SetupStatus:
    wake: bool
    whisper: bool
    ollama_installed: bool
    ollama_model: bool
    microphone: bool

    @property
    def ready(self) -> bool:
        return all((self.wake, self.whisper, self.ollama_installed,
                    self.ollama_model, self.microphone))


def check_status() -> SetupStatus:
    installed = OllamaWorker._ollama_executable() is not None
    model = False
    if installed:
        try:
            response = ollama.Client(
                host="http://127.0.0.1:11434", timeout=2, trust_env=False
            ).list()
            model = MODEL_NAME in OllamaWorker._model_names(response)
        except Exception:
            pass
    try:
        sd.query_devices(kind="input")
        microphone = True
    except Exception:
        microphone = False
    return SetupStatus(wake_model_ready(), whisper_ready(), installed, model, microphone)


def prepare_ollama_model(report) -> None:
    executable = OllamaWorker._ollama_executable()
    if not executable:
        raise RuntimeError("未安装 Ollama。请先点‘安装 Ollama’并完成官方安装。")

    client = ollama.Client(
        host="http://127.0.0.1:11434", timeout=120, trust_env=False
    )
    try:
        client.list()
    except Exception:
        report("正在启动 Ollama 本地服务…")
        flags = 0
        if os.name == "nt":
            flags = (subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                     | subprocess.CREATE_NO_WINDOW)
        subprocess.Popen(
            [executable, "serve"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
            close_fds=True,
        )
        for _ in range(60):
            try:
                client.list()
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("Ollama 服务未能启动。请打开 Ollama 后重试。")

    report(f"正在准备本地对话模型 {MODEL_NAME}…")
    previous_status = None
    for progress in client.pull(MODEL_NAME, stream=True):
        status = getattr(progress, "status", "")
        if status and status != previous_status:
            report(status)
            previous_status = status
    if MODEL_NAME not in OllamaWorker._model_names(client.list()):
        raise RuntimeError("模型下载结束，但 Ollama 没有报告已安装模型。")


class PreparationWorker(QThread):
    progress = Signal(str)
    completed = Signal(bool, str)

    def __init__(self, task: str, parent=None):
        super().__init__(parent)
        self.task = task

    def run(self):
        try:
            if self.task == "voice":
                if not wake_model_ready():
                    self.progress.emit("正在下载并校验唤醒模型…")
                    install_model(wake_model_dir())
                if not whisper_ready():
                    self.progress.emit("正在下载语音识别模型；首次下载可能需要几分钟…")
                    WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4)
                self.completed.emit(True, "语音模型已准备好。")
            else:
                prepare_ollama_model(self.progress.emit)
                self.completed.emit(True, "本地对话模型已准备好。")
        except Exception as exc:
            self.completed.emit(False, str(exc))


class SetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jarvis v0.2 · 首次运行设置")
        self.setMinimumSize(650, 470)
        self.setStyleSheet(
            "QDialog { background: #091622; color: #E9F9FF; }"
            "QLabel { color: #D6F6FF; }"
            "QPushButton { background: #12384A; color: #E9FCFF; border: 1px solid #38CDE8;"
            " border-radius: 5px; padding: 9px; }"
            "QPushButton:hover { background: #1C5367; }"
            "QPushButton:disabled { color: #78919A; border-color: #365563; }"
            "QTextEdit { background: #0D202D; color: #B9ECF8; border: 1px solid #285566; }"
        )
        self.worker = None

        layout = QVBoxLayout(self)
        title = QLabel("J.A.R.V.I.S  /  系统就绪检查")
        title.setStyleSheet("font-size: 23px; font-weight: 700; color: #38E8FF;")
        layout.addWidget(title)
        layout.addWidget(QLabel(
            "模型由各自的官方来源下载，不包含在安装包中。准备完成后，Jarvis 才能通过语音唤醒和回答。"
        ))
        self.status_label = QLabel()
        self.status_label.setTextFormat(Qt.TextFormat.RichText)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(125)
        layout.addWidget(self.log)

        row = QHBoxLayout()
        self.voice_button = QPushButton("准备语音模型")
        self.ollama_button = QPushButton("准备 Ollama 模型")
        self.install_ollama_button = QPushButton("安装 Ollama")
        row.addWidget(self.voice_button)
        row.addWidget(self.ollama_button)
        row.addWidget(self.install_ollama_button)
        layout.addLayout(row)

        import_row = QHBoxLayout()
        self.import_model_button = QPushButton("导入已有唤醒模型文件夹")
        import_row.addWidget(self.import_model_button)
        import_row.addStretch()
        layout.addLayout(import_row)

        bottom = QHBoxLayout()
        self.refresh_button = QPushButton("重新检查")
        self.start_button = QPushButton("完成并启动 Jarvis")
        bottom.addWidget(self.refresh_button)
        bottom.addStretch()
        bottom.addWidget(self.start_button)
        layout.addLayout(bottom)

        self.voice_button.clicked.connect(lambda: self.start_task("voice"))
        self.ollama_button.clicked.connect(lambda: self.start_task("ollama"))
        self.install_ollama_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://ollama.com/download"))
        )
        self.import_model_button.clicked.connect(self.import_existing_model)
        self.refresh_button.clicked.connect(self.refresh)
        self.start_button.clicked.connect(self.finish)
        self.refresh()

    def refresh(self):
        status = check_status()
        rows = (
            ("唤醒模型", status.wake),
            ("Whisper 语音识别", status.whisper),
            ("Ollama 程序", status.ollama_installed),
            (MODEL_NAME + " 对话模型", status.ollama_model),
            ("默认麦克风", status.microphone),
        )
        self.status_label.setText("<br>".join(
            f"<span style='color:{'#6CFFCB' if ready else '#FFC857'}'>"
            f"{'● 已就绪' if ready else '○ 待准备'}</span>　{name}"
            for name, ready in rows
        ))
        self.start_button.setEnabled(status.ready)
        self.voice_button.setEnabled(not (status.wake and status.whisper))
        self.ollama_button.setEnabled(status.ollama_installed and not status.ollama_model)
        self.import_model_button.setEnabled(not status.wake)

    def import_existing_model(self):
        folder = QFileDialog.getExistingDirectory(self, "选择已有唤醒模型文件夹")
        if not folder:
            return
        try:
            import_model_folder(Path(folder), wake_model_dir())
            self.log.append("已有唤醒模型已校验并导入。")
        except Exception as exc:
            QMessageBox.warning(self, "导入失败", str(exc))
        self.refresh()

    def start_task(self, task: str):
        if self.worker and self.worker.isRunning():
            return
        self.voice_button.setEnabled(False)
        self.ollama_button.setEnabled(False)
        self.import_model_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.worker = PreparationWorker(task, self)
        self.worker.progress.connect(self.log.append)
        self.worker.completed.connect(self.task_completed)
        self.worker.start()

    def task_completed(self, success: bool, message: str):
        if self.worker:
            self.worker.wait(1000)
        self.log.append(message)
        if not success:
            QMessageBox.warning(self, "准备未完成", message)
        self.refresh_button.setEnabled(True)
        self.refresh()

    def finish(self):
        if not check_status().ready:
            QMessageBox.warning(self, "尚未就绪", "请先完成模型准备，并确认麦克风可用。")
            self.refresh()
            return
        marker = setup_marker()
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({
            "version": "0.2.0",
            "completed_at": datetime.now().astimezone().isoformat(),
        }), encoding="utf-8")
        self.accept()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "正在准备模型", "请等待当前下载结束后再关闭设置。")
            event.ignore()
        else:
            super().closeEvent(event)
