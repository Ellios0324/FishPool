"""
FishPool — 智能调度入口 Agent（Claude Code 风格美化版）

作为 Agent 系统的「大脑」，职责仅限于三个核心能力：

  🧩 1. 拆分需求   — 分析用户输入的复杂需求，拆分为可执行的子任务单元
  🎯 2. 分配任务   — 将每个子任务路由到最合适的 Agent 处理
  🚀 3. 唤醒执行   — 通过子进程唤醒对应的 Agent，实时流式输出执行过程

## ✅ 中文输入修复
使用 cli_input 模块替代原生 input()，解决中文输入时退格键需按两次、
方向键导航异常等 bug。

## ⌨️ 中断处理
- 在提示符处按 Ctrl+C → 打印告别信息 → 退出程序
- 在任务执行中按 Ctrl+C → 终止当前任务 → 回到提示符
"""

import os
import re
import json
import sys
import subprocess
import threading
from pathlib import Path
from datetime import datetime

from openai import OpenAI
from dotenv import load_dotenv

# ─── 加载环境变量 ───
load_dotenv()

# ─── 初始化 DeepSeek 客户端 ───
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

MODEL = "deepseek-v4-flash"
AGENT_NAME = "FishPool"
VERSION = "2.0.0"

# ─── 项目根目录 ───
PROJECT_ROOT = Path(__file__).parent

# ─── 子 Agent 路径 ───
CODING_AGENT_PATH = PROJECT_ROOT / "CodingAgent.py"
SKILLS_MANAGER_PATH = PROJECT_ROOT / "SkillsManager.py"
MODIFY_AGENT_PATH = PROJECT_ROOT / "ModifyAgent.py"
WEATHER_AGENT_PATH = PROJECT_ROOT / "WeatherAgent.py"

# ─── 导入联网搜索模块（自包含，无需子进程）───
from AgentSkills.skills.web_search import (
    smart_search,
    search_news,
    web_search_and_open,
)

# ─── 从 cli_style 导入美化函数 ───
from cli_style import (
    Color, cprint, get_term_width, format_timestamp, format_full_timestamp,
    print_panel, print_banner, print_tool_result,
    print_user_input, print_agent_start, print_agent_end,
    print_welcome, print_goodbye,
    print_help, print_separator, print_status, truncate_text,
    print_ascii_banner, print_small_banner,
    print_system_message, print_thinking_message, print_result_message,
    print_error_message, print_warn_message, print_tagged_line,
    print_thinking_indicator, clear_thinking_indicator, Spinner,
    print_code_indent, print_code_block,
    print_bullet_list, print_numbered_list,
    print_claude_tool_call, print_claude_result_line,
    print_claude_separator, build_claude_prompt, build_prompt_with_label,
    print_leader_status_line, print_leader_info_line,
    print_claude_welcome,
    LEADER_ASCII, AGENT_ASCII, CODING_ASCII,
    strip_ansi, get_visible_width,
)

# ─── 导入中文友好的输入模块 ───
try:
    from cli_input import chinese_input, ExitRequested
    HAVE_CLI_INPUT = True
except ImportError:
    HAVE_CLI_INPUT = False

    def chinese_input(prompt="", **kwargs):
        try:
            return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            raise ExitRequested() from None

    class ExitRequested(BaseException):
        pass


# ═══════════════════════════════════════════════════════════════════════
# 1. Agent 调度工具（流式输出版本）
# ═══════════════════════════════════════════════════════════════════════

def _run_agent_subprocess(agent_path: Path, agent_name: str, task: str) -> str:
    """通过子进程唤醒指定的 Agent 执行任务，**流式输出**执行过程

    使用 subprocess.Popen + 线程逐块读取 stdout，实时打印子 Agent 的输出。
    子 Agent 的 workflow（LLM 流式思考 + 工具调用）会实时呈现给用户。

    支持 Ctrl+C 中断：当用户在子 Agent 执行过程中按下 Ctrl+C，
    会终止子进程并返回中断提示信息。

    Args:
        agent_path: Agent 脚本的完整路径
        agent_name: Agent 名称（用于错误提示）
        task: 要执行的任务描述

    Returns:
        Agent 执行结果文本（完整输出）
    """
    if not agent_path.exists():
        return f"❌ {agent_name}.py 不存在，请确保它在项目根目录。"

    process = None
    stdout_thread = None
    stderr_thread = None
    read_complete = threading.Event()

    try:
        # ── 使用 Popen 启动子进程（支持流式读取） ──
        process = subprocess.Popen(
            [sys.executable, str(agent_path), "--task", task],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )

        output_parts: list[str] = []
        error_parts: list[str] = []

        def read_stdout():
            try:
                while True:
                    chunk = process.stdout.read(4096)
                    if not chunk:
                        break
                    print(chunk, end="", flush=True)
                    output_parts.append(chunk)
            except (ValueError, OSError):
                pass
            finally:
                read_complete.set()

        def read_stderr():
            try:
                for line in iter(process.stderr.readline, ""):
                    error_parts.append(line)
            except (ValueError, OSError):
                pass

        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        try:
            process.wait(timeout=600)
        except KeyboardInterrupt:
            print()
            process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            read_complete.wait(timeout=5)
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()
            if stdout_thread and stdout_thread.is_alive():
                stdout_thread.join(timeout=3)
            if stderr_thread and stderr_thread.is_alive():
                stderr_thread.join(timeout=3)
            cprint(f"  ⚠️  {agent_name} 任务已被用户中断\n", Color.WARN)
            print()
            return f"⚠️ 任务已被用户中断（{agent_name}）"
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            read_complete.wait(timeout=5)
            return f"❌ {agent_name} 执行超时（超过 10 分钟），请尝试拆分任务为更小的步骤。"

        read_complete.wait(timeout=10)
        if stdout_thread and stdout_thread.is_alive():
            stdout_thread.join(timeout=5)
        if stderr_thread and stderr_thread.is_alive():
            stderr_thread.join(timeout=5)

        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()

        output = "".join(output_parts).strip()
        error_output = "".join(error_parts).strip()

        if process.returncode != 0 and not output:
            return (
                f"❌ {agent_name} 执行失败 (exit code {process.returncode})\n"
                f"{error_output or '无输出'}"
            )

        if error_output:
            output += f"\n\n⚠️ 警告信息:\n{error_output}"

        return output

    except KeyboardInterrupt:
        if process:
            try:
                process.kill()
                process.wait(timeout=5)
            except Exception:
                pass
        cprint(f"  ⚠️  {agent_name} 任务已被用户中断\n", Color.WARN)
        print()
        return f"⚠️ 任务已被用户中断（{agent_name}）"
    except Exception as e:
        return f"❌ 唤醒 {agent_name} 时出错: {e}"


def run_coding_agent(task: str) -> str:
    """🚀 唤醒 KillerWhale 处理编程任务（流式输出）"""
    return _run_agent_subprocess(CODING_AGENT_PATH, "KillerWhale", task)


def run_skills_manager(task: str) -> str:
    """🚀 唤醒 FishFarmer 处理技能管理任务（流式输出）"""
    return _run_agent_subprocess(SKILLS_MANAGER_PATH, "FishFarmer", task)


def run_web_search(task: str) -> str:
    """🔍 直接联网搜索（集成在 FishPool 内部，无需子进程）"""
    # 注意：这个函数保留作为备用接口，实际搜索通过直接函数调用完成
    return task  # 占位，实际由 LLM 直接调用 smart_search 等函数


def run_modify_agent(task: str) -> str:
    """🚀 唤醒 ModifyAgent 处理内容优化任务（流式输出）"""
    return _run_agent_subprocess(MODIFY_AGENT_PATH, "ModifyAgent", task)


def run_weather_agent(task: str) -> str:
    """🚀 唤醒 Dolphin 查询天气信息（流式输出）"""
    return _run_agent_subprocess(WEATHER_AGENT_PATH, "Dolphin", task)


def launch_sub_agent(agent_name: str) -> str:
    """🚀 启动子 Agent 独立交互模式

    当用户需要与某个子 Agent 进行多轮深度对话时使用。

    Args:
        agent_name: Agent 名称

    Returns:
        启动指引信息
    """
    agent_map = {
        "codingagent": ("KillerWhale", CODING_AGENT_PATH),
        "skillsmanager": ("FishFarmer", SKILLS_MANAGER_PATH),
        "modifyagent": ("ModifyAgent", MODIFY_AGENT_PATH),
        "weatheragent": ("Dolphin", WEATHER_AGENT_PATH),
    }

    key = agent_name.lower().replace(" ", "").replace("-", "").replace("_", "")
    if key not in agent_map:
        available = list(agent_map.keys())
        return f"❌ 未知的 Agent: '{agent_name}'。可选: {', '.join(available)}"

    display_name, agent_path = agent_map[key]

    if not agent_path.exists():
        return f"❌ {display_name}.py 不存在: {agent_path}"

    return (
        f"🚀 正在为您启动 {display_name} 的独立交互模式...\n\n"
        f"请在新终端中执行以下命令：\n\n"
        f"  cd {PROJECT_ROOT} && python {agent_path.name}\n\n"
        f"或者您可以直接在这里描述需求，我帮您调度到对应的 Agent。"
    )


# ═══════════════════════════════════════════════════════════════════════
# 2. 工具的 JSON Schema
# ═══════════════════════════════════════════════════════════════════════

tools = [
    {
        "type": "function",
        "function": {
            "name": "run_coding_agent",
            "description": "【编程任务】启动 KillerWhale 处理代码编写/修改/检查/项目创建等编程任务。适用于：创建Go/Python项目、编写脚本、修改代码、语法检查、运行Shell命令、联网搜索技术方案。任何与代码、编程、开发相关的需求都使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "要让 KillerWhale 完成的完整任务描述，包含所有需求细节、文件路径、代码内容等"
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_skills_manager",
            "description": "【技能管理】启动 FishFarmer 管理 AgentSkills 包中的技能。适用于：列出所有技能、查看技能详情、创建新技能、修改技能代码、删除技能、测试技能功能。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "要让 FishFarmer 完成的技能管理任务描述，包含操作类型和参数"
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "【联网搜索】直接搜索互联网信息，返回标题、链接和摘要。支持多引擎切换(Bing/Google/DuckDuckGo/Baidu)、时间范围过滤、语言选择。适用于查询新闻资讯、搜索技术文档、调研资料、查找实时信息等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，应精确且包含核心概念"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数量（默认5，最多20）"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "时间范围过滤：None(不限)/24h(近24小时)/7d(近一周)/30d(近一月)/1y(近一年)"
                    },
                    "language": {
                        "type": "string",
                        "description": "搜索语言：zh(中文)/en(英文)/ja(日文)等"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "【新闻搜索】专门搜索最新新闻资讯，支持时间范围过滤和中英文双语搜索。适合查询时事政治、热点事件等时效性强的信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "新闻搜索关键词"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数量（默认10，最多30）"
                    },
                    "language": {
                        "type": "string",
                        "description": "搜索语言：zh(中文)/en(英文)"
                    },
                    "time_period": {
                        "type": "string",
                        "description": "时间范围：24h/7d(默认)/30d/1y"
                    },
                    "bilingual": {
                        "type": "boolean",
                        "description": "是否启用中英文双语搜索（默认false）"
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
            "description": "【搜索并打开网页】搜索互联网并获取指定结果的页面正文详细内容。适合需要深入了解某个特定主题详情时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "result_index": {
                        "type": "integer",
                        "description": "打开第几条结果（从1开始，默认1）"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_modify_agent",
            "description": "【内容优化】启动 ModifyAgent 将技术输出针对不同受众进行专业化改写/翻译/格式转换。适用于：面向开发者的技术文档→面向管理者的汇报→面向高管的摘要→面向初学者的教程→面向客户的方案→面向非技术人员的功能说明。支持7种受众x10种格式x5种语言。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "要让 ModifyAgent 完成的内容优化任务描述，包含需要优化的原始内容和目标受众/格式/语言"
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_weather_agent",
            "description": "【天气查询】启动 Dolphin 查询天气信息。适用于：查询任意城市未来7天的天气预报、穿衣建议、生活小提示。例如「北京未来7天天气怎么样」「上海明天适合穿什么衣服」「查询东京的天气」等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "要让 Dolphin 完成的天气查询任务描述，包含城市名称"
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "launch_sub_agent",
            "description": "【交互模式】在独立终端中启动指定子 Agent 的完整交互模式。用于需要多轮深度对话的复杂场景，如逐步调试代码、迭代修改技能、持续查询天气。可选: KillerWhale(编程), FishFarmer(技能管理), ModifyAgent(内容优化), Dolphin(天气查询)",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Agent 名称: 'KillerWhale'(编程), 'FishFarmer'(技能管理), 'ModifyAgent'(内容优化), 'Dolphin'(天气查询)"
                    }
                },
                "required": ["agent_name"]
            }
        }
    },
]

tool_functions = {
    "run_coding_agent": run_coding_agent,
    "run_skills_manager": run_skills_manager,
    "run_web_search": run_web_search,
    "web_search": lambda **kwargs: smart_search(**kwargs),
    "search_news": lambda **kwargs: search_news(**kwargs),
    "web_search_and_open": lambda **kwargs: web_search_and_open(**kwargs),
    "run_modify_agent": run_modify_agent,
    "run_weather_agent": run_weather_agent,
    "launch_sub_agent": launch_sub_agent,
}


# ═══════════════════════════════════════════════════════════════════════
# 3. 流式调用 + Tool Calls 累积
# ═══════════════════════════════════════════════════════════════════════

def stream_chat_with_tools(messages: list) -> dict:
    """流式调用 DeepSeek API，实时打印文本内容，同时累积 tool_calls

    支持通过 KeyboardInterrupt 中断 API 流式调用。

    Args:
        messages: 消息列表

    Returns:
        assistant 消息字典

    Raises:
        KeyboardInterrupt: 如果用户在流式输出过程中按下 Ctrl+C
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

    assistant_msg: dict = {"role": "assistant", "content": content if content else None}
    if tool_calls_list:
        assistant_msg["tool_calls"] = tool_calls_list

    return assistant_msg


# ═══════════════════════════════════════════════════════════════════════
# 4. Agent 主循环（Claude Code 风格美化版）
# ═══════════════════════════════════════════════════════════════════════

def build_system_prompt() -> str:
    """构建系统提示词"""
    return """
你是一个智能的 **FishPool** —— Agent 系统的「大脑」和统一入口。

## 🎯 你的核心职责（只有三件事）

### 🧩 1. 拆分需求
当用户提出一个复杂的、多步骤的需求时，先帮用户分析需求，
拆分成清晰的子任务，然后逐一调度。

### 🎯 2. 分配任务
根据需求类型，路由到最合适的 Agent：

| 需求类型 | 调用的 Agent | 说明 |
|---------|-------------|------|
| 编程/代码/项目创建 | **run_coding_agent** | 任何与代码编写、修改、检查、项目创建、Shell命令相关 |
| 技能管理 | **run_skills_manager** | 查看、创建、修改、删除、测试 AgentSkills 中的技能 |
| 联网搜索/信息查询/资讯 | **web_search / search_news** | 🔍 直接搜索最新资讯/技术资料/热点新闻并总结 |
| 内容优化/改写/翻译 | **run_modify_agent** | 将技术内容面向不同受众改写、翻译、格式转换 |
| 天气查询/预报 | **run_weather_agent** | 查询城市未来天气、穿衣建议、生活小提示 |
| 需要多轮深度对话 | **launch_sub_agent** | 启动独立交互模式 |

### 🚀 3. 唤醒执行（流式输出）
调用对应的工具唤醒子 Agent 执行任务。子 Agent 的 workflow 将以**流式方式**
实时呈现给用户，包括 LLM 思考过程、工具调用结果等。

---

## 🌟 核心原则

1. **不直接执行** — 你不操作文件、不执行命令、不搜索、不检查语法，
   这些具体工作全部交给子 Agent 完成
2. **先分析再调度** — 复杂需求先拆解，再逐一调度
3. **一个任务对应一个调度** — 尽量将相关的子任务合并为一次调度，
   让子 Agent 自主完成
4. **传递完整上下文** — 调度时传递足够的细节，确保子 Agent 理解需求
5. **子 Agent 的结果即答案** — 子 Agent 返回的结果直接呈现给用户，
   不需要额外加工
6. **流式呈现** — 子 Agent 的 workflow（LLM 思考 + 工具调用）会实时流式输出，
   用户可以看到完整的执行过程
""".strip()


def print_startup_banner():
    """打印启动横幅（Claude Code 风格 ASCII 艺术）"""
    print_ascii_banner(
        title_ascii=LEADER_ASCII,
        subtitle="Agent 调度大脑 · 统一入口",
        version=VERSION,
        color=Color.BRAND,
    )


def print_agent_catalog():
    """打印可用 Agent 目录"""
    width = min(get_term_width() - 2, 80)
    width = max(width, 50)
    sep = "━"

    # ── 模型信息和工具计数 ──
    coding_exists = CODING_AGENT_PATH.exists()
    sm_exists = SKILLS_MANAGER_PATH.exists()
    ma_exists = MODIFY_AGENT_PATH.exists()
    wa_exists = WEATHER_AGENT_PATH.exists()

    print(f"  {Color.BRAND}{'═' * (width - 4)}{Color.RST}")
    print(f"  {Color.BRAND}{Color.BLD}  🤖 {AGENT_NAME}{Color.RST}  {Color.DIM}v{VERSION}{Color.RST}")
    print(f"  {Color.DIM}  Model: {MODEL}  |  Tools: {len(tools)} schedulers available{Color.RST}")
    print(f"  {Color.BRAND}{'═' * (width - 4)}{Color.RST}")
    print()

    # Agent 列表
    items = [
        f"{Color.BRAND}◆{Color.RST} {Color.BLD}{'KillerWhale':<20}{Color.RST} {Color.BGRN}✓{Color.RST if coding_exists else Color.RED}✗{Color.RST}  {Color.DIM}编程任务 — 代码/项目/Shell/搜索{Color.RST}",
        f"{Color.BRAND}◆{Color.RST} {Color.BLD}{'FishFarmer':<20}{Color.RST} {Color.BGRN}✓{Color.RST if sm_exists else Color.RED}✗{Color.RST}  {Color.DIM}技能管理 — 查看/创建/修改/删除/测试{Color.RST}",
        f"{Color.BRAND}◆{Color.RST} {Color.BLD}{'ModifyAgent':<20}{Color.RST} {Color.BGRN}✓{Color.RST if ma_exists else Color.RED}✗{Color.RST}  {Color.DIM}内容优化 — 7受众 × 10格式 × 5语言{Color.RST}",
        f"{Color.BRAND}◆{Color.RST} {Color.BLD}{'Dolphin':<20}{Color.RST} {Color.BGRN}✓{Color.RST if wa_exists else Color.RED}✗{Color.RST}  {Color.DIM}天气查询 — 预报/穿衣建议/life tips{Color.RST}",
    ]

    for item in items:
        print(f"  {item}")

    print()

    # 快捷键提示
    hints = [
        f"{Color.DIM}/help{Color.RST}  查看帮助",
        f"{Color.DIM}/exit{Color.RST}  退出",
        f"{Color.DIM}Ctrl+C{Color.RST}  中断当前任务",
    ]
    print(f"  {'  |  '.join(hints)}")

    print(f"  {Color.BRAND}{sep * (width - 4)}{Color.RST}")
    print()


def run_agent():
    """运行 FishPool 主循环（Claude Code 风格美化版）

    Ctrl+C 行为：
    - 在提示符处按下 Ctrl+C → 退出程序
    - 在任务执行中按下 Ctrl+C → 终止当前任务 → 回到提示符
    """

    messages = [{"role": "system", "content": build_system_prompt()}]

    # ═══════════════════════════════════════════════════════════════
    # Claude Code 风格启动界面
    # ═══════════════════════════════════════════════════════════════
    print_startup_banner()
    print_agent_catalog()

    round_num = 0

    # ═══════════════════════════════════════════════════════════════
    # 对话主循环
    # ═══════════════════════════════════════════════════════════════
    while True:
        try:
            # ── Claude Code 风格用户输入提示 ──
            prompt = build_prompt_with_label("You")
            user_input = chinese_input(prompt, multiline=True)

        except ExitRequested:
            # ── 场景 1：在提示符处按下 Ctrl+C → 退出程序 ──
            print()
            _print_goodbye_banner()
            break

        if not user_input:
            continue

        # ── 退出命令 ──
        if user_input.lower() in {"exit", "quit", "/exit", "/quit"} or user_input in {"再见", "退出"}:
            _print_goodbye_banner()
            break

        # ── 帮助命令 ──
        if user_input.lower() in {"/help", "help", "-h", "--help"}:
            print_help([
                ("/help", "显示此帮助信息"),
                ("/exit", "退出程序"),
                ("/quit", "退出程序"),
                ("/clear", "清屏"),
                ("/status", "显示系统状态和可用 Agent"),
            ])
            continue

        # ── 清屏 ──
        if user_input.lower() in {"/clear", "clear"}:
            os.system('cls' if os.name == 'nt' else 'clear')
            print_startup_banner()
            continue

        # ── 状态命令 ──
        if user_input.lower() in {"/status", "status"}:
            _print_status()
            continue

        round_num += 1

        # ── 显示用户输入 ──
        print()
        print(f"  {Color.USER}{Color.BLD}┌─ 💬 You ─────────────────────────────────{Color.RST}")
        print(f"  {Color.USER}{Color.BLD}│{Color.RST} {Color.USER}{user_input}{Color.RST}")
        print(f"  {Color.USER}{Color.BLD}╰{'─' * (min(get_term_width() - 4, 60) - 2)}{Color.RST}")
        print()

        messages.append({"role": "user", "content": user_input})

        # ── 任务执行块：Agent 回复 + 工具调用 ──
        try:
            # ── Agent 思考/流式回复 ──
            ts = format_full_timestamp()
            print(f"  {Color.BRAND}┌─ 🤖 {AGENT_NAME} @ {ts}{Color.RST}")
            print(f"  {Color.BRAND}│{Color.RST} ", end="", flush=True)

            assistant_msg = stream_chat_with_tools(messages)

            print()
            print(f"  {Color.BRAND}╰{'─' * min(get_term_width() - 4, 60)}{Color.RST}")
            print()

            messages.append(assistant_msg)

            # ── 工具调用循环 ──
            while assistant_msg.get("tool_calls"):
                tool_calls = assistant_msg["tool_calls"]

                for tc in tool_calls:
                    tool_name = tc["function"]["name"]
                    tool_args = json.loads(tc["function"]["arguments"])

                    # ── 显示工具调用（Claude Code 紧凑风格） ──
                    args_preview = json.dumps(tool_args, ensure_ascii=False)
                    print(f"  {Color.BRAND}┄ {tool_name}{Color.RST}  {Color.DIM}{truncate_text(args_preview, 60)}{Color.RST}")
                    print()

                    # 调用工具（此时子 Agent 的流式输出会实时打印到终端）
                    if tool_name in tool_functions:
                        try:
                            result = tool_functions[tool_name](**tool_args)
                        except TypeError as e:
                            result = f"❌ 参数错误: {e}"
                        except Exception as e:
                            result = f"❌ 执行出错: {e}"
                    else:
                        result = f"Unknown tool: {tool_name}"

                    # ── 显示工具结果 ──
                    print()
                    print(f"  {Color.BRAND}┌─ 📦 {tool_name} Result{Color.RST}")
                    # 截断过长的结果
                    result_lines = result.split("\n")
                    MAX_DISPLAY = 15
                    if len(result_lines) > MAX_DISPLAY:
                        display_result = "\n".join(result_lines[:MAX_DISPLAY])
                        print(f"  {Color.BRAND}│{Color.RST} {display_result}")
                        print(f"  {Color.BRAND}│{Color.RST} {Color.DIM}... (共 {len(result_lines)} 行，已截断){Color.RST}")
                    else:
                        print(f"  {Color.BRAND}│{Color.RST} {result}")
                    print(f"  {Color.BRAND}╰{'─' * min(get_term_width() - 4, 40)}{Color.RST}")
                    print()

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })

                # ── Agent 再次回复 ──
                ts = format_full_timestamp()
                print(f"  {Color.BRAND}┌─ 🤖 {AGENT_NAME} @ {ts}{Color.RST}")
                print(f"  {Color.BRAND}│{Color.RST} ", end="", flush=True)

                assistant_msg = stream_chat_with_tools(messages)

                print()
                print(f"  {Color.BRAND}╰{'─' * min(get_term_width() - 4, 60)}{Color.RST}")
                print()

                messages.append(assistant_msg)

        except KeyboardInterrupt:
            # ── 场景 2：在任务执行中按下 Ctrl+C → 中断当前任务 ──
            print()
            _print_interrupt_banner()
            # 清理 messages：移除最后一个未完成的 assistant 消息
            if messages and messages[-1].get("role") == "assistant":
                last = messages[-1]
                if last.get("tool_calls"):
                    messages.pop()
            continue

        # ── 轮次分隔线 ──
        print_claude_separator()


def _print_goodbye_banner():
    """打印告别横幅"""
    width = min(get_term_width() - 4, 60)
    width = max(width, 40)
    sep = "═"

    print()
    print(f"  {Color.BRAND}{sep * (width - 4)}{Color.RST}")
    print(f"  {Color.BRAND}{Color.BLD}  👋 感谢使用 FishPool，期待再次相见！{Color.RST}")
    print(f"  {Color.DIM}  {format_full_timestamp()}{Color.RST}")
    print(f"  {Color.BRAND}{sep * (width - 4)}{Color.RST}")
    print()


def _print_interrupt_banner():
    """打印中断提示横幅"""
    width = min(get_term_width() - 4, 60)
    width = max(width, 40)

    print()
    print(f"  {Color.YEL}{'─' * (width - 4)}{Color.RST}")
    print(f"  {Color.YEL}{Color.BLD}  ⚠️  当前任务已被用户中断{Color.RST}")
    print(f"  {Color.DIM}  已回到提示符，请输入新的需求继续...{Color.RST}")
    print(f"  {Color.YEL}{'─' * (width - 4)}{Color.RST}")
    print()


def _print_status():
    """打印 FishPool 系统状态和可用 Agent"""
    width = min(get_term_width() - 2, 80)
    width = max(width, 50)

    lines = []

    # ── Agent 状态 ──
    lines.append(f"  {Color.BLD}{Color.BRAND}🤖 FishPool 状态{Color.RST}")
    lines.append(f"  {Color.BRAND}│{Color.RST} {Color.BLD}模型:{Color.RST}     {Color.PRIMARY_BRIGHT}{MODEL}{Color.RST}")
    lines.append(f"  {Color.BRAND}│{Color.RST} {Color.BLD}版本:{Color.RST}     {Color.PRIMARY_BRIGHT}v{VERSION}{Color.RST}")
    lines.append(f"  {Color.BRAND}│{Color.RST} {Color.BLD}调度工具:{Color.RST}  {Color.BGRN}{len(tools)} 个{Color.RST}")
    lines.append(f"  {Color.BRAND}│{Color.RST} {Color.BLD}项目路径:{Color.RST} {Color.DIM}{PROJECT_ROOT}{Color.RST}")
    lines.append("")

    # ── 子 Agent 可用性 ──
    coding_avail = f"{Color.BGRN}✅ 可用{Color.RST}" if CODING_AGENT_PATH.exists() else f"{Color.RED}❌ 不存在{Color.RST}"
    sm_avail = f"{Color.BGRN}✅ 可用{Color.RST}" if SKILLS_MANAGER_PATH.exists() else f"{Color.RED}❌ 不存在{Color.RST}"
    ma_avail = f"{Color.BGRN}✅ 可用{Color.RST}" if MODIFY_AGENT_PATH.exists() else f"{Color.RED}❌ 不存在{Color.RST}"
    wa_avail = f"{Color.BGRN}✅ 可用{Color.RST}" if WEATHER_AGENT_PATH.exists() else f"{Color.RED}❌ 不存在{Color.RST}"

    lines.append(f"  {Color.BLD}{Color.BRAND}🤖 可调度的子 Agent{Color.RST}")
    lines.append(f"  {Color.BRAND}◆{Color.RST} {Color.BLD}KillerWhale:{Color.RST}    {coding_avail}  — 编程/代码/项目/Shell/搜索")
    lines.append(f"  {Color.BRAND}◆{Color.RST} {Color.BLD}FishFarmer:{Color.RST}    {sm_avail}  — 技能查看/创建/修改/删除/测试")
    lines.append(f"  {Color.BRAND}◆{Color.RST} {Color.BLD}ModifyAgent:{Color.RST}     {ma_avail}  — 内容优化/改写/翻译/格式转换")
    lines.append(f"  {Color.BRAND}◆{Color.RST} {Color.BLD}Dolphin:{Color.RST}       {wa_avail}  — 天气查询/预报/穿衣建议/life tips")
    lines.append("")

    # ── 调度工具列表 ──
    lines.append(f"  {Color.BLD}{Color.BRAND}⚡ 可用调度工具{Color.RST}")
    for t in tools:
        name = t["function"]["name"]
        desc_full = t["function"]["description"]
        desc = desc_full.split("】")[0].replace("【", "")
        lines.append(f"  {Color.BGRN}{name}{Color.RST}  — {Color.DIM}{desc}{Color.RST}")
    lines.append("")

    content = "\n".join(lines)
    print_panel(
        content=content,
        title="📊 FishPool 状态",
        color=Color.SYS,
        width=width,
    )
    print()


# ═══════════════════════════════════════════════════════════════════════
# 5. 程序入口
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    run_agent()
