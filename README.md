# Personal Jarvis

面向 Windows 的本地优先中文语音助手。v0.2 开始提供 Windows 安装包构建流程和首次运行向导；语音模型与 Ollama 仍须在用户同意后从各自的上游来源下载。当前仍是测试版，不是无需配置的商业成品。

## 功能

- 中文唤醒词“贾维斯”、本地 Whisper 语音识别、Ollama 对话、Windows 中文语音播报。
- 后台常驻聆听，唤醒时才显示全屏科技 HUD；HUD 的鼠标与键盘输入可穿透到桌面。`F8` 显示/隐藏，`F9` 免唤醒词对话；也可通过系统托盘图标显示、隐藏或退出。打开应用/网页后 HUD 会自动收起。
- 打开已安装应用或日历、网页搜索、查询当天或指定日期的英超比分。
- 创建、查看、取消提醒；程序运行时到点通过 HUD 和语音通知。
- SQLite 保存近期对话、操作记录、前台窗口活动和未完成提醒。
- 工具采用白名单/受控入口；模型不能直接执行任意命令行或删除文件。

## Windows 安装版（v0.2）

正式发布后，可从项目的 [Releases](https://github.com/jamseriver-cyber/Jarvis/releases) 页面获取 `PersonalJarvis-Setup-0.2.0-win64.exe`，核对发布页的 SHA-256 后运行。开发者也可按下文步骤自行构建。安装器使用当前用户权限，不要求管理员权限；会创建开始菜单快捷方式，并可选择创建桌面快捷方式。

首次启动会打开系统就绪检查。点击“准备语音模型”下载唤醒模型和 Whisper；已有源码版唤醒模型的用户也可以手动选择该模型文件夹导入，导入前会校验文件哈希。安装 [Ollama](https://ollama.com/download) 后点击“准备 Ollama 模型”。检测到默认麦克风、唤醒模型、语音识别模型和本地对话模型后，才能完成设置。下载需要网络，安装包本身不包含第三方模型。以后可从托盘菜单的“设置 / 环境检查”重新打开向导。

升级时运行新版安装包即可。程序安装在当前用户的 `LocalAppData\Programs\Personal Jarvis`；提醒、记忆、录音临时文件、唤醒模型和设置保存在 `LocalAppData\PersonalJarvis`，安装升级不会覆盖，卸载也不会自动删除。源码版旧数据仍在原项目的 `data/` 中；v0.2 不会擅自搜索并导入其他目录的数据。

安装包尚未签名，Windows 可能提示“未知发布者”。只从本项目仓库下载，不要忽略来源和哈希校验。

## 源码安装与运行

系统要求：Windows 10/11、Python 3.11 或更新版本、麦克风、可用的中文系统语音，以及 [Ollama](https://ollama.com/download)。本项目当前在 Python 3.13 上开发和验证。

1. 下载或克隆仓库，双击 `Setup Jarvis.bat`。它会创建 `.venv`、安装 Python 依赖，并从 [sherpa-onnx 官方发布页](https://github.com/k2-fsa/sherpa-onnx/releases/tag/kws-models)下载唤醒模型；下载文件会经过 SHA-256 校验。模型权重不在本仓库内。若你已有上游原始归档，也可运行 `python scripts/install_kws_model.py --archive <归档路径>`。
2. 安装 Ollama，在终端运行 `ollama pull qwen3.5:0.8b`。
3. 双击 `Start Jarvis.bat`。Jarvis 默认在后台聆听，托盘中会出现 J 图标；说“贾维斯”后 HUD 会弹出，听到提示音再说出任务。首次加载 Whisper 可能较慢。可最小化启动命令窗口，但不要关闭，否则 Jarvis 会退出。

不需要 HUD 时按 `F8`，或右键托盘图标选“隐藏 Jarvis”；隐藏后仍会聆听唤醒词并触发提醒。双击托盘图标或再次按 `F8` 可显示 HUD。右键托盘图标可安全退出。

开发者也可以运行：

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\install_kws_model.py
.venv\Scripts\python.exe main.py
```

## 可以尝试的指令

| 指令 | 行为 |
| --- | --- |
| “打开 VS Code / 计算器 / 腾讯会议” | 查找并启动已安装应用 |
| “关闭 / 隐藏界面 / 收起 Jarvis” | 仅隐藏 HUD，继续在后台聆听与提醒 |
| “打开日历” | 打开 Outlook 日历；不会自动创建日程 |
| “打开浏览器搜索 STM32 串口教程” | 用默认浏览器搜索 |
| “打开浏览器帮我看看今天英超的比分” | 查询赛程/比分并打开比分页面 |
| “下午五点提醒我开会” | 保存提醒，程序运行时到点播报 |
| “查看我的提醒”“取消开会的提醒” | 管理未触发提醒 |
| “我最近在干嘛？” | 基于本机记录的窗口活动回答 |

## 隐私与安全

语音识别、对话模型和语音播报在本机运行。查询英超比分会访问 ESPN；网页搜索和日历会打开浏览器；首次安装会从上游下载 Python 依赖与唤醒模型。**本项目并非完全离线应用。**

运行时会在本机数据库中记录对话、提醒、工具操作、前台应用名和窗口标题。源码版数据库位于 `data/jarvis_memory.db`；安装版位于 `LocalAppData\PersonalJarvis\data\jarvis_memory.db`。窗口标题可能含有个人信息；项目目录中的数据库和临时录音均被 `.gitignore` 排除，不应上传。若不想保留历史，可以在退出程序后自行备份或删除对应的 `data/`；当前尚无界面内的隐私管理开关。

本仓库只发布项目源码和自有资源。Python 包、Ollama 模型与 sherpa-onnx 唤醒模型分别受各自的许可证约束；本仓库的 MIT 许可证**不授予第三方模型权重的再分发权**。特别是当前唤醒模型的权重授权说明尚不够明确，因此不会把它打包到仓库或 Release 中。

## 已知限制

- 需要 Jarvis 保持运行，提醒才会准时播报；目前没有系统级后台提醒服务。
- 只能打开日历，暂不能创建、修改或确认日程；也不能在其他软件内部完成多步点击任务。
- 只记录近期活动和对话，尚无可编辑的长期记忆、屏幕理解或文档知识库。
- 模型名、唤醒灵敏度和麦克风阈值仍在代码中配置；现有设置向导只负责环境检查和模型准备，尚不能调整这些参数。
- Windows 中文语音因电脑安装情况而异；没有兼容的中文语音时可能无法正常播报。

## 开发与验证

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.venv\Scripts\python.exe -m compileall -q main.py core llm voice scripts
```

`tests/validate_assistant.py` 是会实际打开软件和网页的手动验收脚本，不在自动测试中运行。架构大致为 `唤醒 → 录音/Whisper → 快速意图路由或 Ollama 工具调用 → Windows 工具 → 语音/HUD`。欢迎提交 issue 和 PR；请先阅读 [贡献说明](CONTRIBUTING.md) 与 [安全说明](SECURITY.md)。

构建 Windows 安装包需在 Windows 10/11 x64 上安装 [Inno Setup 6](https://jrsoftware.org/isinfo.php)，然后运行：

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\packaging\build_windows.ps1
```

脚本先用 PyInstaller 生成可运行程序，并运行 QML 预览自检，再生成 `dist/installer/PersonalJarvis-Setup-0.2.0-win64.exe` 和 SHA-256。`dist/` 是本地构建产物，不会被 Git 跟踪。

## 常见问题

- 找不到模型：运行 `ollama pull qwen3.5:0.8b`，并确认 Ollama 已启动。
- 唤醒模型下载失败：检查 GitHub 网络访问，或手动从上游下载归档并用 `--archive` 安装。
- 听不到回复：检查 Windows 默认输出设备和可用中文语音。
- 识别不到说话：检查默认麦克风；`voice/stt_listener.py` 中的 `energy_threshold` 当前默认为 `0.012`。
- 提醒没响：确认程序在预定时间保持运行。

## 许可证

项目源码采用 [MIT License](LICENSE)。第三方模型和依赖不包含在此授权范围内。
