#!/bin/bash
# =============================================================================
#  🧠 Leader Agent — 智能 Agent 系统的大脑与统一入口
#  版本: v1.0.0
#  美化版本 — ClaudeCode CLI 风格
# =============================================================================

# ═══════════════════════════════════════════════════════════════════════════
#  颜色定义（ANSI 256色，兼容 macOS Terminal）
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
#  工具函数
# ═══════════════════════════════════════════════════════════════════════════

# 打印带颜色的文本
cecho() {
    local color="$1"
    local message="$2"
    echo -e "${color}${message}${C_RESET}"
}

# 打印带图标的状态消息
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

# 打印分隔线
print_separator() {
    local color="${1:-$C_GRAY}"
    echo -e "${color}  ${SEPARATOR_FULL}${C_RESET}"
}

print_separator_thin() {
    local color="${1:-$C_GRAY}"
    echo -e "${color}  ${SEPARATOR_THIN}${C_RESET}"
}

# ── 进度条 ──
show_progress() {
    local duration="$1"
    local message="$2"
    local width=30
    local i=0
    while [ $i -le $width ]; do
        local pct=$(( i * 100 / width ))
        # 使用 bash 原生方式构建进度条，兼容 macOS（无 seq）
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
#  ASCII Art Logo — 内置艺术字（无需 figlet）
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
    echo -e "  ${C_BRIGHT_CYAN}${C_BOLD}  🧠  Leader Agent${C_RESET}  ${C_GRAY}v1.0.0${C_RESET}"
    echo -e "  ${C_ITALIC}${C_CYAN}  智能 Agent 系统的大脑与统一入口${C_RESET}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
#  欢迎 Banner
# ═══════════════════════════════════════════════════════════════════════════

show_welcome_banner() {
    clear

    # ── 顶部装饰线 ──
    echo -e "${C_GRAY}  ┏${SEPARATOR_FULL}┓${C_RESET}"

    # ── Logo 区域 ──
    show_logo

    # ── 描述区域 ──
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_BRIGHT_WHITE}${C_BOLD}✦  系统概述  ✦${C_RESET}  ${C_GRAY}┃${C_RESET}"
    echo -e "  ${C_GRAY}┃${C_RESET}"
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_BRIGHT_CYAN}🧠${C_RESET} ${C_BOLD}Leader Agent${C_RESET} 是智能 Agent 系统的核心调度引擎，"
    echo -e "  ${C_GRAY}┃${C_RESET}  负责协调多个专业 Agent 协同工作，完成复杂任务。"
    echo -e "  ${C_GRAY}┃${C_RESET}"

    # ── 子 Agent 列表 ──
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_BRIGHT_WHITE}${C_BOLD}📋  可用子 Agent${C_RESET}"
    echo -e "  ${C_GRAY}┃${C_RESET}"
    echo -e "  ${C_GRAY}┃${C_RESET}    ${C_BRIGHT_GREEN}🛠️${C_RESET}  ${C_BOLD}CodingAgent${C_RESET}    ${C_GRAY}—${C_RESET} 编程与代码开发"
    echo -e "  ${C_GRAY}┃${C_RESET}    ${C_BRIGHT_PURPLE}📚${C_RESET}  ${C_BOLD}SkillsManager${C_RESET}  ${C_GRAY}—${C_RESET} 技能管理与学习"
    echo -e "  ${C_GRAY}┃${C_RESET}    ${C_BRIGHT_BLUE}🔍${C_RESET}  ${C_BOLD}SearchingAgent${C_RESET} ${C_GRAY}—${C_RESET} 联网搜索与信息获取"
    echo -e "  ${C_GRAY}┃${C_RESET}    ${C_BRIGHT_YELLOW}✏️${C_RESET}  ${C_BOLD}ModifyAgent${C_RESET}    ${C_GRAY}—${C_RESET} 内容优化与修改"
    echo -e "  ${C_GRAY}┃${C_RESET}    ${C_CYAN}🌤️${C_RESET}  ${C_BOLD}WeatherAgent${C_RESET}   ${C_GRAY}—${C_RESET} 天气查询与预报"
    echo -e "  ${C_GRAY}┃${C_RESET}"

    # ── 底部装饰线 ──
    echo -e "  ${C_GRAY}┗${SEPARATOR_FULL}┛${C_RESET}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
#  启动流程
# ═══════════════════════════════════════════════════════════════════════════

# 切换到脚本所在目录
cd "$(dirname "$0")"

# ── 显示欢迎界面 ──
show_welcome_banner

# ── 启动初始化 ──
echo -e "  ${C_BRIGHT_CYAN}${C_BOLD}⚡ 正在初始化系统...${C_RESET}"
echo ""

# ── 检查 Python 环境 ──
PYTHON_CMD="python3"
print_thinking "检测 Python 环境..."

if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD="python"
fi

if ! command -v $PYTHON_CMD &> /dev/null; then
    echo ""
    print_separator
    print_error "未找到 Python，请安装 Python 3.8+"
    echo ""
    print_info "下载地址: https://www.python.org/downloads/"
    echo ""
    print_separator
    echo ""
    echo -e "  ${C_GRAY}按 Enter 键退出...${C_RESET}"
    read
    exit 1
fi

PY_VERSION=$($PYTHON_CMD --version 2>&1)
print_success "Python 环境检测通过" "${C_GRAY}${PY_VERSION}${C_RESET}"

# ── 检测并激活项目的虚拟环境 ──
VENV_DIR="$(dirname "$0")/.venv"
if [ -d "$VENV_DIR" ]; then
    print_thinking "正在激活虚拟环境..."
    # 激活虚拟环境
    source "$VENV_DIR/bin/activate"
    # 更新 Python 命令为虚拟环境中的 Python
    PYTHON_CMD="python3"
    # 确认 openai 模块可用
    python3 -c "import openai" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "虚拟环境已激活，依赖检查通过"
    else
        echo ""
        print_warning "虚拟环境存在但缺少 openai 模块，正在安装..."
        pip install openai python-dotenv 2>/dev/null
        if [ $? -eq 0 ]; then
            print_success "依赖安装完成"
        else
            print_error "依赖安装失败，请手动安装"
        fi
    fi
else
    echo ""
    print_warning "未找到虚拟环境，尝试使用系统 Python..."
    # 尝试安装依赖
    python3 -c "import openai" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "依赖检查通过"
    else
        print_thinking "正在安装所需依赖（openai, python-dotenv）..."
        pip3 install openai python-dotenv 2>/dev/null
        if [ $? -eq 0 ]; then
            print_success "依赖安装完成"
        else
            print_warning "依赖自动安装失败，LeaderAgent 可能无法正常运行"
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
    echo "# 请在此文件中配置您的 API Key" > .env
    echo "DEEPSEEK_API_KEY=your_api_key_here" >> .env
    echo ""
    print_info "请编辑 .env 文件，填入您的 DeepSeek API Key"
    echo ""
    echo -e "  ${C_GRAY}按 Enter 键打开 .env 文件...${C_RESET}"
    read
    open -t .env 2>/dev/null || nano .env
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
")
if [ "$API_KEY" != "YES" ]; then
    echo ""
    echo -e "  ${C_BRIGHT_YELLOW}╔${SEPARATOR_FULL}╗${C_RESET}"
    echo -e "  ${C_BRIGHT_YELLOW}║${C_RESET}  ${C_BRIGHT_YELLOW}⚠️  DeepSeek API Key 未配置或使用了模板值！${C_RESET}  ${C_BRIGHT_YELLOW}║${C_RESET}"
    echo -e "  ${C_BRIGHT_YELLOW}╚${SEPARATOR_FULL}╝${C_RESET}"
    echo ""
    print_info "请编辑 .env 文件，填入您的 DeepSeek API Key"
    echo ""
    echo -e "  ${C_GRAY}按 Enter 键打开 .env 文件进行编辑...${C_RESET}"
    read
    open -t .env 2>/dev/null || nano .env
    exit 0
fi
print_success "API Key 验证通过"

# ── 所有检查通过，准备启动 ──
echo ""
print_separator
echo ""

# ── 显示启动动画 ──
echo -e "  ${C_BRIGHT_CYAN}${C_BOLD}🚀 正在启动 Leader Agent...${C_RESET}"
echo ""
show_progress 0.03 "初始化子系统"
echo ""

# ── 启动前最终提示 ──
echo -e "  ${C_GRAY}┌${SEPARATOR_THIN}┐${C_RESET}"
echo -e "  ${C_GRAY}│${C_RESET}  ${C_BRIGHT_GREEN}${C_BOLD}✓ 所有检查通过，即将进入交互界面${C_RESET}  ${C_GRAY}│${C_RESET}"
echo -e "  ${C_GRAY}│${C_RESET}  ${C_CYAN}${C_BOLD}🚀 Leader >${C_RESET} ${C_GRAY}输入您的指令开始工作...${C_RESET}  ${C_GRAY}│${C_RESET}"
echo -e "  ${C_GRAY}└${SEPARATOR_THIN}┘${C_RESET}"
echo ""

# ── 运行 LeaderAgent ──
$PYTHON_CMD LeaderAgent.py

# ═══════════════════════════════════════════════════════════════════════════
#  退出界面
# ═══════════════════════════════════════════════════════════════════════════

EXIT_CODE=$?
echo ""
echo -e "  ${C_GRAY}┏${SEPARATOR_FULL}┓${C_RESET}"
if [ $EXIT_CODE -ne 0 ]; then
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_BRIGHT_RED}${C_BOLD}❌  Leader Agent 异常退出${C_RESET}  ${C_GRAY}(exit code: ${EXIT_CODE})${C_RESET}  ${C_GRAY}┃${C_RESET}"
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_RED}请检查上方错误信息后重试${C_RESET}  ${C_GRAY}┃${C_RESET}"
else
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_BRIGHT_GREEN}${C_BOLD}✅  Leader Agent 已优雅退出${C_RESET}  ${C_GRAY}┃${C_RESET}"
    echo -e "  ${C_GRAY}┃${C_RESET}  ${C_GREEN}感谢使用，期待下次为您服务！${C_RESET}  ${C_GRAY}┃${C_RESET}"
fi
echo -e "  ${C_GRAY}┗${SEPARATOR_FULL}┛${C_RESET}"
echo ""
echo -e "  ${C_GRAY}按 Enter 键关闭此窗口...${C_RESET}"
read
