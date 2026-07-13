"""
CodingAgent - 智能代码编程助手

基于 DeepSeek API 的流式对话 Agent，支持：
- 📂 文件读写
- 🖥️ Shell 命令执行
- ✅ Python/YAML 语法检查
- 🌐 联网搜索（基于 Bing，无需 API Key）
- 🚀 Go 语言项目创建（gin/echo/fiber 框架，MVC 架构，Docker 部署）

CLI 风格：美观的聊天气泡 + 面板展示
"""

import os
import re
import json
import sys
import time
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional
from urllib.parse import urlparse
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv
import yaml

# Git 操作工具
from AgentSkills.skills.git_ops import (
    check_git_installed,
    git_init,
    git_clone,
    git_status,
    git_add,
    git_commit,
    git_log,
    git_diff,
    git_branch,
    git_checkout,
    git_pull,
    git_push,
    git_ignore,
    git_config,
    git_reset,
    git_tag,
)

# ─── CLI 美化模块 ───
from cli_style import (
    Color, cprint, get_term_width, format_timestamp,
    print_panel, print_banner, print_tool_result,
    print_user_input, print_agent_start, print_agent_end,
    print_streaming_prefix, print_welcome, print_goodbye,
    print_help, print_separator, print_status, truncate_text,
)

# 加载环境变量
load_dotenv()

# 初始化 DeepSeek 客户端
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

MODEL = "deepseek-v4-flash"
AGENT_NAME = "Coding Agent"

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# ─── 导入中文友好的输入模块 ───
try:
    sys.path.insert(0, str(PROJECT_ROOT))
    from cli_input import chinese_input, ExitRequested
    HAVE_CLI_INPUT = True
except ImportError:
    HAVE_CLI_INPUT = False
    chinese_input = input


# ═══════════════════════════════════════════════════════════════════════
# 1. 工具函数定义
# ═══════════════════════════════════════════════════════════════════════

def read_file(file_path: str) -> str:
    """读取指定文件的内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(file_path: str, content: str) -> str:
    """将内容写入指定文件（覆盖写入），自动创建父目录"""
    try:
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


def run_shell_command(command: str) -> str:
    """执行 Shell 命令并返回输出（支持 Go、Python、Node.js 等）"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error executing command: {e}"


def check_python_syntax(file_path: str) -> str:
    """使用 Python 编译器检查 Python 文件的语法"""
    try:
        result = subprocess.run(
            ["python", "-m", "py_compile", file_path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return "✅ Python syntax check passed."
        else:
            return f"❌ Python syntax errors:\n{result.stderr}"
    except Exception as e:
        return f"Error checking Python syntax: {e}"


def check_yaml_syntax(file_path: str) -> str:
    """检查 YAML 文件的语法是否合法"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        return "✅ YAML syntax check passed."
    except yaml.YAMLError as e:
        return f"❌ YAML syntax errors:\n{e}"


# ═══════════════════════════════════════════════════════════════════════
# 1.5 Go 语言辅助函数
# ═══════════════════════════════════════════════════════════════════════


def check_go_installed() -> tuple[bool, str]:
    """检查 Go 是否已安装，返回 (是否安装, 版本信息)"""
    result = run_shell_command("go version 2>&1")
    if "go version" in result:
        return True, result.strip()
    return False, "Go 未安装。请访问 https://go.dev/dl/ 下载安装。"


def check_go_mod_exists(project_dir: str) -> bool:
    """检查指定目录下是否存在 go.mod 文件"""
    mod_path = os.path.join(project_dir, "go.mod")
    return os.path.exists(mod_path)


def run_go_fmt(file_path: str) -> str:
    """使用 gofmt 格式化 Go 代码"""
    result = run_shell_command(f"gofmt -l {file_path} 2>&1")
    if "command not found" in result or "not found" in result:
        return "⚠️ gofmt 未安装，请安装 Go 工具链。"
    if not result.strip():
        return "✅ Go 代码格式正确。"
    return f"📝 以下文件需要格式化:\n{result}"


def run_go_vet(project_dir: str) -> str:
    """使用 go vet 检查 Go 代码潜在问题"""
    result = run_shell_command(f"cd {project_dir} && go vet ./... 2>&1")
    if not result.strip():
        return "✅ go vet 检查通过，无潜在问题。"
    return f"⚠️ go vet 发现以下问题:\n{result}"


def run_go_build(project_dir: str) -> str:
    """构建 Go 项目"""
    result = run_shell_command(f"cd {project_dir} && go build ./... 2>&1")
    if "error" not in result.lower() and "cannot" not in result.lower():
        return "✅ Go 项目构建成功！"
    return f"❌ Go 构建失败:\n{result}"


def create_go_project_structure(project_name: str, target_dir: str = ".") -> str:
    """创建 Go 项目的标准目录结构

    Args:
        project_name: 项目名称（用作 module name）
        target_dir: 目标目录（默认当前目录）

    Returns:
        创建结果描述
    """
    base_path = os.path.join(target_dir, project_name)

    try:
        # 创建项目目录
        os.makedirs(base_path, exist_ok=True)

        # Go 项目标准目录结构
        go_dirs = [
            "cmd/server",
            "internal/config",
            "internal/handler",
            "internal/middleware",
            "internal/model",
            "internal/repository",
            "internal/router",
            "internal/service",
            "pkg/response",
            "pkg/validator",
            "api",
            "configs",
            "deploy",
            "scripts",
            "web",
            "test",
        ]

        for d in go_dirs:
            os.makedirs(os.path.join(base_path, d), exist_ok=True)

        # 初始化 Go module
        mod_result = run_shell_command(f"cd {base_path} && go mod init {project_name} 2>&1")

        # 创建 .gitignore
        gitignore_content = (
            "# Binaries\n"
            "*.exe\n*.exe~\n*.dll\n*.so\n*.dylib\n*.test\n*.out\n/tmp/\n\n"
            "# Go workspace\n"
            "go.work\ngo.work.sum\n\n"
            "# IDE\n"
            ".idea/\n.vscode/\n*.swp\n*.swo\n*~\n\n"
            "# OS\n"
            ".DS_Store\nThumbs.db\n\n"
            "# Environment\n"
            ".env\n.env.local\n\n"
            "# Build\n"
            "/dist/\n/build/\n"
        )

        write_file(os.path.join(base_path, ".gitignore"), gitignore_content)

        result = (
            f"✅ Go 项目「{project_name}」创建成功！\n\n"
            "📁 项目结构：\n"
            f"  {project_name}/\n"
            "    ├── cmd/server/         # 应用入口\n"
            "    ├── internal/\n"
            "    │   ├── config/         # 配置管理\n"
            "    │   ├── handler/        # HTTP 处理器\n"
            "    │   ├── middleware/     # 中间件\n"
            "    │   ├── model/          # 数据模型\n"
            "    │   ├── repository/     # 数据访问层\n"
            "    │   ├── router/         # 路由注册\n"
            "    │   └── service/        # 业务逻辑层\n"
            "    ├── pkg/\n"
            "    │   ├── response/       # 通用响应\n"
            "    │   └── validator/      # 验证器\n"
            "    ├── api/                # API 定义\n"
            "    ├── configs/            # 配置文件\n"
            "    ├── deploy/             # 部署配置\n"
            "    ├── scripts/            # 脚本\n"
            "    ├── web/                # 前端资源\n"
            "    ├── test/               # 测试文件\n"
            "    ├── go.mod              # Go 模块文件\n"
            "    └── .gitignore\n\n"
            f"{mod_result}"
        )
        return result

    except Exception as e:
        return f"❌ 创建项目失败: {e}"


# ─── 联网搜索工具（基于 Bing，无需 API Key） ───

# 简单的内存缓存，避免短时间内重复搜索相同关键词
_search_cache: dict[str, tuple[float, str]] = {}
_CACHE_TTL = 60  # 缓存有效期（秒）


def _fetch_bing_search(query: str, num_results: int = 10) -> str:
    """通过 Bing HTML 页面获取搜索结果"""
    params = {
        "q": query,
        "count": min(num_results, 20),
        "mkt": "zh-CN",
    }
    url = "https://www.bing.com/search?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )

    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read().decode("utf-8", errors="ignore")


def _parse_bing_results(html: str, max_results: int) -> list[dict]:
    """从 Bing HTML 中解析搜索结果"""
    results = []
    h2_link_pattern = re.compile(
        r'<h2[^>]*>.*?<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>.*?</h2>',
        re.DOTALL | re.IGNORECASE,
    )

    for m in h2_link_pattern.finditer(html):
        link = m.group(1)
        title = re.sub(r"<[^>]+>", "", m.group(2)).strip()

        if not title or not link:
            continue

        # 查找该结果对应的摘要
        snippet = ""
        after_h2 = html[m.end(): m.end() + 2000]
        snippet_match = re.search(r'<p[^>]*>(.*?)</p>', after_h2, re.DOTALL)
        if snippet_match:
            snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip()
            snippet = re.sub(r"\s+", " ", snippet)
            snippet = snippet.replace("&ensp;", " ").replace("&#0183;", "·")

        results.append({"title": title, "href": link, "body": snippet})
        if len(results) >= max_results:
            break

    return results


def web_search(
    query: str,
    max_results: int = 5,
    use_cache: bool = True,
) -> str:
    """通过 Bing 搜索互联网，返回格式化的搜索结果

    完全免费，无需 API Key。通过解析 Bing 搜索页面获取结果。

    Args:
        query: 搜索关键词，支持中文
        max_results: 最大返回结果数量（1~20，默认5）
        use_cache: 是否使用缓存（默认 True，60秒内重复搜索相同关键词直接返回缓存）

    Returns:
        格式化的搜索结果字符串，包含标题、链接和摘要
    """
    # 检查缓存
    cache_key = f"{query}:{max_results}"
    if use_cache and cache_key in _search_cache:
        cached_time, cached_result = _search_cache[cache_key]
        if time.time() - cached_time < _CACHE_TTL:
            return cached_result + "\n\n（来自缓存）"

    try:
        max_results = min(max(max_results, 1), 20)

        # 获取并解析 Bing 搜索结果
        html = _fetch_bing_search(query, num_results=max_results)
        raw_results = _parse_bing_results(html, max_results)

        if not raw_results:
            result_msg = f"🔍 搜索「{query}」未找到任何结果。"
            _search_cache[cache_key] = (time.time(), result_msg)
            return result_msg

        # 格式化输出
        output_lines = [
            f"🔍 搜索「{query}」的结果（共 {len(raw_results)} 条）：\n"
        ]
        for i, r in enumerate(raw_results, 1):
            title = r.get("title", "无标题").strip()
            link = r.get("href", "无链接")
            snippet = r.get("body", "").strip()

            # 清理过长摘要
            if len(snippet) > 300:
                snippet = snippet[:300] + "..."

            output_lines.append(f"{i}. {title}")
            output_lines.append(f"   链接: {link}")
            if snippet:
                output_lines.append(f"   摘要: {snippet}")
            output_lines.append("")

        result_msg = "\n".join(output_lines)

        # 写入缓存
        if use_cache:
            _search_cache[cache_key] = (time.time(), result_msg)

        return result_msg

    except urllib.error.HTTPError as e:
        return f"❌ 搜索请求被拒绝 (HTTP {e.code}): 可能是访问过于频繁，请稍后再试。"
    except urllib.error.URLError as e:
        return f"❌ 网络连接失败: {e.reason}。请检查网络连接。"
    except Exception as e:
        return f"❌ 搜索出错: {e}"


def web_search_and_open(
    query: str,
    max_results: int = 5,
    fetch_content: bool = True,
    max_content_length: int = 2000,
) -> str:
    """搜索互联网，并可选地获取第一条结果的页面正文内容

    Args:
        query: 搜索关键词
        max_results: 最大返回结果数量（默认5）
        fetch_content: 是否获取第一条结果的页面内容（默认 True）
        max_content_length: 最大获取的页面内容长度（默认 2000）

    Returns:
        搜索结果及可选页面内容的字符串
    """
    search_result = web_search(query=query, max_results=max_results, use_cache=False)

    if not fetch_content:
        return search_result

    # 尝试提取第一条结果的 URL 并获取页面内容
    try:
        # 从搜索结果中提取第一个链接
        link_match = re.search(r"链接:\s*(https?://[^\s]+)", search_result)
        if not link_match:
            return search_result + "\n\n（无法提取链接以获取页面内容）"

        first_url = link_match.group(1)
        parsed = urlparse(first_url)
        if not parsed.scheme or not parsed.netloc:
            return search_result + "\n\n（链接格式无效，无法获取页面内容）"

        # 请求页面内容
        req = urllib.request.Request(
            first_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # 提取正文文本（去除 HTML 标签）
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) > max_content_length:
            text = text[:max_content_length] + "..."

        return (
            search_result
            + f"\n\n📄 第一条结果的页面内容（来自 {first_url}）：\n{text}"
        )

    except urllib.error.HTTPError as e:
        return search_result + f"\n\n（获取页面内容时被拒绝: HTTP {e.code}）"
    except urllib.error.URLError as e:
        return search_result + f"\n\n（无法连接到目标网站: {e.reason}）"
    except Exception as e:
        return search_result + f"\n\n（获取页面内容时出错: {e}）"


# ═══════════════════════════════════════════════════════════════════════
# 2. 工具的 JSON Schema
# ═══════════════════════════════════════════════════════════════════════

tools = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定文件的内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "文件的路径"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "将内容写入指定文件（覆盖写入），自动创建父目录",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "要写入的内容"}
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell_command",
            "description": "执行 Shell 命令（支持运行 Go 构建/测试/格式化、Python、Node.js 等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的 Shell 命令"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_python_syntax",
            "description": "检查 Python 文件的语法是否正确",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Python 文件路径"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_yaml_syntax",
            "description": "检查 YAML 文件的语法是否正确",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "YAML 文件路径"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "通过 Bing 搜索互联网，返回标题、链接和摘要。完全免费，无需 API Key。适合搜索最新的技术文档、API 用法、教程等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，支持中文"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数量（1~20，默认5）",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search_and_open",
            "description": "搜索互联网，并自动获取第一条结果的页面正文内容。适合需要深入了解某个特定主题的详情。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，支持中文"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数量（1~20，默认5）",
                        "default": 5
                    },
                    "max_content_length": {
                        "type": "integer",
                        "description": "最大获取的页面内容长度（默认 2000）",
                        "default": 2000
                    }
                },
                "required": ["query"]
            }
        }
    },
    # ═══════════ Git 操作 ═══════════
    {
        "type": "function",
        "function": {
            "name": "check_git_installed",
            "description": "检查 Git 是否已安装并返回版本信息",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_init",
            "description": "初始化一个新的 Git 仓库",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目根目录路径"}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_clone",
            "description": "克隆远程仓库到本地",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_url": {"type": "string", "description": "远程仓库 URL"},
                    "target_dir": {"type": "string", "description": "目标目录（可选，默认自动）"}
                },
                "required": ["repo_url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "查看仓库当前工作区状态（变更文件、暂存情况等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目根目录路径"}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_add",
            "description": "将文件变更添加到暂存区",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目根目录路径"},
                    "files": {"type": "string", "description": "要添加的文件或模式（默认 '.' 表示全部）"}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "提交暂存区的变更到本地仓库",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目根目录路径"},
                    "message": {"type": "string", "description": "提交信息"},
                    "author": {"type": "string", "description": "作者信息（可选，格式: 'Name <email>'）"}
                },
                "required": ["project_path", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "查看提交历史记录",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目根目录路径"},
                    "max_count": {"type": "integer", "description": "最大显示条数（默认10）"},
                    "pretty_format": {"type": "string", "description": "输出格式（如 oneline/short/full）"}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "查看工作区与暂存区的差异（未暂存的变更）",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目根目录路径"},
                    "staged": {"type": "boolean", "description": "是否查看已暂存（staged）的差异（默认false）"}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_branch",
            "description": "分支管理：列出、创建或删除分支",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目根目录路径"},
                    "branch_name": {"type": "string", "description": "分支名称（可选，用于创建/删除）"},
                    "action": {"type": "string", "description": "操作类型：list/delete（默认list）", "enum": ["list", "delete"]}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_checkout",
            "description": "切换分支或恢复工作区文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目根目录路径"},
                    "branch_name": {"type": "string", "description": "要切换到的分支名"},
                    "create_new": {"type": "boolean", "description": "是否创建并切换到新分支（默认false）"}
                },
                "required": ["project_path", "branch_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_pull",
            "description": "从远程仓库拉取最新代码并合并到当前分支",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目根目录路径"},
                    "remote": {"type": "string", "description": "远程仓库名称（默认origin）"},
                    "branch": {"type": "string", "description": "远程分支名（可选，默认当前分支）"}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_push",
            "description": "将本地分支的提交推送到远程仓库",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目根目录路径"},
                    "remote": {"type": "string", "description": "远程仓库名称（默认origin）"},
                    "branch": {"type": "string", "description": "要推送的分支名（可选，默认当前分支）"}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_ignore",
            "description": "生成或追加 .gitignore 文件中的忽略规则",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目根目录路径"},
                    "patterns": {"type": "array", "description": "要添加的忽略模式列表", "items": {"type": "string"}}
                },
                "required": ["project_path", "patterns"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_config",
            "description": "查看或设置 Git 配置（如 user.name、user.email 等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目根目录路径（可选，不指定为全局配置）"},
                    "name": {"type": "string", "description": "配置项名称（如 user.name）"},
                    "value": {"type": "string", "description": "配置项值（可选，不传则查看当前值）"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_reset",
            "description": "重置 HEAD 到指定状态，撤销提交或暂存区变更",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目根目录路径"},
                    "mode": {"type": "string", "description": "重置模式：soft/mixed/hard（默认mixed）", "enum": ["soft", "mixed", "hard"]},
                    "target": {"type": "string", "description": "目标提交（默认HEAD）"}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_tag",
            "description": "标签管理：列出、创建或删除标签",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目根目录路径"},
                    "tag_name": {"type": "string", "description": "标签名（可选，用于创建/删除）"},
                    "message": {"type": "string", "description": "附注标签的说明信息"},
                    "action": {"type": "string", "description": "操作类型：list/create/delete（默认list）", "enum": ["list", "create", "delete"]}
                },
                "required": ["project_path"]
            }
        }
    },
]

tool_functions = {
    "read_file": read_file,
    "write_file": write_file,
    "run_shell_command": run_shell_command,
    "check_python_syntax": check_python_syntax,
    "check_yaml_syntax": check_yaml_syntax,
    "web_search": web_search,
    "web_search_and_open": web_search_and_open,
    # Git 操作
    "check_git_installed": check_git_installed,
    "git_init": git_init,
    "git_clone": git_clone,
    "git_status": git_status,
    "git_add": git_add,
    "git_commit": git_commit,
    "git_log": git_log,
    "git_diff": git_diff,
    "git_branch": git_branch,
    "git_checkout": git_checkout,
    "git_pull": git_pull,
    "git_push": git_push,
    "git_ignore": git_ignore,
    "git_config": git_config,
    "git_reset": git_reset,
    "git_tag": git_tag,
}


# ═══════════════════════════════════════════════════════════════════════
# 3. 流式调用 + Tool Calls 累积（非打印模式，用于 --task 收集）
# ═══════════════════════════════════════════════════════════════════════

def _stream_chat_collect(messages: list) -> dict:
    """流式调用 DeepSeek API，累积 tool_calls，收集内容（不打印到终端）

    用于 --task 一键执行模式，将结果收集后返回。

    Returns:
        {
            "role": "assistant",
            "content": "..." or None,
            "tool_calls": [...]  # 如果有的话
        }
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

        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in tool_calls_accum:
                    tool_calls_accum[idx] = {
                        "id": "",
                        "function": {"name": "", "arguments": ""}
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
                "arguments": tc["function"]["arguments"]
            }
        })

    assistant_msg: dict = {
        "role": "assistant",
        "content": content if content else None,
    }
    if tool_calls_list:
        assistant_msg["tool_calls"] = tool_calls_list

    return assistant_msg


# ═══════════════════════════════════════════════════════════════════════
# 3b. 流式调用 + 实时输出（用于 --task 流式模式，被 LeaderAgent 调用）
# ═══════════════════════════════════════════════════════════════════════

def _stream_chat_collect_streaming(messages: list) -> dict:
    """流式调用 DeepSeek API，实时打印到 stdout，同时累积 tool_calls

    与 _stream_chat_collect 的区别：
    - 每收到一个 content chunk，立即用 sys.stdout.write() + flush() 输出
    - 这样 LeaderAgent 通过 PIPE 读取时可以实时获取到流式内容

    Returns:
        {
            "role": "assistant",
            "content": "..." or None,
            "tool_calls": [...]  # 如果有的话
        }
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
            # ★★★ 实时输出到 stdout，LeaderAgent 的 Popen 能立即读取 ★★★
            sys.stdout.write(delta.content)
            sys.stdout.flush()

        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in tool_calls_accum:
                    tool_calls_accum[idx] = {
                        "id": "",
                        "function": {"name": "", "arguments": ""}
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
                "arguments": tc["function"]["arguments"]
            }
        })

    assistant_msg: dict = {
        "role": "assistant",
        "content": content if content else None,
    }
    if tool_calls_list:
        assistant_msg["tool_calls"] = tool_calls_list

    return assistant_msg


# ═══════════════════════════════════════════════════════════════════════
# 3c. 流式调用 + Tool Calls 累积（打印模式，用于交互式）
# ═══════════════════════════════════════════════════════════════════════

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

        # ── 流式打印文本内容 ──
        if delta.content:
            content_parts.append(delta.content)
            print(delta.content, end="", flush=True)

        # ── 累积 tool_calls ──
        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in tool_calls_accum:
                    tool_calls_accum[idx] = {
                        "id": "",
                        "function": {"name": "", "arguments": ""}
                    }

                entry = tool_calls_accum[idx]

                if tc_delta.id:
                    entry["id"] = tc_delta.id

                if tc_delta.function:
                    if tc_delta.function.name:
                        entry["function"]["name"] = tc_delta.function.name
                    if tc_delta.function.arguments:
                        entry["function"]["arguments"] += tc_delta.function.arguments

    # ── 构建标准 assistant message dict ──
    content = "".join(content_parts).strip()

    tool_calls_list = []
    for idx in sorted(tool_calls_accum.keys()):
        tc = tool_calls_accum[idx]
        tool_calls_list.append({
            "id": tc["id"],
            "type": "function",
            "function": {
                "name": tc["function"]["name"],
                "arguments": tc["function"]["arguments"]
            }
        })

    assistant_msg: dict = {
        "role": "assistant",
        "content": content if content else None,
    }
    if tool_calls_list:
        assistant_msg["tool_calls"] = tool_calls_list

    return assistant_msg


# ═══════════════════════════════════════════════════════════════════════
# 4. Agent 主循环（交互式 CLI + 一键执行模式）
# ═══════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = (
    "你是一个专业的 **Coding Agent**，精通多种编程语言，尤其擅长 **Go 语言** 项目的开发。\n"
    "\n"
    "## 可用工具\n"
    "\n"
    "### 文件操作\n"
    "- **read_file** -- 读取指定文件的内容\n"
    "- **write_file** -- 将内容写入指定文件（覆盖写入），自动创建父目录\n"
    "\n"
    "### 命令执行\n"
    "- **run_shell_command** -- 执行 Shell 命令，支持 Go、Python、Node.js 等\n"
    "\n"
    "### 语法检查\n"
    "- **check_python_syntax** -- 检查 Python 文件的语法是否正确\n"
    "- **check_yaml_syntax** -- 检查 YAML 文件的语法是否正确\n"
    "\n"
    "### 联网搜索\n"
    "- **web_search** -- 搜索互联网，返回标题、链接和摘要\n"
    "- **web_search_and_open** -- 搜索并获取页面正文内容\n"
    "\n"
    "### Git 操作\n"
    "- **check_git_installed** -- 检查 Git 是否已安装并返回版本信息\n"
    "- **git_init** -- 初始化一个新的 Git 仓库\n"
    "- **git_clone** -- 克隆远程仓库到本地\n"
    "- **git_status** -- 查看仓库工作区状态\n"
    "- **git_add** -- 添加文件到暂存区\n"
    "- **git_commit** -- 提交暂存区的变更\n"
    "- **git_log** -- 查看提交历史记录\n"
    "- **git_diff** -- 查看文件差异\n"
    "- **git_branch** -- 分支管理（列出/创建/删除）\n"
    "- **git_checkout** -- 切换分支\n"
    "- **git_pull** -- 从远程仓库拉取更新\n"
    "- **git_push** -- 推送至远程仓库\n"
    "- **git_ignore** -- 管理 .gitignore 忽略规则\n"
    "- **git_config** -- 查看/设置 Git 配置\n"
    "- **git_reset** -- 重置仓库状态\n"
    "- **git_tag** -- 标签管理（列出/创建/删除）\n"
    "\n"
    "---\n"
    "\n"
    "## Go 语言项目开发指南\n"
    "\n"
    "当你需要创建 Go 项目时，遵循以下最佳实践：\n"
    "\n"
    "### 标准目录结构\n"
    "```\n"
    "project/\n"
    "  cmd/server/         # 应用入口，main.go\n"
    "  internal/           # 私有代码\n"
    "    config/           # 配置管理（viper）\n"
    "    handler/          # HTTP 请求处理器\n"
    "    middleware/       # 中间件（鉴权、日志、CORS）\n"
    "    model/            # 数据模型/结构体\n"
    "    repository/       # 数据访问层（MySQL/PostgreSQL）\n"
    "    router/           # 路由注册\n"
    "    service/          # 业务逻辑层\n"
    "  pkg/                # 公共库代码\n"
    "    response/         # 统一响应格式\n"
    "    validator/        # 参数验证器\n"
    "  api/                # API 定义（protobuf / OpenAPI）\n"
    "  configs/            # 配置文件（yaml/toml）\n"
    "  deploy/             # Docker / K8s 部署文件\n"
    "  scripts/            # 构建/迁移脚本\n"
    "  test/               # 集成测试\n"
    "  web/                # 前端静态资源\n"
    "  go.mod\n"
    "  go.sum\n"
    "  Makefile\n"
    "  Dockerfile\n"
    "  docker-compose.yml\n"
    "  .env.example\n"
    "```\n"
    "\n"
    "### 常用框架\n"
    "| 类别 | 框架/库 | 用途 |\n"
    "|------|---------|------|\n"
    "| Web 框架 | **Gin** (最流行)、**Echo** (轻量)、**Fiber** (高性能、类 Express) | HTTP 路由/中间件 |\n"
    "| 命令行 | **Cobra** | CLI 应用开发 |\n"
    "| 配置管理 | **Viper** | 多源配置（yaml/env/远程） |\n"
    "| 日志 | **Zap** (高性能)、**Logrus** | 结构化日志 |\n"
    "| 数据库 | **GORM** (ORM)、**sqlx** | 数据库操作 |\n"
    "| 迁移 | **golang-migrate** | 数据库迁移 |\n"
    "| 验证 | **go-playground/validator** | 参数校验 |\n"
    "| 测试 | **testify** | 断言/mock |\n"
    "| JWT | **golang-jwt** | JWT 鉴权 |\n"
    "| Swagger | **swaggo/swag** | API 文档生成 |\n"
    "\n"
    "### MVC 分层架构\n"
    "\n"
    "**handler（控制器层）**：接收 HTTP 请求 -> 参数校验 -> 调用 service -> 返回响应\n"
    "\n"
    "**service（业务逻辑层）**：实现核心业务逻辑，调用 repository\n"
    "\n"
    "**repository（数据访问层）**：封装数据库操作（CRUD）\n"
    "\n"
    "**model（数据模型）**：定义结构体和 GORM 表映射\n"
    "\n"
    "### 部署配置示例\n"
    "\n"
    "**Dockerfile（多阶段构建）**：\n"
    "- 构建阶段：golang:1.22-alpine，编译二进制\n"
    "- 运行阶段：alpine:latest，仅包含编译产物\n"
    "\n"
    "**docker-compose.yml**：\n"
    "- app 服务 + PostgreSQL/MySQL + Redis\n"
    "- 环境变量通过 .env 注入\n"
    "\n"
    "### 最佳实践检查清单\n"
    "1. 错误处理：始终检查 err，使用 errors.Is / errors.As 判断\n"
    "2. 接口设计：面向接口编程，而非具体实现\n"
    "3. 依赖注入：通过构造函数注入依赖，避免全局变量\n"
    "4. 配置管理：使用 Viper，支持环境变量覆盖\n"
    "5. 日志规范：结构化日志（zap），包含请求ID追踪\n"
    "6. 优雅关闭：处理 SIGTERM/SIGINT 信号\n"
    "7. 测试覆盖：单元测试 + 集成测试\n"
    "8. 并发安全：使用 sync 或 channel\n"
    "9. 代码格式化：运行 gofmt -s -w . 和 go vet ./...\n"
    "10. 安全实践：参数化查询，避免 SQL 注入\n"
    "\n"
    "### 搜索使用提示\n"
    "- 当用户询问最新信息、Go 技术文档、API 用法等需要联网获取的内容时，优先使用 web_search\n"
    "- 如果只需要搜索结果概览，使用 web_search\n"
    "- 如果需要深入了解详情，使用 web_search_and_open\n"
    "\n"
    "---\n"
    "\n"
    "请根据用户的需求，合理使用这些工具来帮助完成编程任务！"
)


def run_one_shot(task: str) -> str:
    """一键执行模式（流式输出）：接收任务描述，调用 LLM + 工具循环，实时流式输出结果

    被 LeaderAgent 通过子进程唤醒时使用，不进入交互式 CLI。
    所有 AI 输出和工具调用结果都会实时打印到 stdout，
    LeaderAgent 的 Popen 流式读取后展示给用户。

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

    # 收集所有中间输出（工具调用结果）
    all_outputs = []
    if assistant_msg.get("content"):
        all_outputs.append(assistant_msg["content"])

    # 工具调用循环
    max_turns = 20  # 防止无限循环
    turn_count = 0

    while assistant_msg.get("tool_calls") and turn_count < max_turns:
        turn_count += 1
        tool_calls = assistant_msg["tool_calls"]

        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            tool_args = json.loads(tc["function"]["arguments"])

            # 调用工具
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

        # 再次调用 LLM（流式输出版）
        assistant_msg = _stream_chat_collect_streaming(messages)
        messages.append(assistant_msg)

        if assistant_msg.get("content"):
            all_outputs.append(assistant_msg["content"])

    # 合并所有输出
    final_result = "\n".join(all_outputs).strip()
    return final_result if final_result else "（无输出）"


def run_agent():
    """运行 CodingAgent 主循环（交互式 CLI，带美化）"""

    messages = [{"role": "system", "content": SYSTEM_PROMPT.strip()}]

    # ═══════════════════════════════════════════════════════════════
    # 欢迎界面
    # ═══════════════════════════════════════════════════════════════
    print_welcome(
        title="🧠  Coding Agent -- 智能代码编程助手",
        subtitle="基于 DeepSeek API 的流式对话 Agent | 支持 Go/Python 项目开发",
        model=MODEL,
        tool_count=len(tools),
        extra_info=[
            "  Go 项目 (Gin/Echo/Fiber) 全流程创建",
            "  文件读写  Shell 执行  联网搜索",
            "输入 /help 查看帮助  |  输入 /exit 退出对话",
        ],
    )

    # ═══════════════════════════════════════════════════════════════
    # 对话主循环
    # ═══════════════════════════════════════════════════════════════
    round_num = 0

    while True:
        try:
            # ── 用户输入 ──
            if HAVE_CLI_INPUT:
                user_input = chinese_input(
                    f"  {Color.BCYN}{Color.BLD}  You{Color.RST} {Color.DIM}>{Color.RST} ",
                    multiline=True,
                )
            else:
                user_input = input(
                    f"  {Color.BCYN}{Color.BLD}  You{Color.RST} {Color.DIM}>{Color.RST} "
                ).strip()

        except (ExitRequested, EOFError, KeyboardInterrupt):
            print()
            print_goodbye("  感谢使用 Coding Agent，期待再次相见！")
            break

        if not user_input:
            continue

        # ── 退出命令 ──
        if user_input.lower() in {"exit", "quit", "/exit", "/quit"} or user_input in {"再见", "退出"}:
            print_goodbye("  感谢使用 Coding Agent，期待再次相见！")
            break

        # ── 帮助命令 ──
        if user_input.lower() in {"/help", "help", "-h", "--help"}:
            print_help([
                ("/help", "显示此帮助信息"),
                ("/exit", "退出程序"),
                ("/quit", "退出程序"),
                ("/clear", "清屏"),
            ])
            continue

        # ── 清屏命令 ──
        if user_input.lower() in {"/clear", "clear"}:
            os.system('cls' if os.name == 'nt' else 'clear')
            continue

        round_num += 1

        # ── 显示用户输入 ──
        print_user_input(user_input)

        messages.append({"role": "user", "content": user_input})

        # ── Agent 回复（流式） ──
        ts = format_timestamp()
        print_agent_start(agent_name=AGENT_NAME, timestamp=ts)

        assistant_msg = stream_chat_with_tools(messages)

        print_agent_end()
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
                        result = f"  参数错误: {e}"
                    except Exception as e:
                        result = f"  执行出错: {e}"
                else:
                    result = f"Unknown tool: {tool_name}"

                # 以美化面板显示工具调用与结果
                print_tool_result(tool_name, tool_args, result)
                print()

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

            # ── Agent 再次回复（流式） ──
            ts = format_timestamp()
            print_agent_start(agent_name=AGENT_NAME, timestamp=ts)

            assistant_msg = stream_chat_with_tools(messages)

            print_agent_end()
            messages.append(assistant_msg)

        # 工具调用结束后，打印一个分隔线区分对话轮次
        if round_num > 0:
            print_separator(color=Color.DIM)


# ═══════════════════════════════════════════════════════════════════════
# 5. 程序入口
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 检查依赖
    try:
        import yaml
    except ImportError:
        print("  建议安装 PyYAML: pip install pyyaml")

    # 解析命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--task":
        # ── 一键执行模式（被 LeaderAgent 唤醒） ──
        task = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not task:
            # 尝试从 stdin 读取
            task = sys.stdin.read().strip()
        if not task:
            print("❌ 错误: --task 参数不能为空。用法: python CodingAgent.py --task \"你的任务描述\"")
            sys.exit(1)
        result = run_one_shot(task)
        # 流式模式下，内容已实时输出，这里只确保返回完整结果
        # 如果上面没有输出任何内容，则打印结果
        sys.exit(0)
    else:
        # ── 交互模式 ──
        run_agent()
