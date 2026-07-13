@echo off
chcp 65001 >nul
title 📚 知识库 API 服务器

echo ╔══════════════════════════════════════════════╗
echo ║     📚 知识库 API 服务器 v1.0.0              ║
echo ║     基于 RAG 的本地知识库问答服务             ║
echo ╚══════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo 📂 工作目录: %CD%

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请安装 Python 3.8+
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo ✅ Python: %%i

:: 检查并安装依赖
echo.
echo 📦 检查依赖...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 goto install_deps
python -c "import chromadb" >nul 2>&1
if errorlevel 1 goto install_deps
python -c "import sentence_transformers" >nul 2>&1
if errorlevel 1 goto install_deps

echo ✅ 依赖已就绪
goto start_server

:install_deps
echo 📦 正在安装依赖 (可能需要几分钟)...
echo    💡 如果速度慢，可以使用国内镜像:
echo       pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)
echo ✅ 依赖安装完成

:start_server
echo.
echo 📋 启动配置:
echo    📂 知识库目录: %KB_DOCS_DIR% (默认: ./docs)
echo    🌐 监听地址: %HOST%:%PORT% (默认: 0.0.0.0:8000)
echo    📖 API 文档: http://localhost:%PORT%/docs

if defined LLM_API_KEY (
    echo    🤖 AI 问答: 已启用
) else (
    echo    🤖 AI 问答: 未启用 (纯检索模式)
    echo    💡 设置 LLM_API_KEY 环境变量可启用 AI 问答
)

echo.
echo 🚀 正在启动服务器...
echo    按 Ctrl+C 停止服务
echo.

python server.py
pause
