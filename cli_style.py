"""
cli_style — CLI 美化工具集 (Claude Code Style Enhanced)

提供 ANSI 颜色、ASCII 艺术横幅、面板框、消息标签、状态指示器等美化功能，
供 FishPool / KillerWhale / FishFarmer 等 CLI 程序使用。
"""

import os
import re
import json
import sys
import shutil
import threading
import time
from typing import Optional, List, Callable
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════
# ANSI 颜色与样式
# ═══════════════════════════════════════════════════════════════════════

class Color:
    """ANSI 颜色与样式常量"""
    # 重置与样式
    RST = '\033[0m'
    BLD = '\033[1m'
    DIM = '\033[2m'
    ITA = '\033[3m'
    ULI = '\033[4m'
    BLK = '\033[5m'

    # 标准前景色
    RED = '\033[31m'
    GRN = '\033[32m'
    YEL = '\033[33m'
    BLU = '\033[34m'
    MAG = '\033[35m'
    CYN = '\033[36m'
    WHT = '\033[37m'

    # 亮色前景
    BRED = '\033[91m'
    BGRN = '\033[92m'
    BYEL = '\033[93m'
    BBLU = '\033[94m'
    BMAG = '\033[95m'
    BCYN = '\033[96m'
    BWHT = '\033[97m'

    # 背景色
    BG_RED = '\033[41m'
    BG_GRN = '\033[42m'
    BG_YEL = '\033[43m'
    BG_BLU = '\033[44m'
    BG_MAG = '\033[45m'
    BG_CYN = '\033[46m'
    BG_WHT = '\033[47m'
    BG_BMAG = '\033[105m'

    # ── 语义化颜色别名 ──
    USER = CYN          # 用户输入
    AGENT = BYEL        # Agent 回复
    TOOL = BMAG         # 工具调用
    SYS = BBLU          # 系统信息
    OK = BGRN           # 成功
    ERR = BRED          # 错误
    WARN = BYEL         # 警告
    INFO = BBLU         # 信息
    TITLE = BCYN        # 标题
    HINT = DIM          # 提示文本
    TAG = BWHT          # 标签
    CODE = BGRN         # 代码高亮
    HIGHLIGHT = BCYN    # 高亮文本
    SEP = DIM           # 分隔线

    # ── Claude Code 风格颜色 ──
    # Warm amber (24-bit RGB: 213, 168, 94)
    CLAUDE = '\033[38;2;213;168;94m'
    CLAUDE_BG = '\033[48;2;213;168;94m'

    # Magenta/Purple 主色调（FishPool 品牌色）
    PRIMARY = '\033[38;2;180;80;255m'       # 紫色主色
    PRIMARY_BRIGHT = '\033[38;2;200;120;255m'
    PRIMARY_BG = '\033[48;2;180;80;255m'
    PRIMARY_DIM = '\033[38;2;120;50;180m'

    # 标题/品牌色
    BRAND = PRIMARY
    BRAND_BRIGHT = PRIMARY_BRIGHT


# ═══════════════════════════════════════════════════════════════════════
# 终端工具函数
# ═══════════════════════════════════════════════════════════════════════

def cprint(text: str, color: str = "", end: str = "\n", bold: bool = False, reset: bool = True) -> None:
    """带颜色的 print"""
    prefix = (Color.BLD if bold else "") + color
    suffix = Color.RST if reset else ""
    print(f"{prefix}{text}{suffix}", end=end)


def get_term_width() -> int:
    """获取终端宽度，默认 80"""
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def make_line(char: str = "─", width: Optional[int] = None) -> str:
    """生成重复字符的水平线"""
    if width is None:
        width = get_term_width()
    return char * max(width, 20)


def truncate_text(text: str, max_len: int = 80) -> str:
    """截断文本并添加省略号"""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def format_timestamp() -> str:
    """格式化当前时间戳"""
    return datetime.now().strftime("%H:%M:%S")


def format_full_timestamp() -> str:
    """完整时间戳"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def strip_ansi(text: str) -> str:
    """移除字符串中的 ANSI 转义码"""
    return re.sub(r'\033\[[0-9;]*m', '', text)


def get_visible_width(text: str) -> int:
    """获取文本的可见宽度（不含 ANSI 转义码）"""
    return len(strip_ansi(text))


# ═══════════════════════════════════════════════════════════════════════
# ASCII 艺术横幅（Claude Code 风格）
# ═══════════════════════════════════════════════════════════════════════

LEADER_ASCII = [
    "██████╗ ███████╗ █████╗ ██████╗ ███████╗██████╗ ",
    "██╔════╝ ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔══██╗",
    "██║  ███╗█████╗  ███████║██║  ██║█████╗  ██████╔╝",
    "██║   ██║██╔══╝  ██╔══██║██║  ██║██╔══╝  ██╔══██╗",
    "╚██████╔╝███████╗██║  ██║██████╔╝███████╗██║  ██║",
    " ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝",
]

AGENT_ASCII = [
    " █████╗  ██████╗ ███████╗███╗   ██╗████████╗",
    "██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝",
    "███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ",
    "██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ",
    "██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ",
    "╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ",
]

CODING_ASCII = [
    " ██████╗ ██████╗ ██████╗ ██╗███╗   ██╗ ██████╗ ",
    "██╔════╝██╔═══██╗██╔══██╗██║████╗  ██║██╔════╝ ",
    "██║     ██║   ██║██║  ██║██║██╔██╗ ██║██║  ███╗",
    "██║     ██║   ██║██║  ██║██║██║╚██╗██║██║   ██║",
    "╚██████╗╚██████╔╝██████╔╝██║██║ ╚████║╚██████╔╝",
    " ╚═════╝ ╚═════╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝ ",
]


def print_ascii_banner(
    title_ascii: list,
    subtitle: str = "",
    version: str = "",
    color: str = "",
    width: Optional[int] = None,
) -> None:
    """打印大型 ASCII 艺术横幅（Claude Code 风格）

    Args:
        title_ascii: ASCII 艺术字行列表
        subtitle: 副标题
        version: 版本号
        color: 颜色
        width: 终端宽度
    """
    if width is None:
        width = min(get_term_width(), 80)
    width = max(width, 50)

    clr = color if color else Color.BRAND
    rst = Color.RST
    dim = Color.DIM

    print()
    # 顶部装饰线
    print(f"  {clr}{'═' * (width - 4)}{rst}")

    # ASCII 艺术字（居中）
    for line in title_ascii:
        visible = strip_ansi(line)
        padding = max(0, (width - 4 - len(visible)) // 2)
        print(f"  {clr}{' ' * padding}{line}{rst}")

    # 版本号和副标题
    info_parts = []
    if version:
        info_parts.append(f"v{version}")
    if subtitle:
        info_parts.append(subtitle)

    if info_parts:
        info_line = "  ·  ".join(info_parts)
        padding = max(0, (width - 4 - len(strip_ansi(info_line))) // 2)
        print(f"  {dim}{' ' * padding}{info_line}{rst}")
        print()

    # 底部装饰线
    print(f"  {clr}{'═' * (width - 4)}{rst}")
    print()


def print_small_banner(
    title: str,
    subtitle: str = "",
    color: str = "",
    width: Optional[int] = None,
) -> None:
    """打印小型横幅（轻量版）"""
    if width is None:
        width = min(get_term_width() - 2, 72)
    width = max(width, 40)

    clr = color if color else Color.BRAND
    rst = Color.RST

    print()
    print(f"  {clr}{'─' * (width - 4)}{rst}")
    print(f"  {clr}{Color.BLD}  {title}{rst}")
    if subtitle:
        print(f"  {Color.DIM}  {subtitle}{rst}")
    print(f"  {clr}{'─' * (width - 4)}{rst}")
    print()


# ═══════════════════════════════════════════════════════════════════════
# 面板与边框
# ═══════════════════════════════════════════════════════════════════════

def print_panel(
    content: str,
    title: str = "",
    color: str = "",
    width: Optional[int] = None,
    border_style: str = "rounded",
) -> None:
    """打印一个带标题的圆角/直角面板框

    Args:
        content: 面板内容（多行文本）
        title: 面板标题
        color: 边框颜色
        width: 面板宽度
        border_style: "rounded" = ╭╮╰╯, "square" = ┌┐└┘, "double" = ╔╗╚╝
    """
    if width is None:
        width = min(get_term_width() - 2, 100)
    width = max(width, 40)

    if border_style == "rounded":
        tl, tr, bl, br = "╭", "╮", "╰", "╯"
    elif border_style == "double":
        tl, tr, bl, br = "╔", "╗", "╚", "╝"
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
        visible = strip_ansi(line)
        padding = max(0, width - 2 - len(visible))
        print(f"{clr}{v}{rst} {line}{' ' * padding}{clr}{v}{rst}")

    print(f"{clr}{footer}{rst}")


def print_banner(text: str, color: str = "", char: str = "═", width: Optional[int] = None) -> None:
    """打印横幅（居中文本 + 上下装饰线）"""
    if width is None:
        width = min(get_term_width(), 80)
    line = char * width
    rst = Color.RST
    clr = color if color else ""
    centered = text.center(width)
    print(f"{clr}{line}{rst}")
    print(f"{clr}{centered}{rst}")
    print(f"{clr}{line}{rst}")


# ═══════════════════════════════════════════════════════════════════════
# 消息标签系统（Claude Code 风格）
# ═══════════════════════════════════════════════════════════════════════

def print_system_message(message: str, width: Optional[int] = None) -> None:
    """打印 [System] 系统消息"""
    if width is None:
        width = min(get_term_width() - 4, 70)
    print(f"  {Color.DIM}[System]{Color.RST} {Color.INFO}{message}{Color.RST}")


def print_thinking_message(message: str, width: Optional[int] = None) -> None:
    """打印 [Thinking] 思考消息"""
    if width is None:
        width = min(get_term_width() - 4, 70)
    print(f"  {Color.DIM}[Thinking]{Color.RST} {Color.MAG}{message}{Color.RST}")


def print_result_message(message: str, width: Optional[int] = None) -> None:
    """打印 [Result] 结果消息"""
    if width is None:
        width = min(get_term_width() - 4, 70)
    print(f"  {Color.DIM}[Result]{Color.RST} {Color.GRN}{message}{Color.RST}")


def print_error_message(message: str, width: Optional[int] = None) -> None:
    """打印 [Error] 错误消息"""
    if width is None:
        width = min(get_term_width() - 4, 70)
    print(f"  {Color.DIM}[Error]{Color.RST} {Color.RED}{message}{Color.RST}")


def print_warn_message(message: str, width: Optional[int] = None) -> None:
    """打印 [Warning] 警告消息"""
    if width is None:
        width = min(get_term_width() - 4, 70)
    print(f"  {Color.DIM}[Warning]{Color.RST} {Color.YEL}{message}{Color.RST}")


def print_tagged_line(tag: str, content: str, tag_color: str = "", content_color: str = "") -> None:
    """打印带标签的行

    Args:
        tag: 标签文本（如 "System", "Thinking", "Result", "Error"）
        content: 内容文本
        tag_color: 标签颜色
        content_color: 内容颜色
    """
    tc = tag_color if tag_color else Color.DIM
    cc = content_color if content_color else ""
    print(f"  {tc}[{tag}]{Color.RST} {cc}{content}{Color.RST}")


# ═══════════════════════════════════════════════════════════════════════
# 状态指示器 / Spinner
# ═══════════════════════════════════════════════════════════════════════

class Spinner:
    """旋转状态指示器（后台线程）

    用法:
        spinner = Spinner("Thinking...")
        spinner.start()
        # ... 执行耗时操作 ...
        spinner.stop("Done!")
    """

    _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    _INTERVAL = 0.1

    def __init__(self, message: str = "", color: str = ""):
        self.message = message
        self.color = color if color else Color.MAG
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._pos = 0

    def start(self):
        """启动 spinner"""
        if self._running:
            return
        self._running = True
        self._pos = 0
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        """spinner 后台循环"""
        while self._running:
            frame = self._FRAMES[self._pos % len(self._FRAMES)]
            msg = f"  {self.color}{frame} {self.message}{Color.RST}"
            sys.stdout.write(f"\r{msg}")
            sys.stdout.flush()
            self._pos += 1
            time.sleep(self._INTERVAL)

    def update_message(self, message: str):
        """更新 spinner 显示的消息"""
        self.message = message

    def stop(self, final_message: str = ""):
        """停止 spinner

        Args:
            final_message: 停止后显示的消息（可选）
        """
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)

        # 清除 spinner 行
        sys.stdout.write("\r" + " " * (get_term_width() - 1) + "\r")
        sys.stdout.flush()

        if final_message:
            print(f"  {Color.GRN}✓{Color.RST} {final_message}")


def print_thinking_indicator(message: str = "⟳ Thinking") -> None:
    """打印静态思考指示器

    使用 ⟳ 符号，适合不需要动态 spinner 的场景
    """
    print(f"  {Color.MAG}{Color.BLD}⟳{Color.RST} {Color.DIM}{message}{Color.RST}", end="", flush=True)


def clear_thinking_indicator():
    """清除思考指示器行"""
    sys.stdout.write("\r" + " " * (get_term_width() - 1) + "\r")
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════════════════
# 代码块展示（带 ┃ 缩进线）
# ═══════════════════════════════════════════════════════════════════════

def print_code_indent(code: str, language: str = "") -> None:
    """以缩进线风格打印代码块（Claude Code 风格 ┃）

    Args:
        code: 代码文本
        language: 语言名称（可选）
    """
    lines = code.split("\n")
    header = f"  {Color.DIM}{language}{Color.RST}" if language else ""

    if header:
        print(header)

    for line in lines:
        print(f"  {Color.DIM}┃{Color.RST} {Color.CODE}{line}{Color.RST}")


def print_code_block(code: str, language: str = "python") -> None:
    """打印代码块（面板风格）"""
    width = min(get_term_width() - 2, 90)
    width = max(width, 40)

    lines = code.split("\n")
    max_lineno = len(lines)
    lineno_width = len(str(max_lineno))

    content_parts = []
    for i, line in enumerate(lines):
        lineno = str(i + 1).rjust(lineno_width)
        content_parts.append(f"  {Color.DIM}{lineno}{Color.RST} {Color.CODE}{line}{Color.RST}")

    content = "\n".join(content_parts)

    print_panel(
        content=content,
        title=f"💻 {language}",
        color=Color.TOOL,
        width=width,
    )


# ═══════════════════════════════════════════════════════════════════════
# 列表展示
# ═══════════════════════════════════════════════════════════════════════

def print_bullet_list(items: List[str], bullet: str = "•", color: str = "") -> None:
    """打印带子弹点的列表

    Args:
        items: 列表项
        bullet: 子弹点符号
        color: 子弹点颜色
    """
    clr = color if color else Color.BRAND
    for item in items:
        print(f"  {clr}{bullet}{Color.RST} {item}")


def print_numbered_list(items: List[str], start: int = 1) -> None:
    """打印编号列表"""
    for i, item in enumerate(items, start=start):
        print(f"  {Color.DIM}{i}.{Color.RST} {item}")


# ═══════════════════════════════════════════════════════════════════════
# 工具调用展示
# ═══════════════════════════════════════════════════════════════════════

def print_tool_result(tool_name: str, args: dict, result: str) -> None:
    """以美观的格式打印工具调用结果"""
    width = min(get_term_width() - 2, 100)
    width = max(width, 50)

    args_str = json.dumps(args, ensure_ascii=False, indent=2) if args else "{}"

    # 截断过长的结果
    result_display = result
    MAX_RESULT_LINES = 20
    result_lines = result.split("\n")
    if len(result_lines) > MAX_RESULT_LINES:
        result_display = "\n".join(result_lines[:MAX_RESULT_LINES]) \
                         + f"\n{Color.DIM}... (共 {len(result_lines)} 行，已截断){Color.RST}"

    content_parts = [
        f"{Color.BLD}📌 工具:{Color.RST} {Color.PRIMARY_BRIGHT}{tool_name}{Color.RST}",
        f"{Color.BLD}📥 参数:{Color.RST} {Color.DIM}{truncate_text(args_str, 60)}{Color.RST}",
    ]

    if len(args_str) > 60:
        content_parts.append(f"   {Color.DIM}{args_str}{Color.RST}")

    content_parts.append("")
    content_parts.append(f"{Color.BLD}📋 执行结果:{Color.RST}")
    content_parts.append(result_display)

    content = "\n".join(content_parts)

    print_panel(
        content=content,
        title=f"🔧 {tool_name}",
        color=Color.TOOL,
        width=width,
    )


# ═══════════════════════════════════════════════════════════════════════
# Agent 聊天气泡风格
# ═══════════════════════════════════════════════════════════════════════

def print_user_input(user_input: str) -> None:
    """以用户气泡风格打印用户输入"""
    width = min(get_term_width() - 4, 80)
    width = max(width, 30)

    print()
    # 用户标签
    print(f"  {Color.USER}{Color.BLD}┌─ 💬 You ─────────────────────────────────{Color.RST}")
    print(f"  {Color.USER}{Color.BLD}│{Color.RST} ", end="")

    # 处理多行输入
    lines = user_input.split("\n")
    for i, line in enumerate(lines):
        if i > 0:
            print(f"\n  {Color.USER}{Color.BLD}│{Color.RST} ", end="")
        print(f"{Color.USER}{line}{Color.RST}", end="")
    print()

    print(f"  {Color.USER}{Color.BLD}╰{'─' * (width - 2)}{Color.RST}")
    print()


def print_agent_thinking() -> None:
    """打印 Agent 思考中的提示"""
    print(f"  {Color.MAG}{Color.BLD}⟳{Color.RST} {Color.DIM}Thinking...{Color.RST}", end="", flush=True)


def print_agent_start(agent_name: str = "Agent", timestamp: str = "") -> None:
    """打印 Agent 回复开始的分隔线"""
    ts = timestamp or format_timestamp()
    print()
    print(f"  {Color.BRAND}{Color.BLD}┌─ 🤖 {agent_name} @ {ts}{Color.RST}")
    print(f"  {Color.BRAND}{Color.BLD}│{Color.RST} ", end="", flush=True)


def print_agent_end(width: Optional[int] = None) -> None:
    """打印 Agent 回复结束的分隔线"""
    if width is None:
        width = min(get_term_width() - 4, 60)
    print()
    print(f"  {Color.BRAND}{Color.BLD}╰{'─' * max(width, 30)}{Color.RST}")
    print()


def print_streaming_prefix():
    """流式输出前缀"""
    print(f"  {Color.BRAND}{Color.BLD}│{Color.RST} ", end="", flush=True)


# ═══════════════════════════════════════════════════════════════════════
# Claude Code 风格紧凑工具调用
# ═══════════════════════════════════════════════════════════════════════

def print_claude_tool_call(tool_name: str, args_str: str = "") -> None:
    """Claude Code 风格紧凑工具调用显示

    一行内显示工具名称和参数，不占大面板

    Args:
        tool_name: 工具名称
        args_str: 参数 JSON 字符串
    """
    if args_str and len(args_str) > 70:
        args_str = args_str[:67] + "..."
    if args_str:
        print(f"  {Color.BRAND}┄ {tool_name}{Color.RST}  {Color.DIM}{args_str}{Color.RST}")
    else:
        print(f"  {Color.BRAND}┄ {tool_name}{Color.RST}")


def print_claude_result_line(line: str, max_len: int = 100) -> None:
    """打印一条 Claude Code 风格的结果行

    轻量缩进显示，无边框

    Args:
        line: 文本行
        max_len: 最大显示长度
    """
    visible = strip_ansi(line)
    if not visible:
        return
    if len(visible) > max_len:
        line = visible[:max_len - 3] + "..."
    print(f"  {Color.DIM}{line}{Color.RST}")


# ═══════════════════════════════════════════════════════════════════════
# 技能管理专用展示
# ═══════════════════════════════════════════════════════════════════════

def print_skill_list(skills: dict, detail: bool = False) -> None:
    """以美观面板展示技能列表"""
    width = min(get_term_width() - 2, 90)
    width = max(width, 50)

    if not skills:
        print_panel(
            content=f"  {Color.WARN}⚠️ 未发现任何导出的技能函数。{Color.RST}",
            title="📦 技能清单",
            color=Color.INFO,
            width=width,
        )
        return

    lines = [f"  {Color.BLD}共 {Color.PRIMARY_BRIGHT}{len(skills)}{Color.RST}{Color.BLD} 项技能{Color.RST}\n"]

    # 按模块分组
    module_groups = {}
    for func_name, module_name in skills.items():
        module_groups.setdefault(module_name, []).append(func_name)

    for module_name, func_names in module_groups.items():
        lines.append(f"  {Color.INFO}📁 模块:{Color.RST} {Color.BWHT}{module_name}.py{Color.RST}")
        for func_name in func_names:
            lines.append(f"    {Color.BRAND}◆{Color.RST} {Color.BCYN}{func_name}{Color.RST}")
        lines.append("")

    content = "\n".join(lines).strip()
    print_panel(
        content=content,
        title="📦 AgentSkills 技能清单",
        color=Color.INFO,
        width=width,
    )


# ═══════════════════════════════════════════════════════════════════════
# 进度与状态
# ═══════════════════════════════════════════════════════════════════════

def print_status(message: str, status: str = "info") -> None:
    """打印状态消息

    Args:
        message: 状态消息
        status: "info" | "ok" | "error" | "warning"
    """
    icons = {
        "info": "ℹ️",
        "ok": "✅",
        "error": "❌",
        "warning": "⚠️",
    }
    colors = {
        "info": Color.INFO,
        "ok": Color.OK,
        "error": Color.ERR,
        "warning": Color.WARN,
    }
    icon = icons.get(status, "ℹ️")
    color = colors.get(status, Color.INFO)
    print(f"  {color}{icon} {message}{Color.RST}")


def print_step(step_num: int, total: int, message: str) -> None:
    """打印步骤进度"""
    print(f"  {Color.DIM}[{step_num}/{total}]{Color.RST} {Color.BLD}{message}{Color.RST}")


# ═══════════════════════════════════════════════════════════════════════
# 欢迎与告别
# ═══════════════════════════════════════════════════════════════════════

def print_welcome(
    title: str,
    subtitle: str = "",
    model: str = "",
    tool_count: int = 0,
    extra_info: Optional[list[str]] = None,
) -> None:
    """打印欢迎界面"""
    width = min(get_term_width() - 2, 80)
    width = max(width, 50)

    content_parts = [
        f"  {Color.BLD}{Color.PRIMARY_BRIGHT}{title}{Color.RST}",
    ]
    if subtitle:
        content_parts.append(f"  {Color.DIM}{subtitle}{Color.RST}")
    content_parts.append("")

    if model:
        content_parts.append(f"  {Color.BLD}模型:{Color.RST}  {Color.PRIMARY_BRIGHT}{model}{Color.RST}")
    if tool_count > 0:
        content_parts.append(f"  {Color.BLD}工具:{Color.RST}  {Color.BGRN}{tool_count} 个工具可用{Color.RST}")

    if extra_info:
        content_parts.append("")
        for info in extra_info:
            content_parts.append(f"  {Color.DIM}{info}{Color.RST}")

    content_parts.append("")
    content_parts.append(f"  {Color.HINT}输入 /exit 或 /quit 退出对话{Color.RST}")

    content = "\n".join(content_parts)

    print()
    print_panel(
        content=content,
        title=f"🚀 {title.split()[0] if title else 'Agent'}",
        color=Color.SYS,
        width=width,
    )
    print()


def print_goodbye(message: str = "🌟 感谢使用，期待再次相见！") -> None:
    """打印告别信息"""
    width = min(get_term_width() - 2, 80)
    width = max(width, 50)

    print()
    print_panel(
        content=f"  {Color.BLD}{Color.PRIMARY_BRIGHT}  {message}{Color.RST}",
        title="👋 再见",
        color=Color.SYS,
        width=width,
    )
    print()


# ═══════════════════════════════════════════════════════════════════════
# 帮助信息
# ═══════════════════════════════════════════════════════════════════════

def print_help(commands: list[tuple[str, str]]) -> None:
    """打印帮助信息

    Args:
        commands: [(命令, 说明), ...] 列表
    """
    width = min(get_term_width() - 2, 80)
    width = max(width, 50)

    lines = [f"  {Color.BLD}{Color.PRIMARY_BRIGHT}可用命令:{Color.RST}\n"]
    for cmd, desc in commands:
        lines.append(f"  {Color.BGRN}{cmd:<12}{Color.RST} - {desc}")
    lines.append("")
    lines.append(f"  {Color.DIM}也可以直接输入自然语言与 AI 对话{Color.RST}")

    content = "\n".join(lines)

    print_panel(
        content=content,
        title="💡 帮助",
        color=Color.INFO,
        width=width,
    )
    print()


# ═══════════════════════════════════════════════════════════════════════
# 分隔线
# ═══════════════════════════════════════════════════════════════════════

def print_separator(char: str = "━", color: str = "") -> None:
    """打印分隔线"""
    width = get_term_width()
    clr = color if color else Color.SEP
    print(f"{clr}{char * max(width, 20)}{Color.RST}")


def print_claude_separator(width: Optional[int] = None) -> None:
    """Claude Code 风格紧凑分隔线"""
    if width is None:
        width = min(get_term_width() - 4, 50)
    width = max(width, 30)
    print(f"  {Color.DIM}{'─' * width}{Color.RST}")
    print()


# ═══════════════════════════════════════════════════════════════════════
# 用户输入提示符
# ═══════════════════════════════════════════════════════════════════════

def build_claude_prompt() -> str:
    """构建 Claude Code 风格的用户输入提示符

    Returns:
        ANSI 彩色提示符字符串
    """
    return f"  {Color.BRAND}❯{Color.RST} "


def build_prompt_with_label(label: str = "You") -> str:
    """构建带标签的用户输入提示符

    Args:
        label: 标签文本

    Returns:
        ANSI 彩色提示符字符串
    """
    return f"  {Color.BRAND_BRIGHT}{Color.BLD}💬 {label}{Color.RST} {Color.DIM}❯{Color.RST} "


# ═══════════════════════════════════════════════════════════════════════
# 对 FishPool 友好的状态显示
# ═══════════════════════════════════════════════════════════════════════

def print_leader_status_line(agent_name: str, status_icon: str, description: str) -> None:
    """打印 FishPool 的状态行

    Args:
        agent_name: Agent 名称
        status_icon: 状态图标（✅/❌/⚠️）
        description: 功能描述
    """
    print(f"  {Color.BRAND}◆{Color.RST} {Color.BLD}{Color.PRIMARY_BRIGHT}{agent_name:<20}{Color.RST} {status_icon}  {Color.DIM}{description}{Color.RST}")


def print_leader_info_line(key: str, value: str, key_color: str = "", value_color: str = "") -> None:
    """打印 FishPool 信息行"""
    kc = key_color if key_color else Color.DIM
    vc = value_color if value_color else Color.PRIMARY_BRIGHT
    print(f"  {Color.BRAND}│{Color.RST} {kc}{key}:{Color.RST} {vc}{value}{Color.RST}")


# ═══════════════════════════════════════════════════════════════════════
# Claude Code 风格欢迎横幅（轻量版）
# ═══════════════════════════════════════════════════════════════════════

def print_claude_welcome(
    title: str,
    subtitle: str = "",
    model: str = "",
    tool_count: int = 0,
    extra_info: Optional[list[str]] = None,
) -> None:
    """Claude Code 风格轻量顶部横幅

    暖紫色主色调，紧凑显示

    Args:
        title: 主标题（如 "🔍 Searching Agent"）
        subtitle: 副标题
        model: 模型名称
        tool_count: 工具数量
        extra_info: 额外信息列表
    """
    width = min(get_term_width(), 72)
    width = max(width, 40)
    sep = "─"

    print()
    # 顶部装饰线
    print(f"  {Color.BRAND}{sep * (width - 4)}{Color.RST}")
    # 标题
    print(f"  {Color.BRAND}{Color.BLD}  {title}{Color.RST}")
    if subtitle:
        print(f"  {Color.DIM}  {subtitle}{Color.RST}")
    print()
    # 信息行
    info_parts = []
    if model:
        info_parts.append(f"Model: {model}")
    if tool_count:
        info_parts.append(f"Tools: {tool_count}")
    if info_parts:
        print(f"  {Color.DIM}  {'  |  '.join(info_parts)}{Color.RST}")
    # 额外信息
    if extra_info:
        for info in extra_info:
            print(f"  {Color.DIM}  {info}{Color.RST}")
    # 底部装饰线
    print(f"  {Color.BRAND}{sep * (width - 4)}{Color.RST}")
    print()


# ═══════════════════════════════════════════════════════════════════════
# 对 Claude Code 兼容：保留旧版函数名作为别名
# ═══════════════════════════════════════════════════════════════════════

print_claude_banner = print_claude_welcome
print_claude_thinking = print_agent_thinking
