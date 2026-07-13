"""
cli_input — 中文友好的 CLI 输入模块 (Cross-platform)

使用 prompt_toolkit 替代原生的 input()，解决中文输入时：
- ❌ 退格键需按两次才能删除一个中文字符
- ❌ 左右方向键在中文内容中导航异常
- ❌ 光标位置计算不正确

改用 prompt_toolkit 的 PromptSession 后：
- ✅ 一次退格删除一个完整中文字符（多字节 UTF-8）
- ✅ 左右方向键正确跳转到前/后一个字符位置
- ✅ 光标位置正确识别中文字符宽度（2列 vs 1列）
- ✅ 支持历史记录、Tab补全等高级功能
- ✅ 支持 ANSI 转义码渲染（彩色提示符）

## 回退方案

如果 prompt_toolkit 未安装，自动回退到基于 `msvcrt`（Windows）或
`termios`（Unix/Mac）的原始终端输入模式，同样正确处理：
- ✅ 方向键（左/右）移动光标
- ✅ 中文（多字节 UTF-8）退格删除
- ✅ Home/End 键
- ✅ Ctrl+C 退出
"""

import os
import sys
import re
import textwrap
from typing import Optional, List, Callable

# 尝试使用 prompt_toolkit（推荐，功能更完善）
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.formatted_text import ANSI as ANSIFormattedText
    HAVE_PROMPT_TOOLKIT = True
except ImportError:
    HAVE_PROMPT_TOOLKIT = False
    ANSIFormattedText = None  # type: ignore


# ========================================================================
# 自定义异常
# ========================================================================

class ExitRequested(BaseException):
    """用户在提示符处按下 Ctrl+C 时引发，表示请求退出程序

    与普通的 KeyboardInterrupt 不同，ExitRequested 仅在提示符等待输入时
    由 Ctrl+C 触发，表示用户希望直接退出程序。
    """
    pass


# ========================================================================
# 回退方案：基于 termios / msvcrt 的原始终端输入
# ========================================================================

def _is_windows() -> bool:
    """检查是否 Windows 系统"""
    return os.name == 'nt'


def _clear_line():
    """清除当前行并回到行首"""
    sys.stdout.write('\r\033[K')
    sys.stdout.flush()


def _render_input_line(prompt: str, buffer: str, cursor_pos: int):
    """重新渲染输入行（含 ANSI 提示符 + 输入缓冲区 + 光标位置）

    Args:
        prompt: 提示文本（可能含 ANSI 转义码）
        buffer: 当前输入缓冲区内容
        cursor_pos: 光标在缓冲区中的位置（字符索引）
    """
    # 计算输入缓冲区中光标前的可见宽度
    before_cursor = buffer[:cursor_pos]
    before_width = _get_string_visual_width(before_cursor)

    # 计算完整的可见宽度
    buffer_visible_width = _get_string_visual_width(buffer)

    # 清空当前行
    _clear_line()

    # 输出提示符 + 缓冲区内容
    sys.stdout.write(f"{prompt}{buffer}")

    # 计算需要回退的列数：
    # 光标应该位于 "提示符 + 光标前内容" 的位置
    # 总输出长度 = prompt_visible_width + buffer_visible_width
    # 光标位置 = prompt_visible_width + before_width
    # 需要回退的宽度 = 总输出宽度 - 光标列位置
    prompt_visible = re.sub(r'\033\[[0-9;]*m', '', prompt)
    prompt_width = len(prompt_visible)
    after_width = buffer_visible_width - before_width

    # 回退到光标位置
    if after_width > 0:
        sys.stdout.write('\b' * after_width)

    sys.stdout.flush()


def _get_string_visual_width(s: str) -> int:
    """获取字符串的可见宽度（中文字符算2列，英文字符算1列）

    在终端中，中文字符（CJK）通常占用2个英文字符的宽度。
    这个函数用于正确计算光标位置。

    Args:
        s: 输入字符串

    Returns:
        可见宽度（列数）
    """
    width = 0
    for ch in s:
        # CJK 统一表意文字区间
        if '\u4e00' <= ch <= '\u9fff' or \
           '\u3000' <= ch <= '\u303f' or \
           '\uff00' <= ch <= '\uffef' or \
           '\u2e80' <= ch <= '\u2eff' or \
           '\u2f00' <= ch <= '\u2fdf':
            width += 2  # 中日韩字符占2列
        else:
            width += 1
    return width


def _backspace_one_char(buffer: str, cursor_pos: int) -> tuple:
    """从缓冲区删除光标前的一个完整字符

    Python 字符串以 Unicode 字符为单位索引，所以 `buffer[:cursor_pos-1]`
    会自动正确处理多字节 UTF-8 字符（中文、Emoji 等）。

    Args:
        buffer: 当前缓冲区
        cursor_pos: 光标位置（字符索引）

    Returns:
        (new_buffer, new_cursor_pos)
    """
    if cursor_pos <= 0:
        return buffer, cursor_pos

    # Python 字符串切片基于 Unicode 字符位置，天然支持多字节字符
    i = cursor_pos - 1
    new_buffer = buffer[:i] + buffer[cursor_pos:]
    new_cursor_pos = i
    return new_buffer, new_cursor_pos


def _insert_into_buffer(buffer: str, cursor_pos: int, ch: str) -> tuple:
    """在光标位置插入字符

    Args:
        buffer: 当前缓冲区
        cursor_pos: 光标位置（字符索引）
        ch: 要插入的字符（支持多字节 UTF-8）

    Returns:
        (new_buffer, new_cursor_pos)
    """
    new_buffer = buffer[:cursor_pos] + ch + buffer[cursor_pos:]
    new_cursor_pos = cursor_pos + len(ch)
    return new_buffer, new_cursor_pos


def _raw_input_fallback(prompt: str = "") -> str:
    """回退方案：基于 termios/msvcrt 的原始终端输入

    在不依赖 prompt_toolkit 的情况下，直接读取终端按键输入，
    正确处理方向键（左/右）、中文（多字节 UTF-8）退格、Ctrl+C 等。

    ⚠️ 此回退方案为单行输入，不支持历史记录（↑/↓ 被忽略）。

    支持的按键：
    - 方向键 ← →：移动光标
    - Home / End：跳转到行首/行尾
    - Backspace：删除光标前的一个字符（支持多字节 UTF-8）
    - Enter：确认输入
    - Ctrl+C：退出（引发 ExitRequested）
    - Ctrl+D：退出（引发 ExitRequested）

    Returns:
        用户输入的字符串

    Raises:
        ExitRequested: 用户按下 Ctrl+C 或 Ctrl+D
    """
    # 输出提示符
    sys.stdout.write(prompt)
    sys.stdout.flush()

    buffer = ""
    cursor_pos = 0

    if _is_windows():
        # ── Windows: 使用 msvcrt ──
        import msvcrt
        while True:
            ch = msvcrt.getch()

            if ch == b'\r':  # Enter
                print()
                return buffer

            elif ch == b'\x03':  # Ctrl+C
                print("^C")
                raise ExitRequested()

            elif ch == b'\x04':  # Ctrl+D
                print("^D")
                raise ExitRequested()

            elif ch in (b'\x08', b'\x7f'):  # Backspace
                buffer, cursor_pos = _backspace_one_char(buffer, cursor_pos)
                _render_input_line(prompt, buffer, cursor_pos)

            elif ch == b'\xe0':  # 功能键前缀（方向键等）
                ch2 = msvcrt.getch()
                if ch2 == b'K':  # ← 左箭头
                    cursor_pos = max(0, cursor_pos - 1)
                    _render_input_line(prompt, buffer, cursor_pos)
                elif ch2 == b'M':  # → 右箭头
                    cursor_pos = min(len(buffer), cursor_pos + 1)
                    _render_input_line(prompt, buffer, cursor_pos)
                elif ch2 == b'H':  # Home
                    cursor_pos = 0
                    _render_input_line(prompt, buffer, cursor_pos)
                elif ch2 == b'F':  # End
                    cursor_pos = len(buffer)
                    _render_input_line(prompt, buffer, cursor_pos)
                # ↑/↓ (P/Q) 忽略，不支持历史记录

            elif ch[0] & 0x80:
                # 多字节 UTF-8 字符的第一个字节
                remaining = b''
                if ch[0] & 0xE0 == 0xC0:  # 2字节 UTF-8
                    remaining = msvcrt.getch()
                elif ch[0] & 0xF0 == 0xE0:  # 3字节 UTF-8（中文）
                    remaining = msvcrt.getch() + msvcrt.getch()
                elif ch[0] & 0xF8 == 0xF0:  # 4字节 UTF-8（Emoji）
                    remaining = (msvcrt.getch() + msvcrt.getch() +
                                 msvcrt.getch())

                try:
                    full_char = (ch + remaining).decode('utf-8')
                    buffer, cursor_pos = _insert_into_buffer(
                        buffer, cursor_pos, full_char
                    )
                    _render_input_line(prompt, buffer, cursor_pos)
                except (UnicodeDecodeError, IndexError):
                    pass  # 无效的 UTF-8 序列，忽略

            else:
                # ASCII 字符
                try:
                    char = ch.decode('utf-8')
                    buffer, cursor_pos = _insert_into_buffer(
                        buffer, cursor_pos, char
                    )
                    _render_input_line(prompt, buffer, cursor_pos)
                except UnicodeDecodeError:
                    pass

    else:
        # ── Unix/Mac: 使用 termios ──
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            tty.setraw(sys.stdin.fileno())

            while True:
                ch = sys.stdin.read(1)

                if ch in ('\r', '\n'):  # Enter
                    print()
                    break

                elif ch == '\x03':  # Ctrl+C
                    print("^C")
                    raise ExitRequested()

                elif ch == '\x04':  # Ctrl+D
                    print("^D")
                    raise ExitRequested()

                elif ch in ('\x7f', '\x08'):  # Backspace
                    buffer, cursor_pos = _backspace_one_char(
                        buffer, cursor_pos
                    )
                    _render_input_line(prompt, buffer, cursor_pos)

                elif ch == '\x1b':  # Escape sequence 开始
                    seq = ch + sys.stdin.read(2)
                    if seq == '\x1b[D':  # ← 左箭头
                        cursor_pos = max(0, cursor_pos - 1)
                        _render_input_line(prompt, buffer, cursor_pos)
                    elif seq == '\x1b[C':  # → 右箭头
                        cursor_pos = min(len(buffer), cursor_pos + 1)
                        _render_input_line(prompt, buffer, cursor_pos)
                    elif seq == '\x1b[H':  # Home
                        cursor_pos = 0
                        _render_input_line(prompt, buffer, cursor_pos)
                    elif seq == '\x1b[F':  # End
                        cursor_pos = len(buffer)
                        _render_input_line(prompt, buffer, cursor_pos)
                    elif seq == '\x1b[A':  # ↑ 上箭头（忽略）
                        pass
                    elif seq == '\x1b[B':  # ↓ 下箭头（忽略）
                        pass
                    elif seq == '\x1b[3':  # Delete 键
                        more = sys.stdin.read(1)
                        if more == '~' and cursor_pos < len(buffer):
                            buffer = (buffer[:cursor_pos] +
                                      buffer[cursor_pos + 1:])
                            _render_input_line(prompt, buffer, cursor_pos)
                    elif seq == '\x1b[1':  # Home (xterm)
                        more = sys.stdin.read(1)
                        if more == '~':
                            cursor_pos = 0
                            _render_input_line(prompt, buffer, cursor_pos)
                    elif seq == '\x1b[4':  # End (xterm)
                        more = sys.stdin.read(1)
                        if more == '~':
                            cursor_pos = len(buffer)
                            _render_input_line(prompt, buffer, cursor_pos)
                    # 其他序列忽略

                else:
                    # 多字节 UTF-8 字符
                    byte_data = ch.encode('utf-8')
                    if byte_data[0] & 0x80:
                        remaining_bytes = 0
                        if byte_data[0] & 0xE0 == 0xC0:
                            remaining_bytes = 1
                        elif byte_data[0] & 0xF0 == 0xE0:
                            remaining_bytes = 2
                        elif byte_data[0] & 0xF8 == 0xF0:
                            remaining_bytes = 3

                        for _ in range(remaining_bytes):
                            byte_data += sys.stdin.read(1).encode('utf-8')

                    try:
                        char = byte_data.decode('utf-8')
                        buffer, cursor_pos = _insert_into_buffer(
                            buffer, cursor_pos, char
                        )
                        _render_input_line(prompt, buffer, cursor_pos)
                    except (UnicodeDecodeError, IndexError):
                        pass  # 无效的 UTF-8 序列，忽略

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return buffer


# ========================================================================
# 中文友好的 input 替代函数
# ========================================================================

# 全局 PromptSession 实例（支持历史记录）
_session = None
_session_history = None


def _get_session() -> "PromptSession":
    """获取或创建全局 PromptSession 实例"""
    global _session, _session_history
    if _session is None:
        _session_history = InMemoryHistory()
        _session = PromptSession(
            history=_session_history,
            enable_history_search=True,
            vi_mode=False,
            complete_while_typing=False,
        )
    return _session


def _format_prompt(prompt: str):
    """将提示文本包装为 ANSI 格式化文本

    prompt_toolkit 默认将 prompt 作为纯文本处理，会转义 ANSI 转义码
    （如 \033[96m 显示为 ^[[96m）。使用 ANSIFormattedText 包装后，
    prompt_toolkit 能正确解析并渲染 ANSI 颜色/样式。

    如果 prompt 中不包含 ANSI 码，则直接返回原字符串（无额外开销）。

    Args:
        prompt: 可能包含 ANSI 转义码的提示字符串

    Returns:
        ANSIFormattedText 或原始字符串
    """
    if HAVE_PROMPT_TOOLKIT and '\033' in prompt:
        return ANSIFormattedText(prompt)
    return prompt


def chinese_input(
    prompt: str = "",
    password: bool = False,
    default: str = "",
    multiline: bool = False,
) -> str:
    """中文友好的输入函数，替代内置的 input()

    使用 prompt_toolkit 处理用户输入，正确处理多字节 UTF-8 字符
    （中文、日文、韩文、Emoji 等）。

    如果 prompt_toolkit 不可用，自动回退到基于 termios/msvcrt 的
    原始终端输入模式，同样支持：
    - 方向键 ← → 移动光标
    - Home/End 跳转行首/行尾
    - 中文退格删除（删除完整字符）
    - Ctrl+C 退出

    特性：
    - 退格键一次删除一个完整中文字符
    - 左右方向键正确导航
    - 光标位置正确计算
    - 支持历史记录（上下方向键浏览）[prompt_toolkit]
    - 支持密码模式（输入不回显）[prompt_toolkit]
    - 支持多行输入 [prompt_toolkit]
    - 支持 ANSI 转义码（彩色提示符）

    Args:
        prompt: 提示文本（支持 ANSI 转义码）
        password: 是否密码模式（输入不回显）
        default: 默认值
        multiline: 是否支持多行输入

    Returns:
        用户输入的字符串

    Raises:
        ExitRequested: 用户在提示符处按下 Ctrl+C 时引发，表示请求退出程序
    """
    if not HAVE_PROMPT_TOOLKIT:
        # 回退到原始终端输入模式（正确处理方向键、中文退格等）
        try:
            if password:
                # 密码模式：使用 getpass 隐藏输入
                import getpass
                user_input = getpass.getpass(prompt)
            elif multiline:
                user_input = _raw_multiline_fallback(prompt)
            else:
                user_input = _raw_input_fallback(prompt)
                if default and not user_input:
                    user_input = default
            return user_input.strip() if not multiline else user_input
        except EOFError:
            raise ExitRequested() from None
        except KeyboardInterrupt:
            raise ExitRequested() from None

    try:
        session = _get_session()
        formatted_prompt = _format_prompt(prompt)

        if multiline:
            user_input = session.prompt(
                formatted_prompt,
                multiline=True,
            )
        elif password:
            user_input = session.prompt(
                formatted_prompt,
                is_password=True,
                default=default,
            )
        else:
            user_input = session.prompt(
                formatted_prompt,
                default=default,
            )

        return user_input.strip() if not multiline else user_input

    except EOFError:
        raise ExitRequested() from None
    except KeyboardInterrupt:
        raise ExitRequested() from None


def _raw_multiline_fallback(prompt: str = "") -> str:
    """多行输入回退（逐行读取直到空行）

    Args:
        prompt: 提示文本

    Returns:
        多行文本

    Raises:
        ExitRequested: 用户按下 Ctrl+C
    """
    print(f"{prompt} (输入空行结束多行输入)")
    lines = []
    while True:
        try:
            line = _raw_input_fallback("  > ")
            if not line:
                break
            lines.append(line)
        except ExitRequested:
            raise
    return "\n".join(lines)


def chinese_input_simple(prompt: str = "") -> str:
    """简单的中文输入，无历史记录、无默认值

    适合简单的 yes/no 确认等场景。

    Args:
        prompt: 提示文本（支持 ANSI 转义码）

    Returns:
        用户输入的字符串

    Raises:
        ExitRequested: 用户在提示符处按下 Ctrl+C 时引发
    """
    return chinese_input(prompt=prompt)


def chinese_confirm(prompt: str = "", default: bool = True) -> bool:
    """中文友好的确认输入

    Args:
        prompt: 提示文本
        default: 默认选择

    Returns:
        用户的选择（True/False）

    Raises:
        ExitRequested: 用户在提示符处按下 Ctrl+C 时引发
    """
    hint = " [Y/n]" if default else " [y/N]"
    full_prompt = f"{prompt}{hint}: "

    while True:
        result = chinese_input(full_prompt).strip().lower()

        if not result:
            return default

        if result in ("y", "yes", "是", "确认", "对", "true", "1"):
            return True
        elif result in ("n", "no", "否", "取消", "错", "false", "0"):
            return False
        else:
            print(f"  请输入 y 或 n", file=sys.stderr)


# ========================================================================
# 兼容层：直接替换 input()
# ========================================================================

def patch_input():
    """将内置的 input() 替换为中文友好的版本

    调用后，所有使用 input() 的代码自动获得中文输入支持。
    但注意：一些依赖 input() 特殊行为的第三方库可能受影响。

    建议在项目入口处调用：
        import cli_input
        cli_input.patch_input()
    """
    import builtins
    builtins.input = chinese_input


# ========================================================================
# 测试函数
# ========================================================================

def test_chinese_input():
    """测试中文输入功能"""
    print("\n" + "=" * 60)
    print("  🧪 Chinese Input Test")
    print("  ⚠️  请测试以下场景：")
    print("=" * 60)

    print("\n📝 测试 1: 基本中文输入")
    print("  输入一些中文，然后按退格键删除")
    text1 = chinese_input("  >> ")
    print(f"  输入内容: [{text1}]")
    print(f"  字符数: {len(text1)}")
    print(f"  字节数: {len(text1.encode('utf-8'))}")

    print("\n📝 测试 2: 带默认值")
    text2 = chinese_input("  >> ", default="你好世界")
    print(f"  输入内容: [{text2}]")

    print("\n📝 测试 3: 密码模式")
    text3 = chinese_input("  >> ", password=True)
    print(f"  输入内容: [{text3}]")

    print("\n📝 测试 4: 中英文混合")
    print("  试试输入: Hello 你好 World 世界 Test 测试")
    text4 = chinese_input("  >> ")
    print(f"  输入内容: [{text4}]")

    print("\n📝 测试 5: Emoji 测试")
    text5 = chinese_input("  >> ")
    print(f"  输入内容: [{text5}]")

    print("\n📝 测试 6: ANSI 彩色提示符")
    text6 = chinese_input("\033[96m\033[1m💬 You\033[0m \033[2m>\033[0m ")
    print(f"  输入内容: [{text6}]")

    print("\n" + "=" * 60)
    print("  ✅ 测试完成")
    print("=" * 60 + "\n")


def test_raw_fallback():
    """测试 raw input fallback 功能（无 prompt_toolkit 时使用）"""
    print("\n" + "=" * 60)
    print("  🧪 Raw Input Fallback Test")
    print("  ⚠️  请测试以下场景：")
    print("=" * 60)

    print("\n📝 测试 1: 基本输入（方向键 ← → 移动光标）")
    print("  输入一些文字后，按方向键移动光标到中间再继续输入")
    text1 = _raw_input_fallback("  >> ")
    print(f"  输入内容: [{text1}]")

    print("\n📝 测试 2: 中文输入")
    print("  输入中英文混合字符，测试退格键和方向键")
    text2 = _raw_input_fallback("  >> ")
    print(f"  输入内容: [{text2}]")

    print("\n" + "=" * 60)
    print("  ✅ 测试完成")
    print("=" * 60 + "\n")


# ========================================================================
# 当直接运行时执行测试
# ========================================================================

if __name__ == "__main__":
    if HAVE_PROMPT_TOOLKIT:
        test_chinese_input()
    else:
        print(f"\n  ⚠️  prompt_toolkit 未安装，使用回退模式测试")
        test_raw_fallback()
