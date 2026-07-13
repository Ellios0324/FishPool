@echo off
chcp 65001 >nul
title 🧠 Leader Agent — 快速启动

cd /d "%~dp0"

echo.
echo ╔══════════════════════════════════════════╗
echo ║    🧠  Leader Agent                     ║
echo ║    快速启动                             ║
echo ╚══════════════════════════════════════════╝
echo.

:: 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo ❌ 未检测到 Python，请先安装 Python 3.9+
    echo    下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查依赖
python -c "import openai" >nul 2>&1
if errorlevel 1 (
    echo ⚠️ 依赖未安装，正在安装...
    pip install -r AgentSkills\requirements.txt
    if errorlevel 1 (
        echo ❌ 依赖安装失败！
        pause
        exit /b 1
    )
    echo ✅ 依赖安装完成
) else (
    echo ✅ 依赖已就绪
)

echo.
echo 🚀 正在启动 Leader Agent...
echo.

python LeaderAgent.py

echo.
echo ✅ Leader Agent 已退出，感谢使用！
pause
