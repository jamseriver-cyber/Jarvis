@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [Jarvis] 未找到项目虚拟环境：.venv
    echo 请先双击 Setup Jarvis.bat 完成安装。
    pause
    exit /b 1
)

echo [Jarvis] 正在启动本地语音助手...
".venv\Scripts\python.exe" -u main.py

if errorlevel 1 (
    echo.
    echo [Jarvis] 程序异常退出，请查看上方错误信息。
    pause
)
