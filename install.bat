@echo off
chcp 65001 >nul
title 🧠 Leader Agent — 一键安装启动器

rem ============================================================================
rem  🧠 Leader Agent — Windows 一键安装启动器
rem  版本: v1.0.0
rem
rem  🪟 双击运行即可自动完成：
rem     ✅ 检查 Python 环境
rem     ✅ 安装所需依赖
rem     ✅ 配置 API Key（如未配置）
rem     ✅ 启动交互界面
rem ============================================================================

cls
echo.
echo ╔══════════════════════════════════════════╗
echo ║    🧠  Leader Agent                     ║
echo ║    AI 智能助手系统                      ║
echo ║    Windows 一键安装启动器               ║
echo ╚══════════════════════════════════════════╝
echo.

rem ─── 切换到脚本所在目录 ───
cd /d "%~dp0"

rem ─── 第 1 步：检查 Python ───
echo [1/4] 🔍 检查 Python 环境...

where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ 未检测到 Python！
    echo.
    echo Python 是本程序的运行基础，请先安装：
    echo.
    echo 1️⃣  打开 https://www.python.org/downloads/
    echo 2️⃣  下载并运行 Python 安装包
    echo 3️⃣  ⚠️ 安装时务必勾选 "Add Python to PATH"
    echo 4️⃣  安装完成后重新运行本脚本
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VERSION=%%i
echo    ✅ 已检测到: %PY_VERSION%
echo.

rem ─── 第 2 步：安装依赖 ───
echo [2/4] 📦 安装依赖...

if exist AgentSkills\requirements.txt (
    echo    正在检查依赖状态...
    python -c "import openai" >nul 2>&1
    if errorlevel 1 (
        echo    正在安装依赖（首次安装需要一些时间）...
        echo.
        pip install -r AgentSkills\requirements.txt --break-system-packages
        if errorlevel 1 (
            echo.
            echo ❌ 依赖安装失败，请手动运行：
            echo    pip install -r AgentSkills\requirements.txt --break-system-package
            echo.
            pause
            exit /b 1
        )
        echo.
        echo    ✅ 依赖安装完成！
    ) else (
        echo    ✅ 依赖已就绪
    )
) else (
    echo    ⚠️ 未找到 requirements.txt
)
echo.

rem ─── 第 3 步：配置 .env ───
echo [3/4] 🔑 配置 API 密钥...

:CHECK_ENV
if not exist ".env" (
    echo.
    echo ⚠️ 未找到 .env 配置文件
    echo.
    if exist ".env.example" (
        echo    正在从 .env.example 创建配置模板...
        copy ".env.example" ".env" >nul
    ) else (
        echo    正在创建配置模板...
        echo # 🔑 请在此配置您的 DeepSeek API 密钥 > .env
        echo # 申请地址: https://platform.deepseek.com/ >> .env
        echo DEEPSEEK_API_KEY=your_api_key_here >> .env
    )
    echo    ✅ 模板文件已创建！
    echo.
    echo 🔑 接下来请编辑 .env 文件，填入您的 DeepSeek API Key
    echo.
    echo 如何获取？
    echo   1. 打开 https://platform.deepseek.com/
    echo   2. 注册 → 登录 → API Keys → 创建新 Key
    echo   3. 复制 sk- 开头的密钥
    echo.
    echo ⏎ 按任意键打开记事本编辑 .env 文件...
    pause >nul
    notepad .env
    echo.
    echo ✅ 编辑完成，继续检查...
    goto :CHECK_ENV
)

echo    ✅ 配置文件存在

rem ─── 检查 API Key 是否有效 ───
:CHECK_KEY
echo    正在验证 API Key...

python -c "import dotenv; dotenv.load_dotenv(); import os; key=os.getenv('DEEPSEEK_API_KEY',''); exit(0 if key and key!='your_api_key_here' else 1)" 2>nul
if errorlevel 1 (
    echo.
    echo ⚠️ API Key 未配置或使用了模板值！
    echo.
    echo 请将 your_api_key_here 替换为您的真实 API Key
    echo.
    echo ⏎ 按任意键打开记事本编辑 .env 文件...
    pause >nul
    notepad .env
    echo.
    echo ✅ 编辑完成，重新验证...
    goto :CHECK_KEY
)

echo    ✅ API Key 验证通过
echo.

rem ─── 第 4 步：启动程序 ───
echo [4/4] 🚀 启动程序...
echo.
echo ═══════════════════════════════════════════
echo  所有检查通过，即将进入交互界面！
echo ═══════════════════════════════════════════
echo.
echo 💡 使用提示：
echo   • 直接输入问题，AI 会自动处理
echo   • 输入 /help 查看帮助
echo   • 输入 /exit 退出程序
echo   • 按 Ctrl+C 中断当前任务
echo.

rem ─── 启动 LeaderAgent（无 pause，在当前终端运行） ───
python LeaderAgent.py

echo.
echo ✅ Leader Agent 已退出，感谢使用！
echo.
