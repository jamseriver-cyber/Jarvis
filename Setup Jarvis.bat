@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 goto failed
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed

".venv\Scripts\python.exe" scripts\install_kws_model.py
if errorlevel 1 goto failed

echo.
echo [Jarvis] Python 依赖和唤醒模型已准备好。
echo [Jarvis] 还需要安装 Ollama，并运行：ollama pull qwen3.5:0.8b
echo [Jarvis] 然后双击 Start Jarvis.bat。
pause
exit /b 0

:failed
echo.
echo [Jarvis] 安装未完成。请查看上方错误信息。
pause
exit /b 1
