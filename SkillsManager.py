"""
SkillsManager - 技能管理 Agent

管理 AgentSkills 包中的所有技能（工具函数），
支持查看、创建、编辑、删除和测试各项技能。
调用 deepseek-v4-flash 模型，以对话方式完成管理操作。
"""

import os
import re
import sys
import json
import shutil
import importlib
import subprocess
from typing import Optional
from pathlib import Path
from datetime import datetime

from openai import OpenAI
from dotenv import load_dotenv

# ========================================================================
# 加载环境变量与初始化 DeepSeek 客户端
# ========================================================================

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

MODEL = "deepseek-v4-flash"

# AgentSkills 包路径
AGENT_SKILLS_DIR = Path(__file__).parent / "AgentSkills"
TOOLS_DIR = AGENT_SKILLS_DIR / "tools"
CORE_DIR = AGENT_SKILLS_DIR / "core"

# ========================================================================
# CLI 样式定义（ANSI 转义码，零依赖）
# ========================================================================

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

    # 语义化颜色别名
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


def print_panel(
    content: str,
    title: str = "",
    color: str = "",
    width: Optional[int] = None,
    border_style: str = "rounded",
) -> None:
    """打印一个带标题的圆角/直角面板框

    border_style: "rounded" = ╭╮╰╯, "square" = ┌┐└┘
    """
    if width is None:
        width = min(get_term_width() - 2, 100)
    # 保证最小宽度
    width = max(width, 40)

    # 边框字符
    if border_style == "rounded":
        tl, tr, bl, br = "╭", "╮", "╰", "╯"
    else:
        tl, tr, bl, br = "┌", "┐", "└", "┘"

    h = "─"
    v = "│"

    # 构建标题部分
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

    # 内容行
    for line in content.split("\n"):
        # 计算可见宽度（去除 ANSI 码）
        visible = re.sub(r'\033\[[0-9;]*m', '', line)
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

    # 构建内容
    content_parts = [
        f"{Color.BLD}📌 工具:{Color.RST} {Color.BCYN}{tool_name}{Color.RST}",
        f"{Color.BLD}📥 参数:{Color.RST} {Color.DIM}{truncate_text(args_str, 60)}{Color.RST}",
    ]

    # 如果有详细参数且需要展示
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


# ========================================================================
# 1. 工具函数定义
# ========================================================================

# ─── 通用文件操作（复用 AgentSkills 的工具） ───

def read_file(file_path: str) -> str:
    """读取指定文件的内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(file_path: str, content: str) -> str:
    """将内容写入指定文件（覆盖写入），自动创建父目录"""
    try:
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


# ─── 技能管理工具 ───

def _discover_skill_files() -> dict:
    """扫描 AgentSkills/tools/ 目录，发现所有技能文件

    Returns:
        {模块名: 文件路径} 的字典
    """
    skill_files = {}
    if not TOOLS_DIR.exists():
        return skill_files
    for f in sorted(TOOLS_DIR.iterdir()):
        if f.suffix == ".py" and f.name != "__init__.py":
            module_name = f.stem
            skill_files[module_name] = str(f)
    return skill_files


def _get_tool_functions_from_init() -> dict:
    """从 AgentSkills/tools/__init__.py 中提取导出的工具函数

    Returns:
        {函数名: 所属模块} 的字典
    """
    init_path = TOOLS_DIR / "__init__.py"
    if not init_path.exists():
        return {}
    content = init_path.read_text(encoding="utf-8")

    result = {}
    # 匹配 from .xxx import ( ... ) 或 from .xxx import func1, func2
    # 多行导入
    for match in re.finditer(
        r'from\s+\.(\w+)\s+import\s+\((.+?)\)', content, re.DOTALL
    ):
        module = match.group(1)
        names = re.findall(r'(\w+)', match.group(2))
        for name in names:
            result[name] = module

    # 单行导入（如 from .xxx import func1, func2）
    # 匹配行末（不跨行），排除多行导入（有括号的情况）
    for match in re.finditer(
        r'from\s+\.(\w+)\s+import\s+([^(][^\n#]+)', content
    ):
        module = match.group(1)
        names_str = match.group(2).strip().rstrip(",")
        names = [n.strip() for n in names_str.split(",") if n.strip()]
        for name in names:
            if name and name not in result:
                result[name] = module

    # __all__ 中的顺序
    all_match = re.search(r'__all__\s*=\s*\[(.+?)\]', content, re.DOTALL)
    if all_match:
        all_names = re.findall(r'"(\w+)"', all_match.group(1))
        # 按 __all__ 排序
        sorted_result = {}
        for name in all_names:
            if name in result:
                sorted_result[name] = result[name]
        # 添加不在 __all__ 中的
        for name in result:
            if name not in sorted_result:
                sorted_result[name] = result[name]
        result = sorted_result

    return result


def _extract_function_info(file_path: str, func_name: str) -> Optional[dict]:
    """从 Python 文件中提取指定函数的信息

    Args:
        file_path: Python 文件路径
        func_name: 函数名

    Returns:
        {name, docstring, code, params} 或 None
    """
    try:
        content = Path(file_path).read_text(encoding="utf-8")
    except Exception:
        return None

    # 查找函数定义
    pattern = rf'(def\s+{re.escape(func_name)}\s*\([^)]*\)\s*(?:->\s*[^:]*)?:.*?)(?=\n\S|\Z)'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return None

    code = match.group(1).strip()

    # 提取 docstring
    doc_match = re.search(
        rf'def\s+{re.escape(func_name)}\s*\([^)]*\)\s*(?:->\s*[^:]*)?:\s*"""(.+?)"""',
        content, re.DOTALL
    )
    docstring = doc_match.group(1).strip() if doc_match else ""

    # 提取参数
    params_match = re.search(
        rf'def\s+{re.escape(func_name)}\s*\(([^)]*)\)', content
    )
    params_str = params_match.group(1).strip() if params_match else ""
    params = [p.strip() for p in params_str.split(",") if p.strip()]

    return {
        "name": func_name,
        "docstring": docstring,
        "code": code,
        "params": params,
        "file": file_path,
    }


def _extract_tool_schema(tools_module, func_name: str) -> Optional[dict]:
    """从 Agent 的 tools 定义中查找某个函数的 JSON Schema

    Args:
        tools_module: 包含 TOOLS_SCHEMA 的模块
        func_name: 函数名

    Returns:
        schema dict 或 None
    """
    try:
        schema_list = tools_module.TOOLS_SCHEMA
        for item in schema_list:
            if item.get("function", {}).get("name") == func_name:
                return item
    except AttributeError:
        pass
    return None


def list_skills(detail: bool = False) -> str:
    """列出 AgentSkills 中所有可用的技能（工具函数）

    Args:
        detail: 是否显示详细信息（包括 docstring 和参数）

    Returns:
        格式化的技能列表
    """
    skill_files = _discover_skill_files()
    exported = _get_tool_functions_from_init()

    if not exported:
        return "⚠️ 未发现任何导出的技能函数。"

    lines = [f"📦 AgentSkills 技能清单（共 {len(exported)} 项）\n"]

    # 按模块分组
    module_groups = {}
    for func_name, module_name in exported.items():
        module_groups.setdefault(module_name, []).append(func_name)

    for module_name, func_names in module_groups.items():
        file_path = skill_files.get(module_name, "未知文件")
        lines.append(f"📁 模块: {module_name}.py")
        if detail:
            lines.append(f"   文件: {file_path}")

        for func_name in func_names:
            info = _extract_function_info(file_path, func_name)
            if info and detail:
                lines.append(f"\n  🔧 {func_name}")
                lines.append(f"     参数: {', '.join(info['params'])}")
                if info["docstring"]:
                    # 只显示第一行
                    first_line = info["docstring"].split("\n")[0]
                    lines.append(f"     说明: {first_line}")
            else:
                lines.append(f"  🔧 {func_name}")

        lines.append("")

    return "\n".join(lines).strip()


def view_skill(skill_name: str) -> str:
    """查看某个技能的详细信息

    Args:
        skill_name: 技能（函数）名称

    Returns:
        技能的详细信息，包括代码、参数、docstring 和 schema
    """
    exported = _get_tool_functions_from_init()

    if skill_name not in exported:
        available = ", ".join(sorted(exported.keys()))
        return f"❌ 未找到技能 '{skill_name}'。\n可用技能: {available}"

    module_name = exported[skill_name]
    skill_files = _discover_skill_files()
    file_path = skill_files.get(module_name, "")

    if not file_path:
        return f"❌ 找不到技能 '{skill_name}' 对应的文件。"

    info = _extract_function_info(file_path, skill_name)
    if not info:
        return f"❌ 无法解析技能 '{skill_name}' 的代码。"

    lines = [f"🔍 技能详情: {skill_name}", "=" * 50]
    lines.append(f"📁 所在文件: {info['file']}")
    lines.append(f"📝 参数: {', '.join(info['params'])}")

    if info["docstring"]:
        lines.append(f"\n📖 说明:\n{info['docstring']}")

    lines.append(f"\n💻 代码:\n{info['code']}")

    # 尝试获取 schema
    try:
        from AgentSkills.core import agent as agent_module
        schema = _extract_tool_schema(agent_module, skill_name)
        if schema:
            lines.append(f"\n📋 JSON Schema:\n{json.dumps(schema, ensure_ascii=False, indent=2)}")
    except Exception:
        pass

    return "\n".join(lines)


def create_skill(
    skill_name: str,
    module_name: str,
    code: str,
    update_init: bool = True,
) -> str:
    """创建一个新的技能

    在 AgentSkills/tools/ 下的指定模块中创建一个新的工具函数，
    并可选择更新 __init__.py 导出列表。

    Args:
        skill_name: 新技能的函数名（如 'my_new_tool'）
        module_name: 要添加到哪个模块文件（不含 .py，如 'file_ops'）
        code: 完整的函数定义代码（包括 def 和 docstring）
        update_init: 是否自动更新 __init__.py 的导出列表（默认 True）

    Returns:
        创建结果信息
    """
    target_file = TOOLS_DIR / f"{module_name}.py"

    # 检查技能名是否已存在
    exported = _get_tool_functions_from_init()
    if skill_name in exported:
        return f"❌ 技能 '{skill_name}' 已存在。如需修改请使用 update_skill。"

    # 检查目标模块是否存在
    if not target_file.exists():
        return f"❌ 模块 '{module_name}.py' 不存在。可用模块: {', '.join(sorted(_discover_skill_files().keys()))}"

    # 检查代码格式
    if not code.strip().startswith("def "):
        return "❌ 代码必须以 'def function_name(...):' 开头。"

    # 检查函数名是否匹配
    name_in_code = re.search(r'def\s+(\w+)\s*\(', code)
    if not name_in_code or name_in_code.group(1) != skill_name:
        return f"❌ 代码中的函数名 '{name_in_code.group(1) if name_in_code else 'N/A'}' 与指定的 skill_name '{skill_name}' 不匹配。"

    # 语法检查
    import tempfile
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(code)
        tmp.close()
        result = subprocess.run(
            ["python", "-m", "py_compile", tmp.name],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return f"❌ Python 语法错误:\n{result.stderr}"
    finally:
        os.unlink(tmp.name)

    # 追加代码到模块文件
    try:
        with open(target_file, "a", encoding="utf-8") as f:
            f.write(f"\n\n{code.strip()}\n")
    except Exception as e:
        return f"❌ 写入文件失败: {e}"

    # 更新 __init__.py
    if update_init:
        init_file = TOOLS_DIR / "__init__.py"
        try:
            init_content = init_file.read_text(encoding="utf-8")

            # 添加 import 语句
            import_line = f"from .{module_name} import (\n    {skill_name},\n)"
            # 在对应的 from import 块中添加
            pattern = rf'(from\s+\.{module_name}\s+import\s*\()'
            match = re.search(pattern, init_content)
            if match:
                # 找到对应模块的 import 块，追加函数名
                block_start = match.start()
                block_end = re.search(r'\)', init_content[block_start:]).start() + block_start
                block = init_content[block_start:block_end]
                # 在最后一个逗号或括号前插入
                new_block = block.rstrip()
                if new_block.endswith(")"):
                    new_block = new_block[:-1] + f"    {skill_name},\n)"
                elif new_block.endswith(","):
                    new_block = new_block + f"\n    {skill_name},"
                else:
                    new_block = new_block + f",\n    {skill_name},"
                init_content = init_content[:block_start] + new_block + init_content[block_end:]
            else:
                # 没有对应的 import 块，追加到文件末尾
                init_content += f"\n{import_line}\n"

            # 更新 __all__
            all_pattern = r'(__all__\s*=\s*\[)(.+?)(\])'
            all_match = re.search(all_pattern, init_content, re.DOTALL)
            if all_match:
                all_body = all_match.group(2).strip()
                new_all_body = all_body.rstrip(",") + f",\n    \"{skill_name}\",\n"
                init_content = (
                    init_content[:all_match.start(2)]
                    + new_all_body
                    + init_content[all_match.end(2):]
                )

            init_file.write_text(init_content, encoding="utf-8")
            init_msg = f"✅ __init__.py 已更新导出列表。"
        except Exception as e:
            init_msg = f"⚠️ 写入 __init__.py 失败: {e}（需要手动更新）"
    else:
        init_msg = "⏭️ __init__.py 未更新（update_init=False）"

    return (
        f"✅ 技能 '{skill_name}' 创建成功！\n"
        f"📁 已添加到: {target_file}\n"
        f"{init_msg}\n\n"
        f"💡 提示：创建新技能后，还需在 Agent 的 TOOLS_SCHEMA 和 TOOL_FUNCTIONS "
        f"中添加对应的 JSON Schema 和函数引用才能生效。"
    )


def update_skill(skill_name: str, code: str) -> str:
    """更新一个已有技能的代码

    Args:
        skill_name: 要更新的技能（函数）名称
        code: 新的函数定义代码（会替换原函数的全部内容）

    Returns:
        更新结果信息
    """
    exported = _get_tool_functions_from_init()

    if skill_name not in exported:
        available = ", ".join(sorted(exported.keys()))
        return f"❌ 未找到技能 '{skill_name}'。\n可用技能: {available}"

    module_name = exported[skill_name]
    skill_files = _discover_skill_files()
    file_path = skill_files.get(module_name)

    if not file_path:
        return f"❌ 找不到技能 '{skill_name}' 对应的文件。"

    # 检查代码格式
    name_in_code = re.search(r'def\s+(\w+)\s*\(', code)
    if not name_in_code:
        return "❌ 代码必须以 'def function_name(...):' 开头。"
    if name_in_code.group(1) != skill_name:
        return f"❌ 代码中的函数名 '{name_in_code.group(1)}' 与指定的 skill_name '{skill_name}' 不匹配。"

    # 语法检查
    import tempfile
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(code)
        tmp.close()
        result = subprocess.run(
            ["python", "-m", "py_compile", tmp.name],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return f"❌ Python 语法错误:\n{result.stderr}"
    finally:
        os.unlink(tmp.name)

    # 读取原文件
    try:
        original = Path(file_path).read_text(encoding="utf-8")
    except Exception as e:
        return f"❌ 读取文件失败: {e}"

    # 替换函数定义
    # 匹配从 def func_name 到下一个 def/类/文件末尾
    pattern = rf'(def\s+{re.escape(skill_name)}\s*\([^)]*\)\s*(?:->\s*[^:]*)?:.*?)(?=\n\s*(?:def\s+|class\s+|\Z))'
    new_content = re.sub(pattern, code.strip(), original, count=1, flags=re.DOTALL)

    if new_content == original:
        # 尝试更宽松的匹配（处理文件末尾没有换行的情况）
        pattern2 = rf'(def\s+{re.escape(skill_name)}\s*\([^)]*\)\s*(?:->\s*[^:]*)?:.*?)(?=\Z)'
        new_content = re.sub(pattern2, code.strip(), original, count=1, flags=re.DOTALL)

    if new_content == original:
        return f"❌ 无法在文件中定位技能 '{skill_name}' 的定义。"

    # 写回文件
    try:
        Path(file_path).write_text(new_content, encoding="utf-8")
    except Exception as e:
        return f"❌ 写入文件失败: {e}"

    return (
        f"✅ 技能 '{skill_name}' 更新成功！\n"
        f"📁 文件: {file_path}\n"
        f"💡 提示：如果函数的参数签名发生了变化，请同步更新 "
        f"Agent 中 TOOLS_SCHEMA 和 TOOL_FUNCTIONS 的对应条目。"
    )


def delete_skill(skill_name: str, remove_from_init: bool = True) -> str:
    """删除一个技能

    从对应的模块文件中移除函数定义，
    并可选择从 __init__.py 导出列表中移除。

    Args:
        skill_name: 要删除的技能（函数）名称
        remove_from_init: 是否同时从 __init__.py 移除导出（默认 True）

    Returns:
        删除结果信息
    """
    exported = _get_tool_functions_from_init()

    if skill_name not in exported:
        available = ", ".join(sorted(exported.keys()))
        return f"❌ 未找到技能 '{skill_name}'。\n可用技能: {available}"

    module_name = exported[skill_name]
    skill_files = _discover_skill_files()
    file_path = skill_files.get(module_name)

    if not file_path:
        return f"❌ 找不到技能 '{skill_name}' 对应的文件。"

    # 读取原文件
    try:
        original = Path(file_path).read_text(encoding="utf-8")
    except Exception as e:
        return f"❌ 读取文件失败: {e}"

    # 删除函数定义
    pattern = rf'\n\n\s*(def\s+{re.escape(skill_name)}\s*\([^)]*\)\s*(?:->\s*[^:]*)?:.*?)(?=\n\s*(?:def\s+|class\s+|\Z))'
    new_content = re.sub(pattern, "", original, count=1, flags=re.DOTALL)

    if new_content == original:
        # 尝试文件开头的函数
        pattern2 = rf'^(def\s+{re.escape(skill_name)}\s*\([^)]*\)\s*(?:->\s*[^:]*)?:.*?)(?=\n\s*(?:def\s+|class\s+|\Z))'
        new_content = re.sub(pattern2, "", original, count=1, flags=re.DOTALL)

    if new_content == original:
        return f"❌ 无法在文件中定位技能 '{skill_name}' 的定义，请手动删除。"

    # 清理多余的空行
    new_content = re.sub(r'\n{3,}', '\n\n', new_content).strip()
    if new_content:
        new_content += "\n"

    # 写回文件
    try:
        Path(file_path).write_text(new_content, encoding="utf-8")
    except Exception as e:
        return f"❌ 写入文件失败: {e}"

    # 更新 __init__.py
    init_msgs = []
    if remove_from_init:
        init_file = TOOLS_DIR / "__init__.py"
        try:
            init_content = init_file.read_text(encoding="utf-8")

            # 从 import 语句中移除
            pattern_import = rf'from\s+\.{module_name}\s+import\s*\(([^)]+)\)'
            match = re.search(pattern_import, init_content, re.DOTALL)
            if match:
                imports = match.group(1)
                new_imports = re.sub(
                    rf'\s*{re.escape(skill_name)}\s*,?\s*',
                    '',
                    imports
                )
                new_imports = re.sub(r',\s*,', ',', new_imports)
                new_imports = new_imports.strip().strip(',')
                if new_imports:
                    new_block = f"from .{module_name} import (\n{new_imports}\n)"
                else:
                    new_block = ""
                init_content = init_content[:match.start()] + new_block + init_content[match.end():]

            # 从 __all__ 中移除
            all_pattern = r'(__all__\s*=\s*\[)(.+?)(\])'
            all_match = re.search(all_pattern, init_content, re.DOTALL)
            if all_match:
                all_body = all_match.group(2)
                new_all_body = re.sub(
                    rf'\s*"{re.escape(skill_name)}"\s*,?\s*',
                    '',
                    all_body
                )
                new_all_body = re.sub(r',\s*,', ',', new_all_body).strip().strip(',')
                if new_all_body:
                    new_all_body = '\n    ' + ',\n    '.join(
                        f'"{n.strip()}"' for n in new_all_body.replace('"', '').split(',') if n.strip()
                    ) + ',\n'
                    init_content = (
                        init_content[:all_match.start(2)]
                        + new_all_body
                        + init_content[all_match.end(2):]
                    )

            # 清理多余空行
            init_content = re.sub(r'\n{3,}', '\n\n', init_content)

            init_file.write_text(init_content, encoding="utf-8")
            init_msgs.append("✅ __init__.py 已更新。")
        except Exception as e:
            init_msgs.append(f"⚠️ 更新 __init__.py 失败: {e}")

    return (
        f"✅ 技能 '{skill_name}' 已删除！\n"
        f"📁 已从 {file_path} 中移除。\n" +
        "\n".join(init_msgs) +
        "\n\n💡 提示：如果该技能在 Agent 的 TOOLS_SCHEMA 和 TOOL_FUNCTIONS "
        "中有注册，请同步清理对应条目。"
    )


def test_skill(skill_name: str, **kwargs) -> str:
    """测试调用一个技能函数

    使用给定的参数调用指定的技能函数，并返回执行结果。

    Args:
        skill_name: 要测试的技能名称
        **kwargs: 传递给技能函数的参数

    Returns:
        函数执行结果
    """
    # 动态导入工具模块
    try:
        sys.path.insert(0, str(AGENT_SKILLS_DIR.parent))
        from AgentSkills.skills import (
            read_file as _read_file,
            write_file as _write_file,
            delete_file as _delete_file,
            delete_directory as _delete_directory,
            list_directory as _list_directory,
            create_directory as _create_directory,
            run_shell_command as _run_shell_command,
            check_python_syntax as _check_python_syntax,
            check_yaml_syntax as _check_yaml_syntax,
            check_html_syntax as _check_html_syntax,
            check_css_syntax as _check_css_syntax,
            check_js_syntax as _check_js_syntax,
            web_search as _web_search,
            web_search_and_open as _web_search_and_open,
        )
    except Exception as e:
        return f"❌ 导入 AgentSkills 失败: {e}"

    # 函数映射
    tool_map = {
        "read_file": _read_file,
        "write_file": _write_file,
        "delete_file": _delete_file,
        "delete_directory": _delete_directory,
        "list_directory": _list_directory,
        "create_directory": _create_directory,
        "run_shell_command": _run_shell_command,
        "check_python_syntax": _check_python_syntax,
        "check_yaml_syntax": _check_yaml_syntax,
        "check_html_syntax": _check_html_syntax,
        "check_css_syntax": _check_css_syntax,
        "check_js_syntax": _check_js_syntax,
        "web_search": web_search,
        "web_search_and_open": web_search_and_open,
    }

    # 也包含当前模块中定义的函数
    local_map = {
        "list_skills": list_skills,
        "view_skill": view_skill,
        "create_skill": create_skill,
        "update_skill": update_skill,
        "delete_skill": delete_skill,
        "test_skill": test_skill,
    }

    func = tool_map.get(skill_name) or local_map.get(skill_name)
    if func is None:
        # 尝试从 AgentSkills 动态导入
        exported = _get_tool_functions_from_init()
        if skill_name not in exported:
            available = ", ".join(sorted(set(list(tool_map.keys()) + list(local_map.keys()) + list(exported.keys()))))
            return f"❌ 未找到技能 '{skill_name}'。\n可用技能: {available}"

        module_name = exported[skill_name]
        try:
            mod = importlib.import_module(f"AgentSkills.skills.{module_name}")
            func = getattr(mod, skill_name, None)
            if func is None:
                return f"❌ 在模块 '{module_name}' 中未找到函数 '{skill_name}'。"
        except Exception as e:
            return f"❌ 导入失败: {e}"

    # 执行函数
    try:
        result = func(**kwargs)
        return str(result)
    except TypeError as e:
        return f"❌ 参数错误: {e}\n💡 请检查传入的参数是否与函数签名匹配。"
    except Exception as e:
        return f"❌ 执行出错: {e}"


def web_search(query: str, max_results: int = 5) -> str:
    """通过 Bing 搜索互联网，返回标题、链接和摘要"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from AgentSkills.skills.web_search import web_search as _do_search
        return _do_search(query=query, max_results=max_results)
    except ImportError:
        result = subprocess.run(
            [sys.executable, "-c",
             f"""
import sys
sys.path.insert(0, '{Path(__file__).parent}')
from AgentSkills.skills.web_search import web_search
print(web_search(query={json.dumps(query)}, max_results={max_results}))
"""],
            capture_output=True, text=True, timeout=30,
        )
        return (result.stdout + result.stderr).strip()


def web_search_and_open(
    query: str,
    max_results: int = 5,
    fetch_content: bool = True,
    max_content_length: int = 2000,
) -> str:
    """搜索互联网并获取第一条结果的页面正文内容"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from AgentSkills.skills.web_search import web_search_and_open as _do_search_open
        return _do_search_open(
            query=query, max_results=max_results,
            fetch_content=fetch_content,
            max_content_length=max_content_length,
        )
    except ImportError:
        result = subprocess.run(
            [sys.executable, "-c",
             f"""
import sys
sys.path.insert(0, '{Path(__file__).parent}')
from AgentSkills.skills.web_search import web_search_and_open
print(web_search_and_open(
    query={json.dumps(query)},
    max_results={max_results},
    fetch_content={json.dumps(fetch_content)},
    max_content_length={max_content_length},
))
"""],
            capture_output=True, text=True, timeout=30,
        )
        return (result.stdout + result.stderr).strip()


# ========================================================================
# 2. 工具的 JSON Schema
# ========================================================================

tools = [
    # ─── 技能管理工具 ───
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "列出 AgentSkills 中所有可用的技能（工具函数），支持简单模式和详细模式",
            "parameters": {
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "boolean",
                        "description": "是否显示详细信息（包括 docstring 和参数），默认 False",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_skill",
            "description": "查看某个技能的详细信息，包括代码实现、参数列表、docstring 和 JSON Schema",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "技能（函数）名称，如 'read_file', 'web_search'",
                    }
                },
                "required": ["skill_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_skill",
            "description": "创建一个新的技能（工具函数）。在 AgentSkills/tools/ 下的指定模块中添加新函数，并可选择自动更新 __init__.py 导出列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "新技能的函数名，如 'my_new_tool'",
                    },
                    "module_name": {
                        "type": "string",
                        "description": "要添加到哪个模块文件（不含 .py），如 'file_ops', 'shell_ops'",
                    },
                    "code": {
                        "type": "string",
                        "description": "完整的函数定义代码，包括 def、docstring 和函数体",
                    },
                    "update_init": {
                        "type": "boolean",
                        "description": "是否自动更新 __init__.py 的导出列表，默认 True",
                    },
                },
                "required": ["skill_name", "module_name", "code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_skill",
            "description": "更新一个已有技能的代码实现。替换指定函数的全部代码内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "要更新的技能（函数）名称",
                    },
                    "code": {
                        "type": "string",
                        "description": "新的完整函数定义代码",
                    },
                },
                "required": ["skill_name", "code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_skill",
            "description": "删除一个技能。从对应的模块文件中移除函数定义，并可选择从 __init__.py 导出列表中移除。",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "要删除的技能（函数）名称",
                    },
                    "remove_from_init": {
                        "type": "boolean",
                        "description": "是否同时从 __init__.py 移除导出，默认 True",
                    },
                },
                "required": ["skill_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "test_skill",
            "description": "测试调用一个技能函数。传入参数执行指定函数并返回执行结果，用于验证技能功能是否正常。",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "要测试的技能名称",
                    },
                },
                "additionalProperties": True,
                "description": "其他参数会作为关键字参数传递给技能函数",
            },
        },
    },
    # ─── 文件操作（辅助管理） ───
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定文件的内容。用于查看技能代码文件或配置文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "文件的路径"}
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "将内容写入指定文件（覆盖写入），自动创建父目录。用于创建或修改技能相关的文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "要写入的内容"},
                },
                "required": ["file_path", "content"],
            },
        },
    },
    # ─── 联网搜索 ───
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "通过 Bing 搜索互联网，返回标题、链接和摘要列表。适合查询最新的技术文档、API 用法等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词（支持中文）"},
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数量（1~20，默认5）",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search_and_open",
            "description": "搜索互联网并自动获取第一条结果的页面正文内容。适合深入阅读技术文档。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数量（默认5）",
                    },
                    "fetch_content": {
                        "type": "boolean",
                        "description": "是否获取第一条结果的页面内容（默认 true）",
                    },
                    "max_content_length": {
                        "type": "integer",
                        "description": "最大获取的页面内容长度（默认2000）",
                    },
                },
                "required": ["query"],
            },
        },
    },
]

# 工具名称到实际函数的映射
tool_functions = {
    # 技能管理
    "list_skills": list_skills,
    "view_skill": view_skill,
    "create_skill": create_skill,
    "update_skill": update_skill,
    "delete_skill": delete_skill,
    "test_skill": test_skill,
    # 文件操作
    "read_file": read_file,
    "write_file": write_file,
    # 联网搜索
    "web_search": web_search,
    "web_search_and_open": web_search_and_open,
}


# ========================================================================
# 3a. 流式调用 + Tool Calls 累积（非打印模式，用于 --task 收集）
# ========================================================================

def _stream_chat_collect(messages: list) -> dict:
    """流式调用 DeepSeek API，累积 tool_calls，收集内容（不打印到终端）"""
    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.3,
        stream=True,
    )

    content_parts: list[str] = []
    tool_calls_accum: dict[int, dict] = {}

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta is None:
            continue

        if delta.content:
            content_parts.append(delta.content)

        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in tool_calls_accum:
                    tool_calls_accum[idx] = {
                        "id": "",
                        "function": {"name": "", "arguments": ""},
                    }
                entry = tool_calls_accum[idx]
                if tc_delta.id:
                    entry["id"] = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        entry["function"]["name"] = tc_delta.function.name
                    if tc_delta.function.arguments:
                        entry["function"]["arguments"] += tc_delta.function.arguments

    content = "".join(content_parts).strip()

    tool_calls_list = []
    for idx in sorted(tool_calls_accum.keys()):
        tc = tool_calls_accum[idx]
        tool_calls_list.append({
            "id": tc["id"],
            "type": "function",
            "function": {
                "name": tc["function"]["name"],
                "arguments": tc["function"]["arguments"],
            },
        })

    assistant_msg: dict = {
        "role": "assistant",
        "content": content if content else None,
    }
    if tool_calls_list:
        assistant_msg["tool_calls"] = tool_calls_list

    return assistant_msg


# ========================================================================
# 3b. 流式调用 + 实时输出（用于 --task 流式模式，被 FishPool 调用）
# ========================================================================

def _stream_chat_collect_streaming(messages: list) -> dict:
    """流式调用 DeepSeek API，实时打印到 stdout，同时累积 tool_calls

    与 _stream_chat_collect 的区别：
    - 每收到一个 content chunk，立即用 sys.stdout.write() + flush() 输出
    - 这样 FishPool 通过 PIPE 读取时可以实时获取到流式内容
    """
    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.3,
        stream=True,
    )

    content_parts: list[str] = []
    tool_calls_accum: dict[int, dict] = {}

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta is None:
            continue

        if delta.content:
            content_parts.append(delta.content)
            # ★★★ 实时输出到 stdout，FishPool 的 Popen 能立即读取 ★★★
            sys.stdout.write(delta.content)
            sys.stdout.flush()

        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in tool_calls_accum:
                    tool_calls_accum[idx] = {
                        "id": "",
                        "function": {"name": "", "arguments": ""},
                    }
                entry = tool_calls_accum[idx]
                if tc_delta.id:
                    entry["id"] = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        entry["function"]["name"] = tc_delta.function.name
                    if tc_delta.function.arguments:
                        entry["function"]["arguments"] += tc_delta.function.arguments

    content = "".join(content_parts).strip()

    tool_calls_list = []
    for idx in sorted(tool_calls_accum.keys()):
        tc = tool_calls_accum[idx]
        tool_calls_list.append({
            "id": tc["id"],
            "type": "function",
            "function": {
                "name": tc["function"]["name"],
                "arguments": tc["function"]["arguments"],
            },
        })

    assistant_msg: dict = {
        "role": "assistant",
        "content": content if content else None,
    }
    if tool_calls_list:
        assistant_msg["tool_calls"] = tool_calls_list

    return assistant_msg


# ========================================================================
# 3c. 流式调用 + Tool Calls 累积（打印模式，用于交互式）
# ========================================================================

def stream_chat_with_tools(messages: list) -> dict:
    """
    流式调用 DeepSeek API，实时打印文本内容，
    同时累积可能的 tool_calls 并返回完整的 assistant message dict。
    """
    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.3,
        stream=True,
    )

    content_parts: list[str] = []
    tool_calls_accum: dict[int, dict] = {}

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta is None:
            continue

        # 流式打印文本内容
        if delta.content:
            content_parts.append(delta.content)
            print(delta.content, end="", flush=True)

        # 累积 tool_calls
        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in tool_calls_accum:
                    tool_calls_accum[idx] = {
                        "id": "",
                        "function": {"name": "", "arguments": ""},
                    }
                entry = tool_calls_accum[idx]
                if tc_delta.id:
                    entry["id"] = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        entry["function"]["name"] = tc_delta.function.name
                    if tc_delta.function.arguments:
                        entry["function"]["arguments"] += tc_delta.function.arguments

    content = "".join(content_parts).strip()

    tool_calls_list = []
    for idx in sorted(tool_calls_accum.keys()):
        tc = tool_calls_accum[idx]
        tool_calls_list.append(
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"],
                },
            }
        )

    assistant_msg: dict = {
        "role": "assistant",
        "content": content if content else None,
    }
    if tool_calls_list:
        assistant_msg["tool_calls"] = tool_calls_list

    return assistant_msg


# ========================================================================
# 4. 一键执行模式（被 FishPool 唤醒时使用，流式输出）
# ========================================================================

SYSTEM_PROMPT = """
你是一个专业的 **FishFarmer** —— 技能管理 Agent。

你的职责是管理和维护 AgentSkills 包中的所有技能（工具函数）。

## 📦 技能管理工具

你可以使用以下工具来管理技能：

### 🔍 查看与浏览
- **list_skills** — 列出所有可用的技能
  - 参数 detail=True 可查看详细信息（docstring + 参数列表）
- **view_skill** — 查看某个技能的完整详情（代码实现、参数、docstring、JSON Schema）

### ✏️ 创建与修改
- **create_skill** — 创建一个新的技能
  - 需要指定：skill_name（函数名）、module_name（目标模块）、code（函数代码）
  - 可选：update_init 是否自动更新导出列表
- **update_skill** — 更新已有技能的代码实现
  - 需要指定：skill_name、code（新的完整函数代码）
- **delete_skill** — 删除一个技能
  - 可选：remove_from_init 是否同时从导出列表移除

### 🧪 测试与验证
- **test_skill** — 调用指定的技能函数进行测试
  - 传入参数验证函数功能是否正常

### 📁 文件操作（辅助）
- **read_file** — 读取任意文件内容（查看配置文件、代码等）
- **write_file** — 写入或创建文件

### 🌐 联网搜索（辅助）
- **web_search** — 搜索互联网获取最新信息
- **web_search_and_open** — 搜索并阅读页面内容

## 📁 文件结构

技能（工具函数）存储在以下目录：
```
AgentSkills/
├── tools/              # 技能实现代码
│   ├── __init__.py     # 导出列表
│   ├── file_ops.py     # 文件操作技能
│   ├── shell_ops.py    # Shell 执行技能
│   ├── syntax_checker.py  # 语法检查技能
│   └── web_search.py   # 联网搜索技能
├── core/               # Agent 核心逻辑
│   ├── agent.py        # Agent 主循环（含 TOOLS_SCHEMA 和 TOOL_FUNCTIONS）
│   └── llm_client.py   # LLM 客户端
├── skill.py            # Skill 统一接口
└── config.yaml         # 配置文件
```

## 💡 工作流程建议

1. **用户想了解技能** → 使用 list_skills / view_skill
2. **用户想创建新技能** →
   - 先 list_skills 查看已有技能，避免重名
   - 查看目标模块的代码风格
   - 创建技能函数代码
   - 调用 create_skill 写入文件
   - 提示用户更新 core/agent.py 中的 TOOLS_SCHEMA 和 TOOL_FUNCTIONS
3. **用户想修改技能** →
   - 先 view_skill 查看当前实现
   - 修改代码后调用 update_skill
4. **用户想删除技能** →
   - 先 view_skill 确认
   - 调用 delete_skill 删除
   - 提示用户同步清理 core/agent.py
5. **用户想测试技能** → 使用 test_skill 传入参数执行

请根据用户的需求，合理使用这些工具来管理 AgentSkills 中的各项技能。
"""


def run_one_shot(task: str) -> str:
    """一键执行模式（流式输出）：接收任务描述，调用 LLM + 工具循环，实时流式输出结果

    被 FishPool 通过子进程唤醒时使用，不进入交互式 CLI。
    所有 AI 输出和工具调用结果都会实时打印到 stdout，
    FishPool 的 Popen 流式读取后展示给用户。

    Args:
        task: 任务描述

    Returns:
        最终执行结果（完整文本）
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {"role": "user", "content": task},
    ]

    # 第一次调用（流式输出版）
    assistant_msg = _stream_chat_collect_streaming(messages)
    messages.append(assistant_msg)

    # 收集所有中间输出
    all_outputs = []
    if assistant_msg.get("content"):
        all_outputs.append(assistant_msg["content"])

    # 工具调用循环
    max_turns = 20
    turn_count = 0

    while assistant_msg.get("tool_calls") and turn_count < max_turns:
        turn_count += 1
        tool_calls = assistant_msg["tool_calls"]

        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            tool_args = json.loads(tc["function"]["arguments"])

            if tool_name in tool_functions:
                try:
                    result = tool_functions[tool_name](**tool_args)
                except TypeError as e:
                    result = f"❌ 参数错误: {e}"
                except Exception as e:
                    result = f"❌ 执行出错: {e}"
            else:
                result = f"Unknown tool: {tool_name}"

            # 实时输出工具调用结果
            sys.stdout.write(f"\n\n[工具调用] {tool_name}\n参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}\n结果:\n{result}\n\n")
            sys.stdout.flush()

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

        assistant_msg = _stream_chat_collect_streaming(messages)
        messages.append(assistant_msg)

        if assistant_msg.get("content"):
            all_outputs.append(assistant_msg["content"])

    final_result = "\n".join(all_outputs).strip()
    return final_result if final_result else "（无输出）"


# ========================================================================
# 5. 交互式 Agent 主循环（美化版 CLI）
# ========================================================================

def run_agent():
    """运行 FishFarmer Agent 主循环（带美化 CLI）"""

    messages = [{"role": "system", "content": SYSTEM_PROMPT.strip()}]

    # ═══════════════════════════════════════════════════════════════
    # 欢迎界面
    # ═══════════════════════════════════════════════════════════════
    width = min(get_term_width() - 2, 80)
    width = max(width, 50)

    print()
    print_panel(
        content=(
            f"{Color.BLD}{Color.BCYN}  🧠  FishFarmer{Color.RST}  {Color.BWHT}— 技能管理 Agent{Color.RST}\n\n"
            f"  {Color.BLD}模型:{Color.RST}  {Color.BCYN}{MODEL}{Color.RST}\n"
            f"  {Color.BLD}工具:{Color.RST}  {Color.BGRN}{len(tools)} 个技能可用{Color.RST}\n"
            f"  {Color.BLD}路径:{Color.RST}  {Color.DIM}{AGENT_SKILLS_DIR}{Color.RST}\n\n"
            f"  {Color.HINT}输入 /exit 或 /quit 退出对话{Color.RST}"
        ),
        title="🚀 FishFarmer",
        color=Color.SYS,
        width=width,
    )
    print()

    # ═══════════════════════════════════════════════════════════════
    # 对话主循环
    # ═══════════════════════════════════════════════════════════════
    round_num = 0

    while True:
        try:
            # ── 用户输入 ──
            prompt_style = f"{Color.USER}{Color.BLD}┌─ 💬 You ──────────────────────────────────{Color.RST}"
            print(prompt_style)
            user_input = input(f"{Color.USER}{Color.BLD}│{Color.RST} ").strip()
            # 关闭输入框（覆盖 prompt 行的长度）
            print(f"{Color.USER}{Color.BLD}╰────────────────────────────────────────────{Color.RST}")

        except (EOFError, KeyboardInterrupt):
            print()
            print()
            print_panel(
                content=f"{Color.BLD}{Color.BCYN}  🌟 感谢使用 FishFarmer，期待再次相见！{Color.RST}",
                title="👋 再见",
                color=Color.SYS,
                width=width,
            )
            print()
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", "/exit", "/quit"} or user_input in {"再见", "退出"}:
            print()
            print_panel(
                content=f"{Color.BLD}{Color.BCYN}  🌟 感谢使用 FishFarmer，期待再次相见！{Color.RST}",
                title="👋 再见",
                color=Color.SYS,
                width=width,
            )
            print()
            break

        # ── 处理 /help 命令 ──
        if user_input.lower() in {"/help", "help", "-h", "--help"}:
            print_panel(
                content=(
                    f"  {Color.BLD}{Color.BCYN}可用命令:{Color.RST}\n\n"
                    f"  {Color.BGRN}/help{Color.RST}    - 显示此帮助信息\n"
                    f"  {Color.BRED}/exit{Color.RST}    - 退出程序\n"
                    f"  {Color.BRED}/quit{Color.RST}    - 退出程序\n\n"
                    f"  {Color.BLD}或者直接输入自然语言与 AI 对话，{Color.RST}\n"
                    f"  例如：「列出所有技能」「创建一个文件搜索技能」"
                ),
                title="💡 帮助",
                color=Color.INFO,
                width=width,
            )
            print()
            continue

        round_num += 1
        messages.append({"role": "user", "content": user_input})

        # ── Agent 回复（流式） ──
        ts = format_timestamp()
        print(f"{Color.AGENT}{Color.BLD}┌─ 🤖 FishFarmer @ {ts} ─────────────────{Color.RST}")
        print(f"{Color.AGENT}{Color.BLD}│{Color.RST} ", end="", flush=True)

        assistant_msg = stream_chat_with_tools(messages)

        print()
        print(f"{Color.AGENT}{Color.BLD}╰────────────────────────────────────────────{Color.RST}")
        print()
        messages.append(assistant_msg)

        # ── 工具调用循环 ──
        while assistant_msg.get("tool_calls"):
            tool_calls = assistant_msg["tool_calls"]

            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                tool_args = json.loads(tc["function"]["arguments"])

                # 调用工具
                if tool_name in tool_functions:
                    try:
                        result = tool_functions[tool_name](**tool_args)
                    except TypeError as e:
                        result = f"{Color.ERR}❌ 参数错误: {e}{Color.RST}"
                    except Exception as e:
                        result = f"{Color.ERR}❌ 执行出错: {e}{Color.RST}"
                else:
                    result = f"Unknown tool: {tool_name}"

                # 以美化面板显示工具调用与结果
                print_tool_result(tool_name, tool_args, result)
                print()

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    }
                )

            # Agent 再次回复
            ts = format_timestamp()
            print(f"{Color.AGENT}{Color.BLD}┌─ 🤖 FishFarmer @ {ts} ─────────────────{Color.RST}")
            print(f"{Color.AGENT}{Color.BLD}│{Color.RST} ", end="", flush=True)

            assistant_msg = stream_chat_with_tools(messages)

            print()
            print(f"{Color.AGENT}{Color.BLD}╰────────────────────────────────────────────{Color.RST}")
            print()
            messages.append(assistant_msg)

        if assistant_msg.get("content"):
            print()


# ========================================================================
# 6. 程序入口
# ========================================================================

if __name__ == "__main__":
    # 解析命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--task":
        # ── 一键执行模式（被 FishPool 唤醒） ──
        task = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not task:
            task = sys.stdin.read().strip()
        if not task:
            print("❌ 错误: --task 参数不能为空。用法: python SkillsManager.py --task \"你的任务描述\"")
            sys.exit(1)
        result = run_one_shot(task)
        # 流式模式下，内容已实时输出
        sys.exit(0)
    else:
        # ── 交互模式 ──
        run_agent()
