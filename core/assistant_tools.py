"""Safe, explicit Windows tools available to the local assistant."""

from __future__ import annotations

import ctypes
import difflib
import json
import os
import re
import shutil
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from core.memory_store import MemoryStore


@dataclass
class ToolResult:
    success: bool
    message: str
    data: dict | list | None = None

    def as_json(self):
        return json.dumps(asdict(self), ensure_ascii=False)


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "hide_hud",
            "description": "只收起 Jarvis 界面，不退出程序；继续在后台聆听唤醒词和触发提醒。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "打开 Windows 中已安装的应用程序。",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "应用名称"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_calendar",
            "description": "打开用户的 Windows Outlook 日历。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "用默认浏览器搜索用户给出的内容。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "premier_league_scores",
            "description": "查询指定日期的英超实时比分和赛程；日期使用 YYYY-MM-DD。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD，默认今天"},
                    "open_browser": {"type": "boolean", "description": "是否同时打开比分网页"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "创建真正会触发语音和 HUD 通知的提醒。",
            "parameters": {
                "type": "object",
                "properties": {
                    "when": {"type": "string", "description": "ISO 日期时间或自然语言时间"},
                    "message": {"type": "string", "description": "提醒事项"},
                },
                "required": ["when", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": "列出尚未触发的提醒。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_reminder",
            "description": "取消一个待触发提醒。",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_activity",
            "description": "读取本机保存的最近前台应用和窗口活动，回答用户最近在做什么。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class AssistantTools:
    SCORE_ENDPOINT = (
        "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard"
    )

    APP_ALIASES = {
        "计算器": "calc.exe",
        "calculator": "calc.exe",
        "记事本": "notepad.exe",
        "notepad": "notepad.exe",
        "资源管理器": "explorer.exe",
        "文件管理器": "explorer.exe",
        "文件夹": "explorer.exe",
        "终端": "wt.exe",
        "windows终端": "wt.exe",
        "命令提示符": "cmd.exe",
        "任务管理器": "taskmgr.exe",
        "设置": "ms-settings:",
        "画图": "mspaint.exe",
        "vscode": "Visual Studio Code",
        "visualstudiocode": "Visual Studio Code",
        "代码编辑器": "Visual Studio Code",
        "edge": "Microsoft Edge",
        "微软浏览器": "Microsoft Edge",
        "腾讯会议": "腾讯会议",
        "matlab": "MATLAB R2024b",
        "keil": "Keil uVision5",
        "wps": "WPS Office",
        "哔哩哔哩": "哔哩哔哩",
        "b站": "哔哩哔哩",
        "酷狗": "酷狗音乐",
        "飞书": "飞书",
        "steam": "Steam",
    }

    def __init__(self, root: Path, memory: MemoryStore):
        self.root = Path(root)
        self.memory = memory
        self._shortcuts = self._discover_shortcuts()

    @staticmethod
    def _normalize(value: str):
        return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.lower())

    def _discover_shortcuts(self):
        folders = [
            Path(os.environ.get("PROGRAMDATA", "C:/ProgramData"))
            / "Microsoft/Windows/Start Menu/Programs",
            Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        ]
        shortcuts = []
        for folder in folders:
            if not folder.exists():
                continue
            for path in folder.rglob("*.lnk"):
                if path.name.lower().startswith("uninstall"):
                    continue
                shortcuts.append((path.stem, path))
        return shortcuts

    @staticmethod
    def _shell_open(target: str):
        result = ctypes.windll.shell32.ShellExecuteW(None, "open", target, None, None, 1)
        if result <= 32:
            raise OSError(f"Windows 无法打开目标（错误码 {result}）")

    def _match_shortcut(self, requested: str):
        normalized = self._normalize(requested)
        if normalized in self.APP_ALIASES:
            requested = self.APP_ALIASES[normalized]
            normalized = self._normalize(requested)

        exact = [item for item in self._shortcuts if self._normalize(item[0]) == normalized]
        if exact:
            return exact[0]

        contained = [
            item
            for item in self._shortcuts
            if normalized and normalized in self._normalize(item[0])
        ]
        if contained:
            return sorted(contained, key=lambda item: len(item[0]))[0]

        scored = sorted(
            (
                difflib.SequenceMatcher(None, normalized, self._normalize(name)).ratio(),
                name,
                path,
            )
            for name, path in self._shortcuts
        )
        if scored and scored[-1][0] >= 0.62:
            _, name, path = scored[-1]
            return name, path
        return None

    def open_application(self, name: str):
        requested = (name or "").strip().strip("。,.，")
        if not requested:
            return ToolResult(False, "没有提供要打开的应用名称。")

        normalized = self._normalize(requested)
        alias_target = self.APP_ALIASES.get(normalized)
        if alias_target and (alias_target.endswith(".exe") or alias_target.endswith(":")):
            executable = shutil.which(alias_target) if alias_target.endswith(".exe") else None
            target = executable or alias_target
            try:
                self._shell_open(target)
                return ToolResult(True, f"已打开{requested}。", {"target": target})
            except OSError as exc:
                return ToolResult(False, f"无法打开{requested}：{exc}")

        match = self._match_shortcut(alias_target or requested)
        if not match:
            return ToolResult(False, f"没有在开始菜单中找到“{requested}”。")

        display_name, shortcut = match
        try:
            self._shell_open(str(shortcut))
            return ToolResult(True, f"已打开{display_name}。", {"shortcut": str(shortcut)})
        except OSError as exc:
            return ToolResult(False, f"无法打开{display_name}：{exc}")

    @staticmethod
    def hide_hud():
        return ToolResult(True, "界面已收起，我仍在后台待命。")

    def open_calendar(self):
        try:
            self._shell_open("outlookcal:")
            return ToolResult(True, "已打开 Outlook 日历。", {"uri": "outlookcal:"})
        except OSError:
            url = "https://outlook.live.com/calendar/0/view/month"
            opened = webbrowser.open(url, new=2)
            return ToolResult(
                bool(opened),
                "已在浏览器打开 Outlook 日历。" if opened else "无法打开日历。",
                {"url": url},
            )

    @staticmethod
    def open_browser(url: str = "https://www.bing.com"):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return ToolResult(False, "为了安全，只允许打开 http 或 https 网页。")
        opened = webbrowser.open(url, new=2)
        return ToolResult(bool(opened), "已打开浏览器。" if opened else "浏览器启动失败。")

    def search_web(self, query: str):
        query = (query or "").strip()
        if not query:
            return self.open_browser()
        url = "https://www.bing.com/search?q=" + urllib.parse.quote(query)
        result = self.open_browser(url)
        if result.success:
            result.message = f"已在浏览器搜索“{query}”。"
            result.data = {"url": url}
        return result

    @staticmethod
    def _score_date(value: str | None):
        if not value:
            return datetime.now().astimezone().date()
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return datetime.now().astimezone().date()

    def premier_league_scores(self, date: str | None = None, open_browser: bool = False):
        target_date = self._score_date(date)
        date_key = target_date.strftime("%Y%m%d")
        url = self.SCORE_ENDPOINT + "?" + urllib.parse.urlencode({"dates": date_key})
        browser_url = (
            "https://www.espn.com/soccer/scoreboard/_/league/eng.1/date/" + date_key
        )
        browser_result = self.open_browser(browser_url) if open_browser else None
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "PersonalJarvis/2.2", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                payload = json.load(response)
        except Exception as exc:
            if browser_result and browser_result.success:
                return ToolResult(
                    True,
                    "实时比分接口暂时不可用，但已在浏览器打开英超比分页面。",
                    {"url": browser_url, "api_error": str(exc)},
                )
            return ToolResult(False, f"英超比分查询失败：{exc}")

        matches = []
        for event in payload.get("events", []):
            competition = (event.get("competitions") or [{}])[0]
            competitors = competition.get("competitors") or []
            home = next((item for item in competitors if item.get("homeAway") == "home"), None)
            away = next((item for item in competitors if item.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            status = competition.get("status", {}).get("type", {})
            matches.append(
                {
                    "home": home.get("team", {}).get("displayName", "主队"),
                    "away": away.get("team", {}).get("displayName", "客队"),
                    "home_score": str(home.get("score", "-")),
                    "away_score": str(away.get("score", "-")),
                    "status": status.get("shortDetail") or status.get("detail") or "",
                    "completed": bool(status.get("completed")),
                }
            )

        label = target_date.strftime("%m月%d日")
        if not matches:
            message = f"{label}没有查询到英超比赛。"
        else:
            rendered = []
            for match in matches:
                rendered.append(
                    f"{match['home']} {match['home_score']} 比 {match['away_score']} "
                    f"{match['away']}，{match['status']}"
                )
            message = f"{label}英超共有{len(matches)}场：" + "；".join(rendered)

        return ToolResult(
            True,
            message,
            {"date": target_date.isoformat(), "matches": matches, "url": browser_url},
        )

    @staticmethod
    def _chinese_number(value: str):
        digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
                  "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
        if value == "十":
            return 10
        if "十" in value:
            left, right = value.split("十", 1)
            return (digits.get(left, 1) * 10) + digits.get(right, 0)
        return digits.get(value)

    @classmethod
    def parse_reminder(cls, text: str, now: datetime | None = None):
        now = now or datetime.now().astimezone()
        original = text.strip()
        normalized = re.sub(
            r"([零〇一二两三四五六七八九十]{1,3})(?=点|分钟|小时)",
            lambda match: str(cls._chinese_number(match.group(1))),
            original,
        )

        relative = re.search(
            r"(?P<n>\d+)\s*(?P<unit>分钟|小时)后.*?(?:提醒我|提醒)\s*(?P<msg>.+)",
            normalized,
        ) or re.search(
            r"(?:提醒我|提醒).*?(?P<n>\d+)\s*(?P<unit>分钟|小时)后\s*(?P<msg>.+)",
            normalized,
        )
        if relative:
            amount = int(relative.group("n"))
            delta = timedelta(minutes=amount) if relative.group("unit") == "分钟" else timedelta(hours=amount)
            return now + delta, relative.group("msg").strip(" ，。的时候")

        time_match = re.search(
            r"(?P<date>今天|明天|后天)?\s*"
            r"(?P<period>凌晨|早上|上午|中午|下午|晚上)?\s*"
            r"(?P<hour>\d{1,2})(?:\s*(?:点|时|[:：])\s*(?P<minute>\d{1,2})?\s*分?)?",
            normalized,
        )
        marker = re.search(r"提醒我|提醒", normalized)
        if not time_match or not marker:
            return None

        hour = int(time_match.group("hour"))
        minute = int(time_match.group("minute") or 0)
        if hour > 23 or minute > 59:
            return None
        period = time_match.group("period") or ""
        if period in {"下午", "晚上"} and hour < 12:
            hour += 12
        elif period == "中午" and hour < 11:
            hour += 12
        elif period == "凌晨" and hour == 12:
            hour = 0

        date_word = time_match.group("date") or ""
        days = {"今天": 0, "明天": 1, "后天": 2}.get(date_word, 0)
        due = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days)
        if not date_word and due <= now:
            due += timedelta(days=1)
        if date_word == "今天" and due <= now:
            return None

        if marker.start() < time_match.start():
            message = normalized[time_match.end():]
        else:
            message = normalized[marker.end():]
        message = re.sub(r"^(我|在|到|的时候|一下)+", "", message).strip(" ，。的时候")
        if not message:
            message = "查看提醒事项"
        return due, message

    def create_reminder(self, when: str, message: str):
        now = datetime.now().astimezone()
        due = None
        try:
            due = datetime.fromisoformat(when)
            if due.tzinfo is None:
                due = due.replace(tzinfo=now.tzinfo)
        except (ValueError, TypeError):
            parsed = self.parse_reminder(f"提醒我{when}{message}", now)
            if parsed:
                due, parsed_message = parsed
                message = parsed_message or message

        if due is None or due <= now:
            return ToolResult(False, "没有识别到有效的未来提醒时间。")
        reminder_id = self.memory.create_reminder(due, message)
        rendered = due.strftime("%m月%d日 %H:%M")
        return ToolResult(
            True,
            f"提醒已设置：{rendered}提醒你{message}。",
            {"id": reminder_id, "due_at": due.isoformat(), "message": message},
        )

    def list_reminders(self):
        reminders = self.memory.pending_reminders(10)
        if not reminders:
            return ToolResult(True, "目前没有待触发的提醒。", [])
        rendered = [
            f"{datetime.fromtimestamp(item['due_at']).strftime('%m月%d日 %H:%M')} {item['message']}"
            for item in reminders
        ]
        return ToolResult(True, "待处理提醒：" + "；".join(rendered), reminders)

    def cancel_reminder(self, keyword: str = ""):
        reminder = self.memory.cancel_reminder(keyword)
        if not reminder:
            return ToolResult(False, "没有找到匹配的待处理提醒。")
        return ToolResult(True, f"已取消提醒：{reminder['message']}。", reminder)

    def get_recent_activity(self):
        rows = self.memory.recent_activity(8)
        return ToolResult(True, "你最近主要在做这些事：" + self.memory.activity_summary(6), rows)

    def execute(self, name: str, arguments: dict | None = None):
        arguments = arguments or {}
        handlers = {
            "hide_hud": self.hide_hud,
            "open_application": lambda: self.open_application(str(arguments.get("name", ""))),
            "open_calendar": self.open_calendar,
            "search_web": lambda: self.search_web(str(arguments.get("query", ""))),
            "premier_league_scores": lambda: self.premier_league_scores(
                arguments.get("date"), bool(arguments.get("open_browser", False))
            ),
            "create_reminder": lambda: self.create_reminder(
                str(arguments.get("when", "")), str(arguments.get("message", "提醒事项"))
            ),
            "list_reminders": self.list_reminders,
            "cancel_reminder": lambda: self.cancel_reminder(str(arguments.get("keyword", ""))),
            "get_recent_activity": self.get_recent_activity,
        }
        handler = handlers.get(name)
        if not handler:
            return ToolResult(False, f"不支持的工具：{name}")
        try:
            result = handler()
        except Exception as exc:
            result = ToolResult(False, f"工具执行失败：{exc}")
        self.memory.record_action(name, result.message, result.success)
        return result

    def direct_route(self, text: str):
        clean = re.sub(r"^(贾维斯|jarvis)[，,\s]*", "", text.strip(), flags=re.I)
        lower = clean.lower()

        if re.fullmatch(
            r"(?:关闭|隐藏|收起)(?:一下)?\s*(?:你自己|贾维斯|jarvis|界面|窗口|面板|hud)?\s*(?:吧|了)?[。.!！\s]*",
            clean,
            flags=re.I,
        ):
            return "hide_hud", {}

        if "英超" in clean and any(word in clean for word in ("比分", "赛果", "比赛", "赛程")):
            offset = -1 if "昨天" in clean else 1 if "明天" in clean else 0
            date = (datetime.now().astimezone() + timedelta(days=offset)).date().isoformat()
            return "premier_league_scores", {
                "date": date,
                "open_browser": "浏览器" in clean or "打开" in clean,
            }

        if any(phrase in clean for phrase in ("最近在干嘛", "最近做了什么", "刚才在干嘛", "最近忙什么")):
            return "get_recent_activity", {}

        if any(phrase in clean for phrase in ("有哪些提醒", "查看提醒", "我的提醒", "什么提醒")):
            return "list_reminders", {}

        cancel_match = re.search(
            r"(?:取消|删除)(?:一下)?(?:(?P<middle>.+?)的)?提醒(?P<after>.*)", clean
        )
        if cancel_match:
            keyword = (cancel_match.group("middle") or cancel_match.group("after") or "").strip(" ，。")
            return "cancel_reminder", {"keyword": keyword}

        if "提醒" in clean:
            parsed = self.parse_reminder(clean)
            if parsed:
                due, message = parsed
                return "create_reminder", {"when": due.isoformat(), "message": message}

        if re.search(r"(?:打开|启动).{0,4}日历", clean, flags=re.I):
            return "open_calendar", {}

        if "打开浏览器" in clean and not any(word in clean for word in ("搜索", "查", "看看")):
            return "search_web", {"query": ""}

        search_match = re.search(r"(?:搜索|搜一下|查一下|查询)\s*(.+)", clean)
        if search_match and search_match.group(1).strip():
            return "search_web", {"query": search_match.group(1).strip()}

        open_match = re.search(r"(?:打开|启动|运行)(?:一下)?\s*(.+?)(?:程序|软件)?$", clean, flags=re.I)
        if open_match:
            app_name = open_match.group(1).strip(" ，。")
            if app_name:
                return "open_application", {"name": app_name}

        if lower in {"浏览器", "打开网页"}:
            return "search_web", {"query": ""}
        return None
