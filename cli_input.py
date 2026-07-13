"""
cli_input — 中文友好的 CLI 输入模块

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
"""

import sys
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

    特性：
    - 退格键一次删除一个完整中文字符
    - 左右方向键正确导航
    - 光标位置正确计算
    - 支持历史记录（上下方向键浏览）
    - 支持密码模式（输入不回显）
    - 支持多行输入
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
        # 回退到原生 input()（有中文 bug，但至少能工作）
        try:
            user_input = input(prompt)
            return user_input.strip()
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


# ========================================================================
# 当直接运行时执行测试
# ========================================================================

if __name__ == "__main__":
    test_chinese_input()
