#!/usr/bin/env bash
# =============================================================================
#  🧠 Leader Agent — 一键安装启动器 (macOS / Linux)
#  版本: v1.0.0
#
#  运行方式：
#    bash install.sh
#    或 chmod +x install.sh && ./install.sh
#
#  功能：
#    ✅ 自动检测 Python 环境
#    ✅ 自动安装依赖
#    ✅ 引导配置 API Key
#    ✅ 启动交互界面
# =============================================================================

set -o pipefail

# ── ANSI 颜色 ──
C_RESET="\033[0m"
C_GREEN="\033[0;32m"
C_BRIGHT_GREEN="\033[1;32m"
C_RED="\033[0;31m"
C_BRIGHT_RED="\033[1;31m"
C_YELLOW="\033[0;33m"
C_BRIGHT_YELLOW="\033[1;33m"
C_CYAN="\033[0;36m"
C_BRIGHT_CYAN="\033[1;36m"
C_BLUE="\033[0;34m"
C_BRIGHT_WHITE="\033[1;37m"
C_GRAY="\033[0;90m"
C_BOLD="\033[1m"

# ── 输出函数 ──
info()  { echo -e "  ${C_BLUE}ℹ️${C_RESET} ${C_BRIGHT_WHITE}$1${C_RESET}"; }
ok()    { echo -e "  ${C_BRIGHT_GREEN}✅${C_RESET} ${C_BRIGHT_WHITE}$1${C_RESET} ${C_GREEN}$2${C_RESET}"; }
warn()  { echo -e "  ${C_BRIGHT_YELLOW}⚠️${C_RESET} ${C_BRIGHT_WHITE}$1${C_RESET}"; }
err()   { echo -e "  ${C_BRIGHT_RED}❌${C_RESET} ${C_BRIGHT_WHITE}$1${C_RESET}"; }
title() { echo -e "  ${C_BOLD}${C_BRIGHT_CYAN}$1${C_RESET}"; }

# ── 跨平台打开文件编辑器 ──
# 按优先级：open (macOS) → xdg-open (Linux) → $EDITOR → nano → vim → vi
open_file() {
    local file="$1"
    if command -v open &>/dev/null; then
        # macOS: 使用默认文本编辑器
        open -t "$file"
    elif command -v xdg-open &>/dev/null; then
        # Linux 桌面环境
        xdg-open "$file"
    elif [ -n "$EDITOR" ]; then
        $EDITOR "$file"
    elif command -v nano &>/dev/null; then
        nano "$file"
    elif command -v vim &>/dev/null; then
        vim "$file"
    elif command -v vi &>/dev/null; then
        vi "$file"
    else
        echo ""
        warn "未能自动打开编辑器，请手动编辑: $file"
        echo ""
    fi
}

# ── 检测 Python ──
find_python() {
    if command -v python3 &>/dev/null; then
        local ver
        ver=$(python3 --version 2>&1)
        if echo "$ver" | grep -q "Python 3"; then
            echo "python3"
            return 0
        fi
    fi
    if command -v python &>/dev/null; then
        local ver
        ver=$(python --version 2>&1)
        if echo "$ver" | grep -q "Python 3"; then
            echo "python"
            return 0
        fi
    fi
    echo ""
    return 1
}

# ═══════════════════════════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════════════════════════

# ── 切换到脚本所在目录 ──
cd "$(dirname "$0")" || {
    echo "❌ 无法切换到脚本所在目录"
    exit 1
}

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║    🧠  Leader Agent                     ║"
echo "║    AI 智能助手系统                      ║"
echo "║    macOS / Linux 一键安装启动器         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ──────────────────────────
#  第 1 步：检查 Python
# ──────────────────────────
title "[1/4] 🔍 检查 Python 环境..."

PYTHON_CMD=$(find_python)
if [ -z "$PYTHON_CMD" ]; then
    echo ""
    err "未检测到 Python 3！"
    echo ""
    info "请先安装 Python 3.9 或更高版本:"
    info "  macOS: https://www.python.org/downloads/"
    info "  Linux: sudo apt install python3 python3-pip"
    echo ""
    exit 1
fi

PY_VERSION=$($PYTHON_CMD --version 2>&1)
ok "已检测到" "${PY_VERSION}"
echo ""

# ──────────────────────────
#  第 2 步：安装依赖
# ──────────────────────────
title "[2/4] 📦 安装依赖..."

if [ -f "AgentSkills/requirements.txt" ]; then
    # 检查是否已安装
    if $PYTHON_CMD -c "import openai" &>/dev/null; then
        ok "依赖已就绪" ""
    else
        info "正在安装依赖（首次安装需要一些时间）..."
        echo ""
        $PYTHON_CMD -m pip install -r AgentSkills/requirements.txt --break-system-packages
        if [ $? -ne 0 ]; then
            echo ""
            err "依赖安装失败！"
            info "请手动运行: $PYTHON_CMD -m pip install -r AgentSkills/requirements.txt"
            echo ""
            exit 1
        fi
        echo ""
        ok "依赖安装完成" ""
    fi
else
    warn "未找到 AgentSkills/requirements.txt"
fi
echo ""

# ──────────────────────────
#  第 3 步：配置 .env
# ──────────────────────────
title "[3/4] 🔑 配置 API 密钥..."

# 检查 .env 是否存在
if [ ! -f ".env" ]; then
    echo ""
    warn "未找到 .env 配置文件"
    echo ""
    if [ -f ".env.example" ]; then
        info "正在从 .env.example 创建配置模板..."
        cp ".env.example" ".env"
    else
        info "正在创建配置模板..."
        {
            echo "# 🔑 请在此配置您的 DeepSeek API 密钥"
            echo "# 申请地址: https://platform.deepseek.com/"
            echo "DEEPSEEK_API_KEY=your_api_key_here"
        } > .env
    fi
    ok "模板文件已创建" ""
    echo ""
    info "🔑 请编辑 .env 文件，填入您的 DeepSeek API Key"
    echo ""
    info "如何获取？"
    info "  1. 打开 https://platform.deepseek.com/"
    info "  2. 注册 → 登录 → API Keys → 创建新 Key"
    info "  3. 复制 sk- 开头的密钥"
    echo ""
    printf "  ⏎ 按 Enter 键打开编辑器..."
    read -r
    open_file ".env"
    echo ""
    warn "编辑完成后请重新运行本脚本"
    echo ""
    exit 0
fi

ok "配置文件存在" ""

# 验证 API Key
info "正在验证 API Key..."

API_KEY=$($PYTHON_CMD -c "
import os, sys
try:
    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv('DEEPSEEK_API_KEY', '')
    sys.exit(0 if key and key != 'your_api_key_here' else 1)
except:
    sys.exit(1)
" 2>/dev/null)

if [ $? -ne 0 ]; then
    # 后备检查：直接用 grep
    if grep -q "DEEPSEEK_API_KEY=" .env 2>/dev/null && ! grep -q "your_api_key_here" .env 2>/dev/null; then
        :  # Key 看起来有效
    else
        echo ""
        warn "API Key 未配置或使用了模板值！"
        echo ""
        info "请编辑 .env 文件，填入您的真实 API Key"
        echo ""
        printf "  ⏎ 按 Enter 键打开编辑器..."
        read -r
        open_file ".env"
        echo ""
        warn "编辑完成后请重新运行本脚本"
        echo ""
        exit 0
    fi
fi

ok "API Key 验证通过" ""
echo ""

# ──────────────────────────
#  第 4 步：启动程序
# ──────────────────────────
title "[4/4] 🚀 启动程序..."
echo ""
echo "═══════════════════════════════════════════╗"
echo "  所有检查通过，即将进入交互界面！"
echo "╚══════════════════════════════════════════╝"
echo ""
info "使用提示："
info "  • 直接输入问题，AI 会自动处理"
info "  • 输入 /help 查看帮助"
info "  • 输入 /exit 退出程序"
info "  • 按 Ctrl+C 中断当前任务"
echo ""

# ── 使用普通进程启动 CLI，退出后返回终端 ──
$PYTHON_CMD LeaderAgent.py
