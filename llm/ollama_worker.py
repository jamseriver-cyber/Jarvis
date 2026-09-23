"""Hybrid deterministic + Ollama tool-calling assistant worker."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

import ollama
from PySide6.QtCore import QThread, Signal

from core.assistant_tools import TOOL_SCHEMAS


BASE_SYSTEM_PROMPT = (
    "你是 Personal Jarvis，一个运行在用户 Windows 电脑上的私人 AI 助理。"
    "你不仅能对话，还能通过提供的工具真正打开应用、打开日历、搜索网页、查询英超比分、"
    "设置和管理提醒、读取最近的本机活动。需要执行动作时必须调用工具，绝不能假装已经执行。"
    "工具失败时要如实说明，不要编造结果。默认使用简洁、自然、冷静的中文回答，"
    "通常一到三句话，适合直接朗读。不要使用 Markdown 表格，不要自称大型语言模型。"
    "hide_hud 只能用于收起 Jarvis 自己的界面；用户说关闭其他应用时不要调用它。"
    "不允许请求或执行任意命令行、删除文件、关机或其他未列出的高风险操作。"
)


class OllamaWorker(QThread):
    generation_started = Signal()
    chunk_ready = Signal(str)
    finished_text = Signal(str)
    error_occurred = Signal(str)
    server_ready = Signal(str)
    tool_started = Signal(str, str)
    tool_finished = Signal(str, bool, str)

    def __init__(self, user_text: str, history=None, tools=None, context="", parent=None):
        super().__init__(parent)
        self.user_text = user_text.strip()
        self.history = list(history or [])[-10:]
        self.tools = tools
        self.context = (context or "").strip()[:3000]
        self.model = "qwen3.5:0.8b"
        self.host = "http://127.0.0.1:11434"

    @staticmethod
    def _ollama_executable() -> str | None:
        executable = shutil.which("ollama")
        if executable:
            return executable
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidate = Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe"
        return str(candidate) if candidate.exists() else None

    @staticmethod
    def _model_names(response) -> set[str]:
        names = set()
        for item in getattr(response, "models", []) or []:
            name = getattr(item, "model", None) or getattr(item, "name", None)
            if name:
                names.add(str(name))
        return names

    def _ensure_server(self) -> ollama.Client:
        client = ollama.Client(host=self.host, timeout=120.0, trust_env=False)
        try:
            models = self._model_names(client.list())
        except Exception:
            executable = self._ollama_executable()
            if not executable:
                raise RuntimeError("未找到 Ollama，请先安装或修复 Ollama。")

            creation_flags = 0
            if os.name == "nt":
                creation_flags = (
                    subprocess.CREATE_NEW_PROCESS_GROUP
                    | subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NO_WINDOW
                )
            subprocess.Popen(
                [executable, "serve"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
                close_fds=True,
            )

            deadline = time.monotonic() + 60.0
            last_error = None
            while time.monotonic() < deadline:
                if self.isInterruptionRequested():
                    raise RuntimeError("本次请求已取消。")
                try:
                    models = self._model_names(client.list())
                    break
                except Exception as exc:
                    last_error = exc
                    time.sleep(0.5)
            else:
                raise RuntimeError(f"Ollama 服务启动失败：{last_error}")

        if self.model not in models:
            installed = "、".join(sorted(models)) or "无"
            raise RuntimeError(f"未找到本地模型 {self.model}。当前已安装：{installed}")
        self.server_ready.emit(self.model)
        return client

    def _system_prompt(self):
        now = datetime.now().astimezone()
        prompt = BASE_SYSTEM_PROMPT + (
            f"当前本地时间：{now.strftime('%Y-%m-%d %H:%M:%S %A')}。"
            "解释今天、明天、几点等相对时间时必须以这个时间为准。"
        )
        if self.context:
            prompt += "\n以下是只存储在本机的近期上下文，可在相关时使用：\n" + self.context
        return prompt

    def _emit_result(self, text: str):
        text = (text or "").strip()
        if not text:
            raise RuntimeError("助理没有生成可用回复。")
        self.chunk_ready.emit(text)
        self.finished_text.emit(text)

    def _execute_tool(self, name: str, arguments: dict):
        if self.tools is None:
            raise RuntimeError("助理工具系统尚未初始化。")
        detail = json.dumps(arguments, ensure_ascii=False)
        self.tool_started.emit(name, detail)
        result = self.tools.execute(name, arguments)
        self.tool_finished.emit(name, result.success, result.message)
        return result

    @staticmethod
    def _tool_call_parts(call):
        function = getattr(call, "function", None)
        name = getattr(function, "name", "")
        arguments = getattr(function, "arguments", {}) or {}
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}
        return str(name), dict(arguments)

    def run(self):
        try:
            print(f"[Assistant] 用户输入：{self.user_text}")
            self.generation_started.emit()

            direct = self.tools.direct_route(self.user_text) if self.tools else None
            if direct:
                name, arguments = direct
                result = self._execute_tool(name, arguments)
                self._emit_result(result.message)
                return

            client = self._ensure_server()
            messages = [{"role": "system", "content": self._system_prompt()}]
            messages.extend(self.history)
            messages.append({"role": "user", "content": self.user_text})

            start_time = time.perf_counter()
            response = client.chat(
                model=self.model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                stream=False,
                think=False,
                keep_alive=-1,
                options={"temperature": 0.25, "num_ctx": 6144, "num_predict": 256},
            )

            tool_calls = list(getattr(response.message, "tool_calls", None) or [])[:3]
            if not tool_calls:
                self._emit_result(response.message.content or "")
                print(f"[Assistant] 总耗时：{time.perf_counter() - start_time:.2f} 秒")
                return

            messages.append(response.message)
            for call in tool_calls:
                if self.isInterruptionRequested():
                    return
                name, arguments = self._tool_call_parts(call)
                result = self._execute_tool(name, arguments)
                messages.append(
                    {"role": "tool", "tool_name": name, "content": result.as_json()}
                )

            full_text = ""
            stream = client.chat(
                model=self.model,
                messages=messages,
                stream=True,
                think=False,
                keep_alive=-1,
                options={"temperature": 0.3, "num_ctx": 6144, "num_predict": 192},
            )
            for chunk in stream:
                if self.isInterruptionRequested():
                    return
                text = chunk.message.content or ""
                if text:
                    full_text += text
                    self.chunk_ready.emit(text)

            full_text = full_text.strip()
            if not full_text:
                last_result = result.message if tool_calls else "任务已处理。"
                full_text = last_result
                self.chunk_ready.emit(full_text)
            self.finished_text.emit(full_text)
            print(f"[Assistant] 完成：{full_text}")
            print(f"[Assistant] 总耗时：{time.perf_counter() - start_time:.2f} 秒")

        except Exception as exc:
            message = str(exc)
            print(f"[Assistant] ERROR: {message}")
            self.error_occurred.emit(message)
