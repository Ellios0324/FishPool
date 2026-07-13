# -*- coding: utf-8 -*-
"""
ModifyAgent - 输出内容优化专家 Agent

基于 DeepSeek API 的流式对话 Agent，专门负责：
- 🎯 将技术输出优化为不同受众能理解的内容
- 📝 支持多种受众画像：技术人员、业务人员、管理者、初学者、高管
- 🌍 多语言输出优化（中/英/日等）
- 🔄 格式转换（Markdown/HTML/PDF/PPT大纲等）
- 📊 输出格式优化（详细报告/简明摘要/要点列表/可视化描述）

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
AGENT_NAME = "Modify Agent"

# 项目根目录
PROJECT_ROOT = Path(__file__).parent


# ═══════════════════════════════════════════════════════════════════════
# 1. 受众画像定义
# ═══════════════════════════════════════════════════════════════════════

AUDIENCE_PROFILES = {
    "developer": {
        "name": "开发者",
        "description": "面向程序员、工程师、技术团队成员",
        "style": "技术精确、代码优先、详细实现细节、使用专业术语",
        "keywords": ["API", "架构", "实现原理", "代码示例", "性能优化", "技术债务"],
        "tone": "专业、精确、深入",
        "detail_level": "高 - 包含技术细节和实现方案",
    },
    "manager": {
        "name": "管理者",
        "description": "面向项目经理、技术主管、部门经理",
        "style": "关注进度、资源、风险、决策点，避免过度技术细节",
        "keywords": ["里程碑", "资源分配", "风险评估", "ROI", "时间线", "依赖关系"],
        "tone": "务实、决策导向、概括性",
        "detail_level": "中 - 关注结论和影响，而非实现细节",
    },
    "executive": {
        "name": "高管",
        "description": "面向 CTO、CEO、VP 等高层决策者",
        "style": "高度概括、商业价值驱动、战略视角、极简技术细节",
        "keywords": ["商业价值", "竞争优势", "战略对齐", "市场影响", "成本效益"],
        "tone": "简洁、有力、战略高度",
        "detail_level": "低 - 仅包含关键结论和建议",
    },
    "beginner": {
        "name": "初学者",
        "description": "面向刚入门的学习者、转行者、非计算机背景人员",
        "style": "通俗易懂、类比丰富、循序渐进、避免行话（必要时解释）",
        "keywords": ["入门", "基础概念", "循序渐进", "常见误区", "学习路径"],
        "tone": "耐心、鼓励、友好、易懂",
        "detail_level": "中 - 概念解释为主，配有类比和图示描述",
    },
    "non_technical": {
        "name": "非技术人员",
        "description": "面向运营、市场、销售、HR 等非技术背景人员",
        "style": "完全避免技术术语，使用生活化类比，关注功能而非实现",
        "keywords": ["功能", "使用场景", "价值", "易用性", "效果"],
        "tone": "通俗、生动、结果导向",
        "detail_level": "低 - 关注功能和价值，不谈技术实现",
    },
    "client": {
        "name": "客户",
        "description": "面向外部客户、甲方、合作伙伴",
        "style": "专业但易懂、突出价值交付、明确的交付物和时间节点",
        "keywords": ["交付物", "时间节点", "服务承诺", "验收标准", "支持服务"],
        "tone": "专业、可靠、服务意识强",
        "detail_level": "中 - 关注交付和价值，适当展示专业度",
    },
    "educator": {
        "name": "教育者",
        "description": "面向教师、培训师、技术写作者、文档维护者",
        "style": "结构清晰、层次分明、包含教学要点和常见问题解答",
        "keywords": ["教学目标", "知识要点", "练习建议", "常见问题", "扩展阅读"],
        "tone": "教学性、系统性、启发性",
        "detail_level": "中高 - 包含教学要点和知识体系",
    },
}

# 输出格式定义
OUTPUT_FORMATS = {
    "detailed_report": {
        "name": "详细报告",
        "description": "完整的结构化报告，包含背景、分析、方案、结论",
    },
    "executive_summary": {
        "name": "高管摘要",
        "description": "一页纸的极简摘要，仅含关键结论和建议",
    },
    "bullet_points": {
        "name": "要点列表",
        "description": "简洁的要点清单，方便快速浏览",
    },
    "markdown_doc": {
        "name": "Markdown 文档",
        "description": "标准 Markdown 格式，适合文档归档",
    },
    "email_draft": {
        "name": "邮件草稿",
        "description": "邮件格式，适合直接发送给相关人员",
    },
    "presentation_outline": {
        "name": "演示文稿大纲",
        "description": "PPT 的大纲结构，包含每页的核心要点",
    },
    "q_and_a": {
        "name": "问答形式",
        "description": "以 Q&A 形式组织内容，适合 FAQ 或知识库",
    },
    "chat_dialog": {
        "name": "对话形式",
        "description": "模拟对话场景，适合教学或演示",
    },
    "step_by_step": {
        "name": "步骤指南",
        "description": "分步操作指南，适合教程和操作手册",
    },
    "comparison_table": {
        "name": "对比表格",
        "description": "以表格对比不同方案的优缺点",
    },
}

# 语言支持
SUPPORTED_LANGUAGES = {
    "zh-CN": "简体中文",
    "zh-TW": "繁体中文",
    "en": "English",
    "ja": "Japanese",
    "ko": "Korean",
}


# ═══════════════════════════════════════════════════════════════════════
# 2. 工具函数定义
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
    """执行 Shell 命令并返回输出"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error executing command: {e}"


def list_audience_profiles() -> str:
    """列出所有可用的受众画像及其详细说明"""
    lines = [f"共 {len(AUDIENCE_PROFILES)} 种受众画像：\n"]
    for key, profile in AUDIENCE_PROFILES.items():
        lines.append(f"  [{key}] {profile['name']}")
        lines.append(f"    -> {profile['description']}")
        lines.append(f"    风格: {profile['style']}")
        lines.append(f"    语气: {profile['tone']}")
        lines.append(f"    详细度: {profile['detail_level']}")
        lines.append("")
    return "\n".join(lines)


def list_output_formats() -> str:
    """列出所有可用的输出格式"""
    lines = [f"共 {len(OUTPUT_FORMATS)} 种输出格式：\n"]
    for key, fmt in OUTPUT_FORMATS.items():
        lines.append(f"  [{key}] {fmt['name']}")
        lines.append(f"    -> {fmt['description']}")
        lines.append("")
    return "\n".join(lines)


def list_supported_languages() -> str:
    """列出支持的语言"""
    lines = ["支持的语言：\n"]
    for code, name in SUPPORTED_LANGUAGES.items():
        lines.append(f"  [{code}] {name}")
    return "\n".join(lines)


def get_audience_style_guide(audience_key: str) -> str:
    """获取指定受众的写作风格指南"""
    if audience_key not in AUDIENCE_PROFILES:
        available = ", ".join(AUDIENCE_PROFILES.keys())
        return f"未知受众: '{audience_key}'。可选: {available}"

    profile = AUDIENCE_PROFILES[audience_key]
    return (
        f"受众画像: {profile['name']}\n"
        f"描述: {profile['description']}\n"
        f"写作风格: {profile['style']}\n"
        f"语气: {profile['tone']}\n"
        f"详细程度: {profile['detail_level']}\n"
        f"关键词: {', '.join(profile['keywords'])}"
    )


def check_syntax(file_path: str) -> str:
    """自动检测文件类型并检查语法"""
    if not os.path.exists(file_path):
        return f"File not found: {file_path}"

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".py":
        result = subprocess.run(
            ["python", "-m", "py_compile", file_path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return "Python syntax check passed."
        return f"Python syntax errors:\n{result.stderr}"

    elif ext in (".yaml", ".yml"):
        try:
            import yaml
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            return "YAML syntax check passed."
        except Exception as e:
            return f"YAML syntax errors:\n{e}"

    elif ext == ".md":
        return "Markdown file - confirmed readable."

    elif ext in (".json",):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return "JSON syntax check passed."
        except Exception as e:
            return f"JSON syntax errors:\n{e}"

    else:
        return f"Auto syntax check not supported for .{ext} files."


def web_search(query: str, max_results: int = 5) -> str:
    """通过 Bing 搜索互联网，返回格式化的搜索结果"""
    import urllib.request
    import urllib.parse

    try:
        max_results = min(max(max_results, 1), 20)
        params = {"q": query, "count": min(max_results, 20), "mkt": "zh-CN"}
        url = "https://www.bing.com/search?" + urllib.parse.urlencode(params)

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode("utf-8", errors="ignore")

        results = []
        h2_pattern = re.compile(
            r'<h2[^>]*>.*?<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>.*?</h2>',
            re.DOTALL | re.IGNORECASE,
        )
        for m in h2_pattern.finditer(html):
            link = m.group(1)
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            snippet = ""
            after_h2 = html[m.end(): m.end() + 2000]
            snippet_match = re.search(r'<p[^>]*>(.*?)</p>', after_h2, re.DOTALL)
            if snippet_match:
                snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip()
                snippet = re.sub(r"\s+", " ", snippet)[:300]
            results.append({"title": title, "href": link, "body": snippet})
            if len(results) >= max_results:
                break

        if not results:
            return f"Search '{query}' found no results."

        output = [f"Search results for '{query}' ({len(results)} results):\n"]
        for i, r in enumerate(results, 1):
            output.append(f"{i}. {r['title']}")
            output.append(f"   Link: {r['href']}")
            if r['body']:
                output.append(f"   Summary: {r['body']}")
            output.append("")

        return "\n".join(output)

    except urllib.error.HTTPError as e:
        return f"Search request rejected (HTTP {e.code})"
    except urllib.error.URLError as e:
        return f"Network error: {e.reason}"
    except Exception as e:
        return f"Search error: {e}"


# ═══════════════════════════════════════════════════════════════════════
# 3. 优化处理函数（核心逻辑）
# ═══════════════════════════════════════════════════════════════════════

def optimize_content(
    content: str,
    audience: str = "developer",
    output_format: str = "detailed_report",
    language: str = "zh-CN",
    additional_instructions: str = "",
) -> str:
    """使用 LLM 优化内容以适应目标受众

    Args:
        content: 原始内容文本
        audience: 目标受众标识
        output_format: 输出格式标识
        language: 目标语言
        additional_instructions: 额外的优化指令

    Returns:
        优化后的内容
    """
    if audience not in AUDIENCE_PROFILES:
        return f"Unknown audience: '{audience}'"
    if output_format not in OUTPUT_FORMATS:
        return f"Unknown format: '{output_format}'"
    if language not in SUPPORTED_LANGUAGES:
        return f"Unsupported language: '{language}'"

    profile = AUDIENCE_PROFILES[audience]
    fmt = OUTPUT_FORMATS[output_format]
    lang_name = SUPPORTED_LANGUAGES[language]

    system_prompt = SYSTEM_PROMPT


    if additional_instructions:
        system_prompt += f"\n## Additional Instructions\n{additional_instructions}\n"

    user_prompt = f"Please optimize the following content:\n\n{content}"

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            temperature=0.4,
            max_tokens=4096,
        )

        optimized = response.choices[0].message.content.strip()

        # Add optimization metadata footer
        meta_info = (
            f"\n\n---\n"
            f"Target: {profile['name']} | "
            f"Format: {fmt['name']} | "
            f"Language: {lang_name}"
        )

        return optimized + meta_info

    except Exception as e:
        return f"Optimization error: {e}"


# ═══════════════════════════════════════════════════════════════════════
# 4. 工具的 JSON Schema
# ═══════════════════════════════════════════════════════════════════════

tools = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定文件的内容（用于获取需要优化的原始内容）",
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
            "description": "将优化后的内容写入指定文件",
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
            "description": "执行 Shell 命令",
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
            "name": "list_audience_profiles",
            "description": "列出所有可用的受众画像及其详细说明，帮助用户选择目标受众",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_output_formats",
            "description": "列出所有可用的输出格式",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_supported_languages",
            "description": "列出支持的语言代码和名称",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_audience_style_guide",
            "description": "获取指定受众的详细写作风格指南",
            "parameters": {
                "type": "object",
                "properties": {
                    "audience_key": {
                        "type": "string",
                        "description": "受众标识，如 developer, manager, executive, beginner, non_technical, client, educator"
                    }
                },
                "required": ["audience_key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_content",
            "description": "使用 AI 优化内容以适应目标受众。核心功能：传入原始内容和优化参数，返回优化后的内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "要优化的原始内容文本"},
                    "audience": {
                        "type": "string",
                        "description": "目标受众标识: developer, manager, executive, beginner, non_technical, client, educator",
                        "default": "developer"
                    },
                    "output_format": {
                        "type": "string",
                        "description": "输出格式: detailed_report, executive_summary, bullet_points, markdown_doc, email_draft, presentation_outline, q_and_a, chat_dialog, step_by_step, comparison_table",
                        "default": "detailed_report"
                    },
                    "language": {
                        "type": "string",
                        "description": "目标语言代码: zh-CN, zh-TW, en, ja, ko",
                        "default": "zh-CN"
                    },
                    "additional_instructions": {
                        "type": "string",
                        "description": "额外的优化指令",
                        "default": ""
                    }
                },
                "required": ["content", "audience"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_syntax",
            "description": "检查文件的语法（支持 .py, .yaml, .yml, .json, .md）",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "要检查的文件路径"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索互联网，获取最新信息以丰富优化内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数量",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
]

tool_functions = {
    "read_file": read_file,
    "write_file": write_file,
    "run_shell_command": run_shell_command,
    "list_audience_profiles": list_audience_profiles,
    "list_output_formats": list_output_formats,
    "list_supported_languages": list_supported_languages,
    "get_audience_style_guide": get_audience_style_guide,
    "optimize_content": optimize_content,
    "check_syntax": check_syntax,
    "web_search": web_search,
}


# ═══════════════════════════════════════════════════════════════════════
# 5a. 流式调用 + Tool Calls 累积（非打印模式，用于收集）
# ═══════════════════════════════════════════════════════════════════════

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
# 5b. 流式调用 + 实时输出（用于 --task 流式模式，被 LeaderAgent 调用）
# ═══════════════════════════════════════════════════════════════════════

def _stream_chat_collect_streaming(messages: list) -> dict:
    """流式调用 DeepSeek API，实时打印到 stdout，同时累积 tool_calls

    与 _stream_chat_collect 的区别：
    - 每收到一个 content chunk，立即用 sys.stdout.write() + flush() 输出
    - 这样 LeaderAgent 通过 PIPE 读取时可以实时获取到流式内容
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
# 5c. 流式调用 + Tool Calls 累积（打印模式，用于交互式）
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

        if delta.content:
            content_parts.append(delta.content)
            print(delta.content, end="", flush=True)

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
# 5d. 一键执行模式（被 LeaderAgent 唤醒时使用，流式输出）
# ═══════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = (
    "你是一个专业的 Modify Agent（内容优化专家），"
    "专门负责将不同 Agent 的输出结果针对不同人群进行优化。\n"
    "\n"
    "## 核心能力\n"
    "你可以将任何技术内容（代码输出、项目报告、技术文档等）"
    "优化为适合特定受众的版本。\n"
    "\n"
    "## 可用工具\n"
    "\n"
    "### 文件操作\n"
    "- read_file -- 读取需要优化的原始内容\n"
    "- write_file -- 将优化后的内容写入文件\n"
    "\n"
    "### 命令执行\n"
    "- run_shell_command -- 执行 Shell 命令\n"
    "\n"
    "### 受众管理（核心工具）\n"
    "- list_audience_profiles -- 列出所有可用的受众画像\n"
    "- list_output_formats -- 列出所有可用的输出格式\n"
    "- list_supported_languages -- 列出支持的语言\n"
    "- get_audience_style_guide -- 获取指定受众的写作风格指南\n"
    "\n"
    "### 优化执行（核心工具）\n"
    "- optimize_content -- 使用 AI 将内容优化为目标受众版本\n"
    "\n"
    "### 语法检查\n"
    "- check_syntax -- 检查文件语法\n"
    "\n"
    "### 联网搜索\n"
    "- web_search -- 搜索互联网获取参考信息\n"
    "\n"
    "---\n"
    "\n"
    "## 可用受众画像（7种）\n"
    "| 标识 | 名称 | 适用场景 |\n"
    "|------|------|---------|\n"
    "| developer | 开发者 | 程序员、工程师需要技术细节和代码示例 |\n"
    "| manager | 管理者 | 项目经理关注进度、资源和风险 |\n"
    "| executive | 高管 | CTO/CEO 需要战略视角和商业价值 |\n"
    "| beginner | 初学者 | 入门者需要通俗易懂的类比和解释 |\n"
    "| non_technical | 非技术人员 | 运营/市场需要了解功能而非实现 |\n"
    "| client | 客户 | 外部客户关注交付和价值 |\n"
    "| educator | 教育者 | 教师/培训师需要教学性内容 |\n"
    "\n"
    "## 可用输出格式（10种）\n"
    "| 标识 | 名称 | 说明 |\n"
    "|------|------|------|\n"
    "| detailed_report | 详细报告 | 完整的结构化报告 |\n"
    "| executive_summary | 高管摘要 | 一页纸极简摘要 |\n"
    "| bullet_points | 要点列表 | 简洁要点清单 |\n"
    "| markdown_doc | Markdown文档 | 标准 Markdown 格式 |\n"
    "| email_draft | 邮件草稿 | 可直接发送的邮件格式 |\n"
    "| presentation_outline | 演示文稿大纲 | PPT 大纲结构 |\n"
    "| q_and_a | 问答形式 | Q&A 格式，适合 FAQ |\n"
    "| chat_dialog | 对话形式 | 模拟对话场景 |\n"
    "| step_by_step | 步骤指南 | 分步操作指南 |\n"
    "| comparison_table | 对比表格 | 表格对比方案 |\n"
    "\n"
    "## 典型工作流程\n"
    "1. 用户给出内容（直接描述或指文件路径）\n"
    "2. 你确认目标受众和格式\n"
    "3. 如果用户不确定，调用 list_audience_profiles 展示选项\n"
    "4. 调用 optimize_content 执行优化\n"
    "5. 展示优化结果给用户\n"
    "6. 可选: 将结果写入文件\n"
    "\n"
    "## 优化原则\n"
    "1. 保留核心信息 - 不丢失原文的关键数据、结论和建议\n"
    "2. 适配受众 - 根据受众调整词汇、深度和表达方式\n"
    "3. 保持准确 - 优化不是篡改，技术内容必须准确无误\n"
    "4. 提供选择 - 如果用户不确定受众，主动推荐最合适的选项\n"
    "5. 一站式完成 - 从读取内容到输出优化结果，一气呵成\n"
    "\n"
    "---\n"
    "\n"
    "请根据用户的需求，合理使用这些工具来完成内容优化任务！"
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


# ═══════════════════════════════════════════════════════════════════════
# 6. Agent 主循环（美化版 CLI）
# ═══════════════════════════════════════════════════════════════════════

def run_agent():
    """运行 ModifyAgent 主循环（带美化 CLI）"""

    system_prompt = (
        "你是一个专业的 Modify Agent（内容优化专家），"
        "专门负责将不同 Agent 的输出结果针对不同人群进行优化。\n"
        "\n"
        "## 核心能力\n"
        "你可以将任何技术内容（代码输出、项目报告、技术文档等）"
        "优化为适合特定受众的版本。\n"
        "\n"
        "## 可用工具\n"
        "\n"
        "### 文件操作\n"
        "- read_file -- 读取需要优化的原始内容\n"
        "- write_file -- 将优化后的内容写入文件\n"
        "\n"
        "### 命令执行\n"
        "- run_shell_command -- 执行 Shell 命令\n"
        "\n"
        "### 受众管理（核心工具）\n"
        "- list_audience_profiles -- 列出所有可用的受众画像\n"
        "- list_output_formats -- 列出所有可用的输出格式\n"
        "- list_supported_languages -- 列出支持的语言\n"
        "- get_audience_style_guide -- 获取指定受众的写作风格指南\n"
        "\n"
        "### 优化执行（核心工具）\n"
        "- optimize_content -- 使用 AI 将内容优化为目标受众版本\n"
        "\n"
        "### 语法检查\n"
        "- check_syntax -- 检查文件语法\n"
        "\n"
        "### 联网搜索\n"
        "- web_search -- 搜索互联网获取参考信息\n"
        "\n"
        "---\n"
        "\n"
        "## 可用受众画像（7种）\n"
        "| 标识 | 名称 | 适用场景 |\n"
        "|------|------|---------|\n"
        "| developer | 开发者 | 程序员、工程师需要技术细节和代码示例 |\n"
        "| manager | 管理者 | 项目经理关注进度、资源和风险 |\n"
        "| executive | 高管 | CTO/CEO 需要战略视角和商业价值 |\n"
        "| beginner | 初学者 | 入门者需要通俗易懂的类比和解释 |\n"
        "| non_technical | 非技术人员 | 运营/市场需要了解功能而非实现 |\n"
        "| client | 客户 | 外部客户关注交付和价值 |\n"
        "| educator | 教育者 | 教师/培训师需要教学性内容 |\n"
        "\n"
        "## 可用输出格式（10种）\n"
        "| 标识 | 名称 | 说明 |\n"
        "|------|------|------|\n"
        "| detailed_report | 详细报告 | 完整的结构化报告 |\n"
        "| executive_summary | 高管摘要 | 一页纸极简摘要 |\n"
        "| bullet_points | 要点列表 | 简洁要点清单 |\n"
        "| markdown_doc | Markdown文档 | 标准 Markdown 格式 |\n"
        "| email_draft | 邮件草稿 | 可直接发送的邮件格式 |\n"
        "| presentation_outline | 演示文稿大纲 | PPT 大纲结构 |\n"
        "| q_and_a | 问答形式 | Q&A 格式，适合 FAQ |\n"
        "| chat_dialog | 对话形式 | 模拟对话场景 |\n"
        "| step_by_step | 步骤指南 | 分步操作指南 |\n"
        "| comparison_table | 对比表格 | 表格对比方案 |\n"
        "\n"
        "## 典型工作流程\n"
        "1. 用户给出内容（直接描述或指文件路径）\n"
        "2. 你确认目标受众和格式\n"
        "3. 如果用户不确定，调用 list_audience_profiles 展示选项\n"
        "4. 调用 optimize_content 执行优化\n"
        "5. 展示优化结果给用户\n"
        "6. 可选: 将结果写入文件\n"
        "\n"
        "## 优化原则\n"
        "1. 保留核心信息 - 不丢失原文的关键数据、结论和建议\n"
        "2. 适配受众 - 根据受众调整词汇、深度和表达方式\n"
        "3. 保持准确 - 优化不是篡改，技术内容必须准确无误\n"
        "4. 提供选择 - 如果用户不确定受众，主动推荐最合适的选项\n"
        "5. 一站式完成 - 从读取内容到输出优化结果，一气呵成\n"
        "\n"
        "---\n"
        "\n"
        "请根据用户的需求，合理使用这些工具来完成内容优化任务！"
    )

    messages = [{"role": "system", "content": system_prompt.strip()}]

    # Welcome screen
    print_welcome(
        title="Modify Agent -- 内容优化专家",
        subtitle="将技术输出针对不同受众进行专业化优化 | 7种受众 x 10种格式 x 5种语言",
        model=MODEL,
        tool_count=len(tools),
        extra_info=[
            "  7种受众画像: 开发者 / 管理者 / 高管 / 初学者 / 非技术人员 / 客户 / 教育者",
            "  10种输出格式: 报告 / 摘要 / 邮件 / PPT / FAQ / 对话 / 指南 / 表格...",
            "  5种语言: 简体中文 / 繁体中文 / English / Japanese / Korean",
            "输入 /help 查看帮助  |  输入 /exit 退出对话",
        ],
    )

    round_num = 0

    while True:
        try:
            user_input = input(
                f"  {Color.BCYN}{Color.BLD}  You{Color.RST} {Color.DIM}>{Color.RST} "
            ).strip()

        except (EOFError, KeyboardInterrupt):
            print()
            print_goodbye("  感谢使用 Modify Agent，期待再次相见！")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", "/exit", "/quit"} or user_input in {"再见", "退出"}:
            print_goodbye("  感谢使用 Modify Agent，期待再次相见！")
            break

        if user_input.lower() in {"/help", "help", "-h", "--help"}:
            print_help([
                ("/help", "显示此帮助信息"),
                ("/exit", "退出程序"),
                ("/quit", "退出程序"),
                ("/clear", "清屏"),
                ("/profiles", "列出所有受众画像"),
                ("/formats", "列出所有输出格式"),
                ("/languages", "列出支持的语言"),
            ])
            continue

        if user_input.lower() in {"/profiles", "profiles"}:
            result = list_audience_profiles()
            width = min(get_term_width() - 2, 80)
            print_panel(content=result, title="Audience Profiles", color=Color.INFO, width=width)
            continue

        if user_input.lower() in {"/formats", "formats"}:
            result = list_output_formats()
            width = min(get_term_width() - 2, 80)
            print_panel(content=result, title="Output Formats", color=Color.INFO, width=width)
            continue

        if user_input.lower() in {"/languages", "languages"}:
            result = list_supported_languages()
            width = min(get_term_width() - 2, 80)
            print_panel(content=result, title="Supported Languages", color=Color.INFO, width=width)
            continue

        if user_input.lower() in {"/clear", "clear"}:
            os.system('cls' if os.name == 'nt' else 'clear')
            continue

        round_num += 1

        print_user_input(user_input)

        messages.append({"role": "user", "content": user_input})

        ts = format_timestamp()
        print_agent_start(agent_name=AGENT_NAME, timestamp=ts)

        assistant_msg = stream_chat_with_tools(messages)

        print_agent_end()
        messages.append(assistant_msg)

        # Tool call loop
        while assistant_msg.get("tool_calls"):
            tool_calls = assistant_msg["tool_calls"]

            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                tool_args = json.loads(tc["function"]["arguments"])

                if tool_name in tool_functions:
                    try:
                        result = tool_functions[tool_name](**tool_args)
                    except TypeError as e:
                        result = f"  Parameter error: {e}"
                    except Exception as e:
                        result = f"  Execution error: {e}"
                else:
                    result = f"Unknown tool: {tool_name}"

                print_tool_result(tool_name, tool_args, result)
                print()

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

            ts = format_timestamp()
            print_agent_start(agent_name=AGENT_NAME, timestamp=ts)

            assistant_msg = stream_chat_with_tools(messages)

            print_agent_end()
            messages.append(assistant_msg)

        if round_num > 0:
            print_separator(color=Color.DIM)


# ═══════════════════════════════════════════════════════════════════════
# 7. 程序入口
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 解析命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--task":
        # ── 一键执行模式（被 LeaderAgent 唤醒） ──
        task = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not task:
            task = sys.stdin.read().strip()
        if not task:
            print("❌ 错误: --task 参数不能为空。用法: python ModifyAgent.py --task \"你的任务描述\"")
            sys.exit(1)
        result = run_one_shot(task)
        # 流式模式下，内容已实时输出
        sys.exit(0)
    else:
        # ── 交互模式 ──
        run_agent()
