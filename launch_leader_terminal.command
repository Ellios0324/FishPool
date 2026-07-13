#!/usr/bin/env bash
# =============================================================================
#  🧠 FishPool — 跨平台启动脚本
#  版本: v2.0.0（跨平台兼容版）
#
#  🌐 支持的操作系统：
#     🍎 macOS   — 双击 .command 文件，或终端运行
#     🐧 Linux   — 终端运行: bash launch_leader_terminal.command
#     🪟 Windows — 使用 Git Bash 运行: bash launch_leader_terminal.command
#                  或双击 launch_leader_terminal.bat（推荐！）
#
#  📌 本脚本特点：
#     ✅ 自动检测操作系统，适配命令差异
#     ✅ 跨平台清屏（clear / cls / ANSI 转义码）
#     ✅ 跨平台打开文件编辑器（open / xdg-open / notepad / nano / vim）
#     ✅ 跨平台 Python 检测（python3 / python）
#     ✅ 跨平台虚拟环境激活（bin/activate / Scripts/activate）
#     ✅ ANSI 颜色兼容（自动检测终端支持）
#
#  💡 如果双击后只是闪一下：
#     macOS:  右键 → 打开方式 → 终端
#     Windows: 请使用 launch_leader_terminal.bat（双击即可）
# =============================================================================

# ── 安全选项 ──
set -o pipefail

# ═══════════════════════════════════════════════════════════════════════════
#  颜色定义（ANSI 256色，兼容 macOS/Linux/Windows 终端）
# ═══════════════════════════════════════════════════════════════════════════
C_RESET="\033[0m"

# 常规色
C_BLACK="\033[0;30m"
C_RED="\033[0;31m"
C_GREEN="\033[0;32m"
C_YELLOW="\033[0;33m"
C_BLUE="\033[0;34m"
C_PURPLE="\033[0;35m"
C_CYAN="\033[0;36m"
C_WHITE="\033[0;37m"
C_GRAY="\033[0;90m"

# 亮色
C_BRIGHT_RED="\033[1;31m"
C_BRIGHT_GREEN="\033[1;32m"
C_BRIGHT_YELLOW="\033[1;33m"
C_BRIGHT_BLUE="\033[1;34m"
C_BRIGHT_PURPLE="\033[1;35m"
C_BRIGHT_CYAN="\033[1;36m"
C_BRIGHT_WHITE="\033[1;37m"

# 背景色
C_BG_RED="\033[41m"
C_BG_GREEN="\033[42m"
C_BG_YELLOW="\033[43m"
C_BG_BLUE="\033[44m"
C_BG_PURPLE="\033[45m"
C_BG_CYAN="\033[46m"
C_BG_DARK="\033[48;5;236m"
C_BG_DARKER="\033[48;5;234m"

# 样式
C_BOLD="\033[1m"
C_DIM="\033[2m"
C_ITALIC="\033[3m"
C_UNDERLINE="\033[4m"

# ═══════════════════════════════════════════════════════════════════════════
#  分隔线与装饰常量
# ═══════════════════════════════════════════════════════════════════════════
SEPARATOR_FULL="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
SEPARATOR_THIN="╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌"
SEPARATOR_DOTS="⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯"

# ═══════════════════════════════════════════════════════════════════════════
#  跨平台工具函数
# ═══════════════════════════════════════════════════════════════════════════

# ── 跨平台清屏 ──
# 在 macOS/Linux 上使用 clear，Windows 上使用 cls，都不行用 ANSI 转义码
clear_screen() {
    if command -v clear &>/dev/null; then
        clear
    elif command -v cls &>/dev/null; then
        cls
    else
        printf "\033[2J\033[H"
    fi
}

# ── 跨平台打开文件编辑器 ──
# 按优先级尝试：open (macOS) → xdg-open (Linux) → notepad (Windows) → $EDITOR → nano → vim → vi
open_file() {
    local file="$1"
    if command -v open &>/dev/null; then
        # macOS: 使用默认文本编辑器打开
        open -t "$file"
    elif command -v xdg-open &>/dev/null; then
        # Linux 桌面环境
        xdg-open "$file"
    elif command -v notepad &>/dev/null; then
        # Windows (Git Bash / WSL)
        notepad "$file"
    elif [ -n "$EDITOR" ]; then
        # 用户自定义编辑器
        $EDITOR "$file"
    elif command -v nano &>/dev/null; then
        nano "$file"
    elif command -v vim &>/dev/null; then
        vim "$file"
    elif command -v vi &>/dev/null; then
        vi "$file"
    else
        echo ""
        echo "  ⚠️  未能自动打开文本编辑器"
        echo "  请手动用文本编辑器打开以下文件："
        echo "  $file"
        echo ""
    fi
}

# ── 跨平台检测 Python ──
# macOS/Linux: python3 优先；Windows: python 优先（且通常就是 Python 3）
find_python() {
    # 先检测 python3
    if command -v python3 &>/dev/null; then
        # 确认 python3 确实是 Python 3
        local ver
        ver=$(python3 --version 2>&1)
        if echo "$ver" | grep -q "Python 3"; then
            echo "python3"
            return 0
        fi
    fi

    # 再检测 python
    if command -v python &>/dev/null; then
        local ver
        ver=$(python --version 2>&1)
        if echo "$ver" | grep -q "Python 3"; then
            echo "python"
            return 0
        fi
    fi

    # 都没找到
    echo ""
    return 1
}

# ── 跨平台检测 pip ──
find_pip() {
    local python_cmd="$1"
    # 优先用 python -m pip（最可靠，跨平台）
    if "$python_cmd" -m pip --version &>/dev/null; then
        echo "$python_cmd -m pip"
        return 0
    fi
    # 再试 pip3
    if command -v pip3 &>/dev/null; then
        echo "pip3"
        return 0
    fi
    # 再试 pip
    if command -v pip &>/dev/null; then
        echo "pip"
        return 0
    fi
    echo ""
    return 1
}

# ── 跨平台检测操作系统名称（用于显示） ──
detect_os() {
    case "$(uname -s)" in
        Darwin*)  echo "macOS" ;;
        Linux*)   echo "Linux" ;;
        MINGW*|MSYS*|CYGWIN*) echo "Windows" ;;
        *)        echo "Unknown" ;;
    esac
}

# ── 打印带颜色的文本 ──
cecho() {
    local color="$1"
    local message="$2"
    echo -e "${color}${message}${C_RESET}"
}

# ── 打印带图标的状态消息 ──
print_success() {
    echo -e "  ${C_BRIGHT_GREEN}✅${C_RESET} ${C_WHITE}$1${C_RESET} ${C_GREEN}$2${C_RESET}"
}

print_error() {
    echo -e "  ${C_BRIGHT_RED}❌${C_RESET} ${C_BRIGHT_WHITE}$1${C_RESET}"
}

print_warning() {
    echo -e "  ${C_BRIGHT_YELLOW}⚠️${C_RESET} ${C_BRIGHT_WHITE}$1${C_RESET}"
}

print_info() {
    echo -e "  ${C_BRIGHT_BLUE}ℹ️${C_RESET} ${C_WHITE}$1${C_RESET}"
}

print_thinking() {
    echo -e "  ${C_BRIGHT_PURPLE}🤔${C_RESET} ${C_ITALIC}${C_GRAY}$1${C_RESET}"
}

# ── 打印分隔线 ──
print_separator() {
    local color="${1:-$C_GRAY}"
    echo -e "${color}  ${SEPARATOR_FULL}${C_RESET}"
}

print_separator_thin() {
    local color="${1:-$C_GRAY}"
    echo -e "${color}  ${SEPARATOR_THIN}${C_RESET}"
}

# ── 进度条（纯 bash 实现，不依赖 seq，兼容 macOS） ──
show_progress() {
    local duration="$1"
    local message="$2"
    local width=30
    local i=0
    while [ $i -le $width ]; do
        local pct=$(( i * 100 / width ))
        local filled=""
        local empty=""
        local j=0
        while [ $j -lt $i ]; do
            filled="${filled}█"
            j=$(( j + 1 ))
        done
        local k=0
        while [ $k -lt $(( width - i )) ]; do
            empty="${empty}░"
            k=$(( k + 1 ))
        done
        printf "\r  ${C_BRIGHT_CYAN}${message}${C_RESET} ${C_CYAN}[${filled}${empty}]${C_RESET} ${C_BRIGHT_WHITE}%3d%%${C_RESET}" $pct
        sleep "$duration"
        i=$(( i + 1 ))
    done
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
#  ASCII Art Logo
# ═══════════════════════════════════════════════════════════════════════════

show_logo() {
    echo ""
    echo -e "${C_BRIGHT_CYAN}${C_BOLD}"
    echo '    ╔═╗╔═╦╗─╔╦═══╦═══╦═══╗     ╔═╗╔═╦╗─╔╦═══╦═══╦═══╗'
    echo '    ║║╚╝║║║─║║╔══╣╔══╣╔═╗║     ║║╚╝║║║─║║╔══╣╔══╣╔═╗║'
    echo '    ║╔╗╔╗║║║─║║╚══╣╚══╣╚═╝║     ║╔╗╔╗║║║─║║╚══╣╚══╣╚═╝║'
    echo '    ║║║║║║║║─║║╔══╣╔══╣╔╗╔╝     ║║║║║║║║─║║╔══╣╔══╣╔╗╔╝'
    echo '    ║║║║║║║╚═╝║╚══╣╚══╣║║╚╗     ║║║║║║║╚═╝║╚══╣╚══╣║║╚╗'
    echo '    ╚╝╚╝╚╝╚═══╩═══╩═══╩╝╚═╝     ╚╝╚╝╚╝╚═══╩═══╩═══╩╝╚═╝'
    echo -e "${C_RESET}"
    echo -e "  ${C_BRIGHT_CYAN}${C_BOLD}  🧠  FishPool${C_RESET}  ${C_GRAY}v2.0.0${C_RESET}"
    echo -e "  ${C_ITALIC}${C_CYAN}  智能 Agent 系统的大脑与统一入口${C_RESET}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
#  欢迎 Banner
# ═══════════════════════════════════════════════════════════════════════════

show_welcome_banner() {
    clear_screen

    # ── 顶部装饰线 ──
    echo -e "${C_GRAY}  ┏${SEPARATOR_FULL}┓${C_RESET}"

    # ── Logo 区域 ──
    show_logo

    # ── 检测并显示操作系统信息 ──
    OS_NAME=$(detect_os)
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_DIM}🌐 检测到操作系统: ${C_BRIGHT_WHITE}${OS_NAME}${C_RESET}  ${C_GRAY}┃${C_RESET}"
    echo -e "  ${C_GRAY}┃${C_RESET}"

    # ── 描述区域 ──
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_BRIGHT_WHITE}${C_BOLD}✦  系统概述  ✦${C_RESET}  ${C_GRAY}┃${C_RESET}"
    echo -e "  ${C_GRAY}┃${C_RESET}"
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_BRIGHT_CYAN}🧠${C_RESET} ${C_BOLD}FishPool${C_RESET} 是智能 Agent 系统的核心调度引擎，"
    echo -e "  ${C_GRAY}┃${C_RESET}  负责协调多个专业 Agent 协同工作，完成复杂任务。"
    echo -e "  ${C_GRAY}┃${C_RESET}"

    # ── 子 Agent 列表 ──
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_BRIGHT_WHITE}${C_BOLD}📋  可用子 Agent${C_RESET}"
    echo -e "  ${C_GRAY}┃${C_RESET}"
    echo -e "  ${C_GRAY}┃${C_RESET}    ${C_BRIGHT_GREEN}🛠️${C_RESET}  ${C_BOLD}KillerWhale${C_RESET}    ${C_GRAY}—${C_RESET} 编程与代码开发"
    echo -e "  ${C_GRAY}┃${C_RESET}    ${C_BRIGHT_PURPLE}📚${C_RESET}  ${C_BOLD}FishFarmer${C_RESET}    ${C_GRAY}—${C_RESET} 技能管理与学习"
    echo -e "  ${C_GRAY}┃${C_RESET}    ${C_BRIGHT_BLUE}🔍${C_RESET}  ${C_BOLD}SearchingAgent${C_RESET} ${C_GRAY}—${C_RESET} 联网搜索与信息获取"
    echo -e "  ${C_GRAY}┃${C_RESET}    ${C_BRIGHT_YELLOW}✏️${C_RESET}  ${C_BOLD}ModifyAgent${C_RESET}    ${C_GRAY}—${C_RESET} 内容优化与修改"
    echo -e "  ${C_GRAY}┃${C_RESET}    ${C_CYAN}🌤️${C_RESET}  ${C_BOLD}Dolphin${C_RESET}      ${C_GRAY}—${C_RESET} 天气查询与预报"
    echo -e "  ${C_GRAY}┃${C_RESET}"

    # ── 底部装饰线 ──
    echo -e "  ${C_GRAY}┗${SEPARATOR_FULL}┛${C_RESET}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
#  启动流程
# ═══════════════════════════════════════════════════════════════════════════

# ── 切换到脚本所在目录（跨平台兼容） ──
cd "$(dirname "$0")" || {
    echo "❌ 无法切换到脚本所在目录"
    exit 1
}

# ── 显示欢迎界面 ──
show_welcome_banner

# ── 启动初始化 ──
echo -e "  ${C_BRIGHT_CYAN}${C_BOLD}⚡ 正在初始化系统...${C_RESET}"
echo ""

# ── 检测操作系统 ──
OS_NAME=$(detect_os)
echo -e "  ${C_DIM}🌐 操作系统: ${C_BRIGHT_WHITE}${OS_NAME}${C_RESET}"
echo ""

# ── 检查 Python 环境（跨平台） ──
print_thinking "检测 Python 环境..."
PYTHON_CMD=$(find_python)

if [ -z "$PYTHON_CMD" ]; then
    echo ""
    print_separator
    print_error "未找到 Python，请安装 Python 3.9 或更高版本"
    echo ""
    print_info "下载地址: https://www.python.org/downloads/"
    echo ""
    print_info "💡 Windows 用户安装时请务必勾选 'Add Python to PATH'"
    echo ""
    print_separator
    echo ""
    echo -e "  ${C_GRAY}按 Enter 键退出...${C_RESET}"
    read -r
    exit 1
fi

PY_VERSION=$($PYTHON_CMD --version 2>&1)
print_success "Python 环境检测通过" "${C_GRAY}${PY_VERSION}${C_RESET}"

# ── 检测并激活虚拟环境（跨平台路径） ──
SCRIPT_DIR="$(dirname "$0")"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ -d "$VENV_DIR" ]; then
    print_thinking "正在激活虚拟环境..."

    # 跨平台判断虚拟环境激活脚本路径
    if [ -f "$VENV_DIR/bin/activate" ]; then
        # macOS / Linux
        source "$VENV_DIR/bin/activate"
    elif [ -f "$VENV_DIR/Scripts/activate" ]; then
        # Windows (Git Bash / WSL)
        source "$VENV_DIR/Scripts/activate"
    else
        print_warning "未找到虚拟环境激活脚本，跳过激活"
    fi

    # 更新 Python 命令为虚拟环境中的 Python
    if [ -f "$VENV_DIR/bin/python3" ]; then
        PYTHON_CMD="$VENV_DIR/bin/python3"
    elif [ -f "$VENV_DIR/Scripts/python.exe" ]; then
        PYTHON_CMD="$VENV_DIR/Scripts/python.exe"
    fi

    # 检查 openai 模块是否可用
    $PYTHON_CMD -c "import openai" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "虚拟环境已激活，依赖检查通过"
    else
        echo ""
        print_warning "虚拟环境存在但缺少依赖，正在安装..."
        $PYTHON_CMD -m pip install -r "$SCRIPT_DIR/AgentSkills/requirements.txt" 2>/dev/null
        if [ $? -eq 0 ]; then
            print_success "依赖安装完成"
        else
            print_error "依赖安装失败，请手动安装"
        fi
    fi
else
    echo ""
    print_warning "未找到虚拟环境，使用系统 Python..."

    # 检查依赖
    $PYTHON_CMD -c "import openai" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "依赖检查通过"
    else
        print_thinking "正在安装所需依赖..."
        PIP_CMD=$(find_pip "$PYTHON_CMD")
        if [ -n "$PIP_CMD" ]; then
            $PIP_CMD install -r "$SCRIPT_DIR/AgentSkills/requirements.txt" 2>/dev/null
            if [ $? -eq 0 ]; then
                print_success "依赖安装完成"
            else
                print_warning "依赖自动安装失败，FishPool 可能无法正常运行"
                print_info "请手动执行: $PIP_CMD install -r AgentSkills/requirements.txt"
            fi
        else
            print_warning "未找到 pip，请手动安装依赖"
        fi
    fi
fi

# ── 检查 .env 文件 ──
echo ""
print_separator_thin
echo ""
print_thinking "检查配置文件..."

if [ ! -f ".env" ]; then
    echo ""
    print_warning "未找到 .env 文件，正在创建模板..."
    cp .env.example .env 2>/dev/null || {
        echo "# 🔑 请在此配置您的 DeepSeek API 密钥" > .env
        echo "# 申请地址: https://platform.deepseek.com/" >> .env
        echo "DEEPSEEK_API_KEY=your_api_key_here" >> .env
    }
    echo ""
    print_info "请编辑 .env 文件，填入您的 DeepSeek API Key"
    echo ""
    echo -e "  ${C_GRAY}按 Enter 键打开 .env 文件进行编辑...${C_RESET}"
    read -r
    open_file ".env"
    # 编辑后重新检查
    if grep -q "your_api_key_here" .env 2>/dev/null; then
        print_warning "您尚未修改 API Key，请编辑 .env 文件后重新运行"
        exit 0
    fi
    exit 0
fi
print_success "配置文件存在"

# ── 检查 API Key 是否已配置 ──
print_thinking "验证 API Key 配置..."
API_KEY=$($PYTHON_CMD -c "
import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv('DEEPSEEK_API_KEY', '')
print('YES' if key and key != 'your_api_key_here' else 'NO')
" 2>/dev/null)

# 如果 Python 检测失败，用 grep 做简单检查
if [ $? -ne 0 ] || [ "$API_KEY" != "YES" ]; then
    # 用 grep 做后备检查
    if grep -q "DEEPSEEK_API_KEY=" .env 2>/dev/null && ! grep -q "your_api_key_here" .env 2>/dev/null; then
        API_KEY="YES"
    fi
fi

if [ "$API_KEY" != "YES" ]; then
    echo ""
    echo -e "  ${C_BRIGHT_YELLOW}╔${SEPARATOR_FULL}╗${C_RESET}"
    echo -e "  ${C_BRIGHT_YELLOW}║${C_RESET}  ${C_BRIGHT_YELLOW}⚠️  DeepSeek API Key 未配置或使用了模板值！${C_RESET}  ${C_BRIGHT_YELLOW}║${C_RESET}"
    echo -e "  ${C_BRIGHT_YELLOW}╚${SEPARATOR_FULL}╝${C_RESET}"
    echo ""
    print_info "请编辑 .env 文件，填入您的 DeepSeek API Key"
    echo ""
    echo -e "  ${C_GRAY}按 Enter 键打开 .env 文件进行编辑...${C_RESET}"
    read -r
    open_file ".env"
    echo ""
    echo -e "  ${C_GRAY}编辑完成后请重新运行本程序${C_RESET}"
    exit 0
fi
print_success "API Key 验证通过"

# ── 所有检查通过，准备启动 ──
echo ""
print_separator
echo ""

# ── 显示启动动画 ──
echo -e "  ${C_BRIGHT_CYAN}${C_BOLD}🚀 正在启动 FishPool...${C_RESET}"
echo ""
show_progress 0.03 "初始化子系统"
echo ""

# ── 启动前最终提示 ──
echo -e "  ${C_GRAY}┌${SEPARATOR_THIN}┐${C_RESET}"
echo -e "  ${C_GRAY}│${C_RESET}  ${C_BRIGHT_GREEN}${C_BOLD}✓ 所有检查通过，即将进入交互界面${C_RESET}  ${C_GRAY}│${C_RESET}"
echo -e "  ${C_GRAY}│${C_RESET}  ${C_CYAN}${C_BOLD}🚀 FishPool >${C_RESET} ${C_GRAY}输入您的指令开始工作...${C_RESET}  ${C_GRAY}│${C_RESET}"
echo -e "  ${C_GRAY}└${SEPARATOR_THIN}┘${C_RESET}"
echo ""

# ── 运行 FishPool（跨平台） ──
$PYTHON_CMD LeaderAgent.py

# ═══════════════════════════════════════════════════════════════════════════
#  退出界面
# ═══════════════════════════════════════════════════════════════════════════

EXIT_CODE=$?
echo ""
echo -e "  ${C_GRAY}┏${SEPARATOR_FULL}┓${C_RESET}"
if [ $EXIT_CODE -ne 0 ]; then
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_BRIGHT_RED}${C_BOLD}❌  FishPool 异常退出${C_RESET}  ${C_GRAY}(exit code: ${EXIT_CODE})${C_RESET}  ${C_GRAY}┃${C_RESET}"
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_RED}请检查上方错误信息后重试${C_RESET}  ${C_GRAY}┃${C_RESET}"
else
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_BRIGHT_GREEN}${C_BOLD}✅  FishPool 已优雅退出${C_RESET}  ${C_GRAY}┃${C_RESET}"
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_GREEN}感谢使用，期待下次为您服务！${C_RESET}  ${C_GRAY}┃${C_RESET}"
fi
echo -e "  ${C_GRAY}┗${SEPARATOR_FULL}┛${C_RESET}"
echo ""
echo -e "  ${C_GRAY}按 Enter 键关闭此窗口...${C_RESET}"
read -r
