#!/usr/bin/env python3
"""
launch_leader_terminal.py — 🚀 LeaderAgent 交互式终端启动器

一个跨平台的交互式菜单启动器，基于 cli_style 模块的美化风格，
提供多种启动选项，让用户可以选择启动 LeaderAgent 或直接进入某个子 Agent。

✅ 中文输入修复：使用 cli_input 模块替代原生 input()，
   解决退格键需按两次、方向键导航异常等中文输入问题。

⌨️ Ctrl+C 行为：
   - 在菜单等待输入时按 Ctrl+C → 退出程序
   - 在 Agent 执行过程中按 Ctrl+C → 中断当前 Agent 任务

使用方法：
    python launch_leader_terminal.py          # 交互式菜单
    python launch_leader_terminal.py --direct  # 直接启动 LeaderAgent（跳过菜单）
    python launch_leader_terminal.py --agent CodingAgent  # 直接启动指定子 Agent

支持的子 Agent 直连：
    1. CodingAgent     — 编程任务
    2. SkillsManager   — 技能管理
    3. SearchingAgent  — 联网搜索
    4. ModifyAgent     — 内容优化
    5. WeatherAgent    — 天气查询
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Optional

# ── 将项目根目录加入 Python 路径 ──
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── 导入中文友好的输入模块 ──
try:
    from cli_input import chinese_input, ExitRequested, HAVE_PROMPT_TOOLKIT
    HAVE_CLI_INPUT = True
except ImportError:
    HAVE_CLI_INPUT = False
    # 回退到原生 input
    def chinese_input(prompt="", **kwargs):
        try:
            return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            # 兼容：退出程序
            sys.exit(0)

    class ExitRequested(BaseException):
        pass

# 尝试导入 cli_style，如果失败则使用内置回退
try:
    from cli_style import (
        Color, cprint, get_term_width, format_timestamp,
        print_panel, print_banner, print_tool_result,
        print_user_input, print_agent_start, print_agent_end,
        print_welcome, print_goodbye,
        print_help, print_separator, print_status,
    )
    HAVE_CLI_STYLE = True
except ImportError:
    HAVE_CLI_STYLE = False
    # ── 回退：简化的颜色支持 ──
    class Color:
        RST = '\033[0m'
        BLD = '\033[1m'
        DIM = '\033[2m'
        RED = '\033[31m'
        GRN = '\033[32m'
        YEL = '\033[33m'
        BLU = '\033[34m'
        MAG = '\033[35m'
        CYN = '\033[36m'
        BRED = '\033[91m'
        BGRN = '\033[92m'
        BYEL = '\033[93m'
        BBLU = '\033[94m'
        BMAG = '\033[95m'
        BCYN = '\033[96m'
        BWHT = '\033[97m'
        USER = CYN
        AGENT = BYEL
        TOOL = BMAG
        SYS = BBLU
        OK = BGRN
        ERR = BRED
        WARN = BYEL
        INFO = BBLU
        TITLE = BCYN
        HINT = DIM
        SEP = DIM

    def cprint(text, color="", end="\n", bold=False, reset=True):
        prefix = (Color.BLD if bold else "") + color
        suffix = Color.RST if reset else ""
        print(f"{prefix}{text}{suffix}", end=end)

    def get_term_width():
        try:
            import shutil
            return shutil.get_terminal_size().columns
        except Exception:
            return 80

    def format_timestamp():
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def print_panel(content, title="", color="", width=None, border_style="rounded"):
        if width is None:
            width = min(get_term_width() - 2, 100)
        width = max(width, 40)
        if border_style == "rounded":
            tl, tr, bl, br = "╭", "╮", "╰", "╯"
        else:
            tl, tr, bl, br = "┌", "┐", "└", "┘"
        h = "─"
        v = "│"
        if title:
            title_str = f" {title} "
            left_fill = h * 2
            right_fill = h * (width - len(title_str) - len(left_fill) - 2)
            header = f"{tl}{left_fill}{title_str}{right_fill}{tr}"
        else:
            header = f"{tl}{h * (width - 2)}{tr}"
        footer = f"{bl}{h * (width - 2)}{br}"
        rst = Color.RST
        clr = color if color else ""
        print(f"{clr}{header}{rst}")
        for line in content.split("\n"):
            visible = line
            padding = max(0, width - 2 - len(visible))
            print(f"{clr}{v}{rst} {line}{' ' * padding}{clr}{v}{rst}")
        print(f"{clr}{footer}{rst}")

    def print_banner(text, color="", char="═", width=None):
        if width is None:
            width = min(get_term_width(), 80)
        line = char * width
        rst = Color.RST
        clr = color if color else ""
        centered = text.center(width)
        print(f"{clr}{line}{rst}")
        print(f"{clr}{centered}{rst}")
        print(f"{clr}{line}{rst}")

    def print_welcome(title, subtitle="", model="", tool_count=0, extra_info=None):
        print()
        print_panel(
            content=f"  {Color.BLD}{Color.BCYN}{title}{Color.RST}",
            title="🚀 LeaderAgent",
            color=Color.SYS,
        )
        print()

    def print_goodbye(message="🌟 感谢使用，期待再次相见！"):
        print()
        print_panel(content=f"  {Color.BLD}{Color.BCYN}  {message}{Color.RST}", title="👋 再见", color=Color.SYS)
        print()

    def print_status(message, status="info"):
        icons = {"info": "ℹ️", "ok": "✅", "error": "❌", "warning": "⚠️"}
        colors = {"info": Color.INFO, "ok": Color.OK, "error": Color.ERR, "warning": Color.WARN}
        icon = icons.get(status, "ℹ️")
        color = colors.get(status, Color.INFO)
        print(f"  {color}{icon} {message}{Color.RST}")

    def print_separator(char="━", color=""):
        width = get_term_width()
        clr = color if color else Color.SEP
        print(f"{clr}{char * max(width, 20)}{Color.RST}")

    def print_user_input(user_input):
        print(f"\n  {Color.CYN}{Color.BLD}💬 You:{Color.RST} {Color.CYN}{user_input}{Color.RST}\n")

    def print_agent_start(agent_name="Agent", timestamp=""):
        ts = timestamp or format_timestamp()
        print(f"\n  {Color.BYEL}{Color.BLD}🤖 {agent_name} @ {ts}{Color.RST}")

    def print_agent_end():
        print()


# ═══════════════════════════════════════════════════════════════════════
# Agent 路径配置
# ═══════════════════════════════════════════════════════════════════════

AGENTS = {
    "1": {
        "name": "LeaderAgent",
        "file": "LeaderAgent.py",
        "description": "🚀 启动交互模式（完整 CLI 对话）",
        "icon": "🚀",
        "color": Color.BCYN,
        "direct": True,
    },
    "2": {
        "name": "CodingAgent",
        "file": "CodingAgent.py",
        "description": "💻 编程任务（代码编写/修改/检查/项目创建）",
        "icon": "💻",
        "color": Color.BGRN,
        "direct": True,
    },
    "3": {
        "name": "SkillsManager",
        "file": "SkillsManager.py",
        "description": "🔧 技能管理（查看/创建/修改/删除/测试）",
        "icon": "🔧",
        "color": Color.BMAG,
        "direct": True,
    },
    "4": {
        "name": "SearchingAgent",
        "file": "SearchingAgent.py",
        "description": "🔍 联网搜索（资讯/资料/调研/整理归纳总结）",
        "icon": "🔍",
        "color": Color.BBLU,
        "direct": True,
    },
    "5": {
        "name": "ModifyAgent",
        "file": "ModifyAgent.py",
        "description": "🎨 内容优化（7受众 × 10格式 × 5语言）",
        "icon": "🎨",
        "color": Color.BYEL,
        "direct": True,
    },
    "6": {
        "name": "WeatherAgent",
        "file": "WeatherAgent.py",
        "description": "🌤️ 天气查询（预报/穿衣建议/生活小提示）",
        "icon": "🌤️",
        "color": Color.BCYN,
        "direct": True,
    },
}

EXIT_KEYS = {"0", "exit", "quit", "q", "退出", "离开"}
HELP_KEYS = {"help", "h", "/help", "？"}


# ═══════════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════════

def clear_screen():
    """清屏（跨平台）"""
    os.system('cls' if os.name == 'nt' else 'clear')


def find_python() -> str:
    """查找系统中可用的 Python 解释器"""
    for cmd in ["python3", "python"]:
        try:
            result = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and "Python 3" in result.stdout:
                return cmd
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return "python3"  # 默认返回 python3，让系统决定


def check_agent_file(agent_info: dict) -> bool:
    """检查 Agent 文件是否存在"""
    agent_path = PROJECT_ROOT / agent_info["file"]
    return agent_path.exists()


def check_env_file() -> bool:
    """检查 .env 文件是否存在并包含有效的 API Key"""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return False

    # 简单读取 .env 文件检查
    try:
        content = env_path.read_text()
        if "DEEPSEEK_API_KEY" in content and "your_api_key_here" not in content:
            # 检查是否有值
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("DEEPSEEK_API_KEY="):
                    key_value = line.split("=", 1)[1].strip().strip("\"'")
                    if key_value and len(key_value) > 10:
                        return True
        return False
    except Exception:
        return False


def launch_agent(agent_key: str, python_cmd: str) -> None:
    """启动指定的 Agent

    Args:
        agent_key: AGENTS 字典中的键（如 "1", "2"）
        python_cmd: Python 解释器命令
    """
    if agent_key not in AGENTS:
        print_status(f"未知的 Agent 键: {agent_key}", "error")
        return

    agent_info = AGENTS[agent_key]
    agent_file = agent_info["file"]
    agent_name = agent_info["name"]
    agent_path = PROJECT_ROOT / agent_file

    if not agent_path.exists():
        print_status(f"❌ {agent_file} 不存在！", "error")
        print(f"   请确保该文件位于: {PROJECT_ROOT}")
        return

    # ── 显示启动信息 ──
    clear_screen()
    print()
    print_banner(
        text=f"  🚀  正在启动 {agent_name}  ...  ",
        color=agent_info["color"],
        char="═",
    )
    print()
    print(f"  {Color.DIM}📂 工作目录: {PROJECT_ROOT}{Color.RST}")
    print(f"  {Color.DIM}🐍 Python:     {python_cmd}{Color.RST}")
    print(f"  {Color.DIM}📄 脚本:       {agent_file}{Color.RST}")
    print()
    print_separator(char="─", color=Color.DIM)
    print()

    try:
        # 启动子进程（继承当前终端）
        sys.stdout.flush()
        result = subprocess.run(
            [python_cmd, str(agent_path)],
            cwd=PROJECT_ROOT,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )

        print()
        print_separator(char="─", color=Color.DIM)
        print()

        if result.returncode == 0:
            print_status(f"{agent_name} 已正常退出 ✅", "ok")
        else:
            print_status(f"{agent_name} 异常退出 (exit code: {result.returncode})", "error")

    except FileNotFoundError:
        print_status(f"❌ 未找到 Python 解释器: {python_cmd}", "error")
    except PermissionError:
        print_status(f"❌ 权限不足，无法执行 {agent_file}", "error")
        print("   请尝试: chmod +x", agent_file)
    except KeyboardInterrupt:
        print()
        print_status("用户中断操作", "warning")
    except Exception as e:
        print_status(f"❌ 启动失败: {e}", "error")

    print()
    print(f"  {Color.DIM}按 Enter 键返回主菜单...{Color.RST}")
    try:
        chinese_input()  # 使用中文友好的输入
    except ExitRequested:
        print()
        sys.exit(0)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def show_system_info() -> None:
    """显示系统信息和可用的 Agent 状态"""
    width = min(get_term_width() - 2, 80)
    width = max(width, 50)

    python_cmd = find_python()

    # 获取 Python 版本
    python_version = "未知"
    try:
        result = subprocess.run(
            [python_cmd, "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            python_version = result.stdout.strip()
    except Exception:
        pass

    env_ok = check_env_file()

    lines = [
        f"  {Color.BLD}{Color.BCYN}📋 系统信息{Color.RST}",
        f"",
        f"  {Color.BLD}🐍 Python:{Color.RST}    {Color.BCYN}{python_version}{Color.RST}",
        f"  {Color.BLD}📂 工作目录:{Color.RST} {Color.DIM}{PROJECT_ROOT}{Color.RST}",
        f"  {Color.BLD}🔑 API Key:{Color.RST}   {'✅ 已配置' if env_ok else '❌ 未配置'}",
        f"",
        f"  {Color.BLD}{Color.BCYN}🤖 Agent 状态{Color.RST}",
    ]

    for key in sorted(AGENTS.keys()):
        agent = AGENTS[key]
        exists = check_agent_file(agent)
        status_icon = "✅" if exists else "❌"
        lines.append(f"  {agent['icon']} {agent['name']:<16} {status_icon}")

    lines.append("")
    lines.append(f"  {Color.HINT}提示: 确保 .env 文件已配置 DEEPSEEK_API_KEY{Color.RST}")

    content = "\n".join(lines)
    print_panel(
        content=content,
        title="📊 系统状态",
        color=Color.SYS,
        width=width,
    )
    print()


def show_help() -> None:
    """显示帮助信息"""
    width = min(get_term_width() - 2, 80)
    width = max(width, 50)

    lines = [
        f"  {Color.BLD}{Color.BCYN}💡 使用说明{Color.RST}",
        f"",
        f"  {Color.BGRN}1-6{Color.RST}    选择对应的 Agent 启动",
        f"  {Color.BGRN}0{Color.RST}      退出程序",
        f"  {Color.BGRN}s{Color.RST}      显示系统状态信息",
        f"  {Color.BGRN}h{Color.RST}      显示此帮助",
        f"  {Color.BGRN}c{Color.RST}      清屏",
        f"",
        f"  {Color.BLD}命令行参数:{Color.RST}",
        f"  {Color.DIM}--direct{Color.RST}    直接启动 LeaderAgent（跳过菜单）",
        f"  {Color.DIM}--agent NAME{Color.RST} 直接启动指定子 Agent",
        f"  {Color.DIM}--status{Color.RST}    显示系统状态并退出",
        f"  {Color.DIM}--help{Color.RST}      显示此帮助信息",
        f"",
        f"  {Color.HINT}示例: python launch_leader_terminal.py --direct{Color.RST}",
        f"  {Color.HINT}示例: python launch_leader_terminal.py --agent CodingAgent{Color.RST}",
    ]

    content = "\n".join(lines)
    print_panel(
        content=content,
        title="💡 帮助指南",
        color=Color.INFO,
        width=width,
    )
    print()


# ═══════════════════════════════════════════════════════════════════════
# 主菜单界面
# ═══════════════════════════════════════════════════════════════════════

def build_menu_content() -> str:
    """构建菜单面板的内容字符串"""
    lines = []
    width = min(get_term_width() - 2, 80)
    width = max(width, 50)

    # 标题区
    lines.append(f"  {Color.BLD}{Color.BCYN}🧠  LeaderAgent — 智能 Agent 调度大脑{Color.RST}")
    lines.append(f"  {Color.DIM}拆分需求 · 分配任务 · 唤醒执行（流式输出）{Color.RST}")
    lines.append("")

    # 环境检测
    python_cmd = find_python()
    env_ok = check_env_file()
    env_status = f"{Color.OK}✅ 已配置{Color.RST}" if env_ok else f"{Color.ERR}❌ 未配置{Color.RST}"
    lines.append(f"  {Color.DIM}{'─' * (width - 6)}{Color.RST}")
    lines.append(f"  {Color.DIM}🐍 {python_cmd}    |    🔑 API Key: {env_status}{Color.RST}")
    lines.append(f"  {Color.DIM}{'─' * (width - 6)}{Color.RST}")
    lines.append("")

    # Agent 选项列表
    lines.append(f"  {Color.BLD}{Color.BCYN}📋 请选择要启动的 Agent:{Color.RST}")
    lines.append("")

    for key in sorted(AGENTS.keys()):
        agent = AGENTS[key]
        exists = check_agent_file(agent)
        status = "" if exists else f"  {Color.DIM}(文件不存在){Color.RST}"

        # 可用/不可用标记
        if exists:
            marker = f"{agent['color']}●{Color.RST}"
        else:
            marker = f"{Color.DIM}○{Color.RST}"

        lines.append(
            f"  {Color.BGRN}[{key}]{Color.RST}  {marker} "
            f"{agent['icon']}  {agent['color']}{agent['name']:<16}{Color.RST}"
            f"{Color.DIM}{agent['description']}{Color.RST}{status}"
        )

    lines.append("")
    lines.append(f"  {Color.DIM}{'─' * (width - 6)}{Color.RST}")
    lines.append("")

    # 底部操作提示
    lines.append(f"  {Color.BGRN}[0]{Color.RST}  ❌  退出程序")
    lines.append(f"  {Color.BGRN}[s]{Color.RST}  📊  显示系统状态")
    lines.append(f"  {Color.BGRN}[h]{Color.RST}  💡  帮助")
    lines.append(f"  {Color.BGRN}[c]{Color.RST}  🧹  清屏")
    lines.append("")
    lines.append(f"  {Color.HINT}直接输入数字或命令，按 Enter 确认{Color.RST}")

    return "\n".join(lines)


def show_menu() -> Optional[str]:
    """显示主菜单并获取用户选择

    Returns:
        用户选择的 Agent 键（如 "1", "2"），或 None 表示退出
    """
    width = min(get_term_width() - 2, 80)
    width = max(width, 50)

    # 构建并显示菜单面板
    menu_content = build_menu_content()

    print()
    print_panel(
        content=menu_content,
        title="🧠 LeaderAgent 终端启动器",
        color=Color.TITLE,
        width=width,
    )
    print()

    # 获取用户输入 — 使用中文友好的 chinese_input
    choice = chinese_input(
        f"  {Color.BCYN}{Color.BLD}👉 请输入选项{Color.RST} "
        f"{Color.DIM}[0-6/s/h/c]{Color.RST}: "
    ).strip().lower()

    if not choice:
        return None

    return choice


# ═══════════════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════════════

def run_interactive_launcher():
    """运行交互式启动器主循环"""
    python_cmd = find_python()

    # 检查 Python
    if not python_cmd:
        print_status("❌ 未找到 Python 3 解释器，请先安装 Python", "error")
        sys.exit(1)

    # 检查 .env
    env_ok = check_env_file()
    if not env_ok:
        print()
        print_status("⚠️  未检测到有效的 API Key 配置！", "warning")
        print()
        print(f"  {Color.DIM}请创建或编辑 .env 文件，添加 DeepSeek API Key:{Color.RST}")
        print(f"  {Color.BCYN}DEEPSEEK_API_KEY=your_api_key_here{Color.RST}")
        print()
        print(f"  {Color.DIM}.env 文件路径: {PROJECT_ROOT / '.env'}{Color.RST}")
        print()
        try:
            chinese_input(f"  {Color.HINT}按 Enter 键继续...{Color.RST}")
        except ExitRequested:
            print()
            sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

    # 欢迎信息
    clear_screen()

    welcome_extra = [
        f"  🐍 Python: {python_cmd}",
        f"  🔑 API Key: {'✅ 已配置' if env_ok else '❌ 未配置'}",
        f"  📂 目录: {PROJECT_ROOT}",
        "",
        f"  输入数字选择 Agent · 输入 s 查看状态 · 输入 0 退出",
    ]

    print_welcome(
        title="🧠  LeaderAgent 终端启动器",
        subtitle="选择一个 Agent，在新终端窗口中启动完整 CLI 交互",
        extra_info=welcome_extra,
    )

    # ── 主循环 ──
    while True:
        try:
            choice = show_menu()
        except ExitRequested:
            # 在菜单提示符处按 Ctrl+C → 退出程序
            print()
            print_goodbye("🌟 期待下次与您并肩作战！")
            break

        # 退出
        if choice is None or choice in EXIT_KEYS:
            print_goodbye("🌟 期待下次与您并肩作战！")
            break

        # 帮助
        if choice in HELP_KEYS:
            clear_screen()
            show_help()
            continue

        # 清屏
        if choice == "c":
            clear_screen()
            continue

        # 系统状态
        if choice == "s":
            clear_screen()
            show_system_info()
            continue

        # Agent 选择（1-6）
        if choice in AGENTS:
            agent = AGENTS[choice]
            if not check_agent_file(agent):
                print()
                print_status(f"❌ 文件不存在: {agent['file']}", "error")
                print(f"  {Color.DIM}请确保该文件位于: {PROJECT_ROOT}{Color.RST}")
                print()
                print(f"  {Color.HINT}按 Enter 键返回主菜单...{Color.RST}")
                try:
                    chinese_input()  # 使用中文友好的输入
                except ExitRequested:
                    print()
                    sys.exit(0)
                except (EOFError, KeyboardInterrupt):
                    print()
                    sys.exit(0)
                continue

            # 检查 LeaderAgent 是否有 .env 依赖
            if choice == "1" and not env_ok:
                print()
                print_status("⚠️  LeaderAgent 需要有效的 API Key 才能运行！", "warning")
                print(f"  {Color.DIM}请先在 .env 文件中配置 DEEPSEEK_API_KEY{Color.RST}")
                print()
                print(f"  {Color.HINT}按 Enter 键返回主菜单...{Color.RST}")
                try:
                    chinese_input()  # 使用中文友好的输入
                except ExitRequested:
                    print()
                    sys.exit(0)
                except (EOFError, KeyboardInterrupt):
                    print()
                    sys.exit(0)
                continue

            # 启动 Agent
            launch_agent(choice, python_cmd)
            continue

        # 无效输入
        print()
        print_status(f"⚠️  无效选项: '{choice}'，请输入 0-6, s, h, c", "warning")
        print(f"  {Color.DIM}输入 h 查看帮助{Color.RST}")
        print()
        print(f"  {Color.HINT}按 Enter 键继续...{Color.RST}")
        try:
            chinese_input()  # 使用中文友好的输入
        except ExitRequested:
            print()
            break
        except (EOFError, KeyboardInterrupt):
            print()
            break


def run_direct(agent_name: Optional[str] = None):
    """直接启动指定的 Agent 或默认启动 LeaderAgent

    Args:
        agent_name: Agent 名称（可选），None 则启动 LeaderAgent
    """
    python_cmd = find_python()

    if agent_name:
        # 查找匹配的 Agent
        for key, agent in AGENTS.items():
            if agent["name"].lower() == agent_name.lower():
                if not check_agent_file(agent):
                    print(f"❌ 文件不存在: {agent['file']}")
                    sys.exit(1)
                launch_agent(key, python_cmd)
                return

        # 没找到匹配的 Agent
        available = ", ".join(a["name"] for a in AGENTS.values())
        print(f"❌ 未知的 Agent: '{agent_name}'")
        print(f"   可用选项: {available}")
        sys.exit(1)
    else:
        # 默认启动 LeaderAgent
        launch_agent("1", python_cmd)


# ═══════════════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════════════

def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="🚀 LeaderAgent 终端启动器 — 交互式菜单启动 Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                         # 交互式菜单
  %(prog)s --direct                # 直接启动 LeaderAgent
  %(prog)s --agent CodingAgent     # 直接启动指定子 Agent
  %(prog)s --status                # 显示系统状态
        """,
    )

    parser.add_argument(
        "--direct", "-d",
        action="store_true",
        help="直接启动 LeaderAgent（跳过交互菜单）",
    )
    parser.add_argument(
        "--agent", "-a",
        type=str,
        default=None,
        metavar="NAME",
        help="直接启动指定的 Agent（如 CodingAgent, SkillsManager 等）",
    )
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="显示系统状态信息并退出",
    )

    args = parser.parse_args()

    # ── 显示系统状态并退出 ──
    if args.status:
        clear_screen()
        show_system_info()
        return

    # ── 直接模式 ──
    if args.direct or args.agent:
        run_direct(args.agent)
        return

    # ── 交互模式（默认） ──
    try:
        run_interactive_launcher()
    except KeyboardInterrupt:
        print()
        print_goodbye("🌟 期待下次与您并肩作战！")
        sys.exit(0)
    except ExitRequested:
        print()
        print_goodbye("👋 再见！")
        sys.exit(0)
    except Exception as e:
        print()
        print_status(f"❌ 程序异常: {e}", "error")
        print(f"  {Color.DIM}请检查终端是否支持 ANSI 颜色输出{Color.RST}")
        sys.exit(1)


if __name__ == "__main__":
    main()
