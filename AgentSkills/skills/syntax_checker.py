"""
语法检查工具模块

提供 Python、YAML、HTML、CSS、JavaScript 等文件的语法检查功能。
"""

import os
import re
import subprocess
import tempfile

import yaml


def check_python_syntax(file_path: str) -> str:
    """使用 Python 编译器检查 Python 文件的语法

    Args:
        file_path: Python 文件路径

    Returns:
        语法检查通过或错误信息
    """
    try:
        result = subprocess.run(
            ["python", "-m", "py_compile", file_path],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return "✅ Python syntax check passed."
        else:
            # 美化错误信息
            errors = result.stderr.strip()
            return f"❌ Python syntax errors:\n{errors}"
    except Exception as e:
        return f"❌ Error checking Python syntax: {e}"


def check_yaml_syntax(file_path: str) -> str:
    """检查 YAML 文件的语法是否合法

    Args:
        file_path: YAML 文件路径

    Returns:
        语法检查通过或错误信息
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            yaml.safe_load(f)
        return "✅ YAML syntax check passed."
    except yaml.YAMLError as e:
        return f"❌ YAML syntax errors:\n{e}"


def check_html_syntax(file_path: str, use_tidy: bool = True) -> str:
    """检查 HTML 文件的语法是否合法

    支持两种检查方式：
    1. tidy（默认）：使用 HTML Tidy 工具，检查更全面（标签闭合、属性值、嵌套等）
    2. html.parser（回退）：使用 Python 标准库 html.parser 做基本解析

    Args:
        file_path: HTML 文件路径
        use_tidy: 是否优先使用 HTML Tidy 工具（默认 True）

    Returns:
        语法检查通过或错误信息
    """
    if not os.path.exists(file_path):
        return f"❌ File not found: {file_path}"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"❌ Error reading file: {e}"

    if not content.strip():
        return "⚠️ HTML file is empty."

    # ── 方式1：使用 HTML Tidy（更全面）──
    if use_tidy:
        try:
            result = subprocess.run(
                [
                    "tidy",
                    "-q",           # 安静模式
                    "-e",           # 只显示错误
                    "--show-warnings", "no",
                    "--show-errors", "5",  # 最多显示5个错误
                    file_path,
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                return "✅ HTML syntax check passed (tidy)."
            else:
                errors = result.stderr.strip() or result.stdout.strip()
                if errors:
                    return f"❌ HTML syntax errors (tidy):\n{errors}"
                return "✅ HTML syntax check passed (tidy - no critical errors)."
        except FileNotFoundError:
            pass  # tidy 不可用，回退到 html.parser
        except subprocess.TimeoutExpired:
            pass  # 超时，回退到 html.parser
        except Exception:
            pass  # 其他错误，回退到 html.parser

    # ── 方式2：使用 html.parser 做基本检查（回退方案）──
    try:
        from html.parser import HTMLParser

        class HTMLValidator(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.errors = []
                self.tag_stack = []       # 用于检查标签嵌套
                self.void_elements = {
                    "area", "base", "br", "col", "embed", "hr",
                    "img", "input", "link", "meta", "param",
                    "source", "track", "wbr",
                }

            def handle_starttag(self, tag, attrs):
                if tag not in self.void_elements:
                    self.tag_stack.append(tag)

            def handle_endtag(self, tag):
                if tag in self.void_elements:
                    return
                if tag in self.tag_stack:
                    # 从栈中移除匹配的标签及中间未闭合的标签
                    while self.tag_stack:
                        last = self.tag_stack.pop()
                        if last == tag:
                            break
                        self.errors.append(
                            f"  - Tag <{last}> not closed before </{tag}>"
                        )

            def get_report(self):
                # 检查未闭合的标签
                for tag in reversed(self.tag_stack):
                    self.errors.append(f"  - Tag <{tag}> is not closed")
                return self.errors

        validator = HTMLValidator()
        validator.feed(content)
        validator.close()

        errors = validator.get_report()

        # 额外检查：doctype
        if not re.search(r'<!DOCTYPE\s+html', content, re.IGNORECASE):
            errors.insert(0, "  - Missing DOCTYPE declaration")

        # 额外检查：charset
        if not re.search(r'<meta[^>]*charset', content, re.IGNORECASE):
            errors.append("  - Missing charset meta tag (e.g. <meta charset='UTF-8'>)")

        if not errors:
            return "✅ HTML syntax check passed (html.parser)."
        else:
            error_msg = "\n".join(errors)
            return f"❌ HTML potential issues ({len(errors)}):\n{error_msg}"

    except Exception as e:
        return f"❌ Error checking HTML syntax: {e}"


def check_css_syntax(file_path: str) -> str:
    """检查 CSS 文件的语法是否合法

    使用基本规则校验：
    - 花括号匹配
    - 选择器和属性声明格式
    - @规则格式

    Args:
        file_path: CSS 文件路径

    Returns:
        语法检查通过或错误信息
    """
    if not os.path.exists(file_path):
        return f"❌ File not found: {file_path}"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"❌ Error reading file: {e}"

    if not content.strip():
        return "⚠️ CSS file is empty."

    issues = []

    # 移除注释和字符串内容，避免误报
    cleaned = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    cleaned = re.sub(r'url\([^)]+\)', 'url()', cleaned)

    # 1. 检查花括号是否配对
    open_braces = cleaned.count("{")
    close_braces = cleaned.count("}")
    if open_braces != close_braces:
        issues.append(
            f"  - Brace mismatch: {open_braces} opening vs {close_braces} closing"
        )

    # 2. 检查每个规则块内是否有属性声明
    rule_blocks = re.findall(r'([^{]+)\{([^}]*)\}', cleaned)
    for idx, (selector, declarations) in enumerate(rule_blocks, 1):
        selector = selector.strip()
        dec = declarations.strip()

        # 跳过 @import 和 @charset 等
        if selector.startswith("@"):
            continue

        # 检查空规则块
        if not dec:
            issues.append(f"  - Empty rule block: {selector[:50]}")

        # 检查无效属性格式（每行应该有冒号）
        if dec:
            for line in dec.split(";"):
                line = line.strip()
                if line and ":" not in line and not line.startswith("/*"):
                    issues.append(f"  - Missing colon in declaration: '{line[:40]}' (selector: {selector[:30]})")

    # 3. 检查 @规则格式
    at_rules = re.findall(r'@\w+', cleaned)
    for rule in at_rules:
        if rule not in (
            "@import", "@charset", "@namespace", "@media",
            "@font-face", "@keyframes", "@supports",
            "@page", "@document",
        ):
            issues.append(f"  - Unknown @rule: {rule}")

    if not issues:
        return "✅ CSS syntax check passed."
    else:
        issue_msg = "\n".join(issues)
        return f"⚠️ CSS potential issues ({len(issues)}):\n{issue_msg}"


def check_js_syntax(file_path: str) -> str:
    """检查 JavaScript 文件的语法是否合法

    优先使用 Node.js 的 --check 参数进行语法检查（准确可靠），
    如果 Node.js 不可用则回退到基本规则检查。

    Args:
        file_path: JavaScript 文件路径

    Returns:
        语法检查通过或错误信息
    """
    if not os.path.exists(file_path):
        return f"❌ File not found: {file_path}"

    # ── 方式1：使用 Node.js --check（最准确）──
    try:
        result = subprocess.run(
            ["node", "--check", file_path],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return "✅ JavaScript syntax check passed (Node.js)."
        else:
            errors = result.stderr.strip() or result.stdout.strip()
            return f"❌ JavaScript syntax errors (Node.js):\n{errors}"
    except FileNotFoundError:
        pass  # Node.js 不可用
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass

    # ── 方式2：基本规则检查（回退方案）──
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"❌ Error reading file: {e}"

    if not content.strip():
        return "⚠️ JavaScript file is empty."

    issues = []

    # 移除字符串和注释内容
    cleaned = re.sub(r'//.*', '', content)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"'[^']*'", "''", cleaned)
    cleaned = re.sub(r'"[^"]*"', '""', cleaned)
    cleaned = re.sub(r'`[^`]*`', '``', cleaned)

    # 1. 检查括号配对
    for name, open_c, close_c in [
        ("Parentheses", "(", ")"),
        ("Square brackets", "[", "]"),
        ("Curly braces", "{", "}"),
    ]:
        opens = cleaned.count(open_c)
        closes = cleaned.count(close_c)
        if opens != closes:
            issues.append(
                f"  - {name} mismatch: {opens} opening vs {closes} closing"
            )

    # 2. 检查基本的语法结构
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # 跳过空行和注释
        if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
            continue

        # 检查 return/throw 后面是否有换行导致的问题
        if stripped in ("return", "throw", "break", "continue"):
            issues.append(f"  - Line {i}: '{stripped}' with nothing following (ASI issue?)")

    if not issues:
        return "✅ JavaScript syntax check passed (basic)."
    else:
        issue_msg = "\n".join(issues)
        return f"⚠️ JavaScript potential issues ({len(issues)}):\n{issue_msg}"
