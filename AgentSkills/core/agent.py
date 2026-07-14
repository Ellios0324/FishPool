"""
Agent 主循环模块

提供 KillerWhale 的主循环逻辑，包括：
- 系统提示词管理
- 用户输入处理
- 工具调用循环
- 退出逻辑
"""

import json

from ..skills import (
    # 文件操作
    read_file,
    write_file,
    delete_file,
    delete_directory,
    list_directory,
    create_directory,
    # Shell
    run_shell_command,
    # 语法检查
    check_python_syntax,
    check_yaml_syntax,
    check_html_syntax,
    check_css_syntax,
    check_js_syntax,
    # 联网搜索
    web_search,
    web_search_and_open,
    smart_search,
    search_news,
    aggregate_search,
    search_images,
    search_suggestions,
    search_engine_status,
    # Git 操作
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
    # Excel 生成
    create_xlsx,
    convert_md_table_to_xlsx,
    # PDF 生成
    create_pdf,
    PDFGenerator,
    # Markdown 输出
    write_markdown,
    generate_markdown_table,
    generate_markdown_code_block,
    generate_markdown_task_list,
    # Markdown 转 DOCX
    convert_md_to_docx,
    convert_md_content_to_docx,
    # Weather Agent
    run_weather_agent,
    # Modify Agent
    run_modify_agent,
    # C 项目
    create_c_project,
    debug_c_project,
    add_c_module,
    # C++ 项目
    create_cpp_project,
    debug_cpp_project,
    add_cpp_module,
    # C# 项目
    create_csharp_project,
    debug_csharp_project,
    add_csharp_module,
    # ── 语雀知识库 ──
    yuque_list_repos,
    yuque_get_toc,
    yuque_list_docs,
    yuque_get_doc_content,
    yuque_search_docs,
    yuque_ask,
    # ── 腾讯IMA知识库 ──
    tencent_kb_init,
    tencent_kb_list_databases,
    tencent_kb_search,
    tencent_kb_ask,
    tencent_kb_status,
    # ── 文件处理 ──
    identify_file,
    modify_docx,
    modify_pptx,
    modify_xlsx,
)
from .llm_client import LLMClient

# ── 工具函数映射 ──
TOOL_FUNCTIONS = {
    # 文件操作
    "read_file": read_file,
    "write_file": write_file,
    "delete_file": delete_file,
    "delete_directory": delete_directory,
    "list_directory": list_directory,
    "create_directory": create_directory,
    # Shell
    "run_shell_command": run_shell_command,
    # 语法检查
    "check_python_syntax": check_python_syntax,
    "check_yaml_syntax": check_yaml_syntax,
    "check_html_syntax": check_html_syntax,
    "check_css_syntax": check_css_syntax,
    "check_js_syntax": check_js_syntax,
    # 联网搜索
    "web_search": web_search,
    "web_search_and_open": web_search_and_open,
    "smart_search": smart_search,
    "search_news": search_news,
    "aggregate_search": aggregate_search,
    "search_images": search_images,
    "search_suggestions": search_suggestions,
    "search_engine_status": search_engine_status,
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
    # Excel 生成
    "create_xlsx": create_xlsx,
    "convert_md_table_to_xlsx": convert_md_table_to_xlsx,
    # PDF 生成
    "create_pdf": create_pdf,
    "PDFGenerator": PDFGenerator,
    # Markdown 输出
    "write_markdown": write_markdown,
    "generate_markdown_table": generate_markdown_table,
    "generate_markdown_code_block": generate_markdown_code_block,
    "generate_markdown_task_list": generate_markdown_task_list,
    # Markdown 转 DOCX
    "convert_md_to_docx": convert_md_to_docx,
    "convert_md_content_to_docx": convert_md_content_to_docx,
    # Weather Agent
    "run_weather_agent": run_weather_agent,
    # Modify Agent
    "run_modify_agent": run_modify_agent,
    # C 项目
    "create_c_project": create_c_project,
    "debug_c_project": debug_c_project,
    "add_c_module": add_c_module,
    # C++ 项目
    "create_cpp_project": create_cpp_project,
    "debug_cpp_project": debug_cpp_project,
    "add_cpp_module": add_cpp_module,
    # C# 项目
    "create_csharp_project": create_csharp_project,
    "debug_csharp_project": debug_csharp_project,
    "add_csharp_module": add_csharp_module,
    # ── 语雀知识库 ──
    "yuque_list_repos": yuque_list_repos,
    "yuque_get_toc": yuque_get_toc,
    "yuque_list_docs": yuque_list_docs,
    "yuque_get_doc_content": yuque_get_doc_content,
    "yuque_search_docs": yuque_search_docs,
    "yuque_ask": yuque_ask,
    # ── 腾讯IMA知识库 ──
    "tencent_kb_init": tencent_kb_init,
    "tencent_kb_list_databases": tencent_kb_list_databases,
    "tencent_kb_search": tencent_kb_search,
    "tencent_kb_ask": tencent_kb_ask,
    "tencent_kb_status": tencent_kb_status,
    # ── 文件处理 ──
    "identify_file": identify_file,
    "modify_docx": modify_docx,
    "modify_pptx": modify_pptx,
    "modify_xlsx": modify_xlsx,
}

# ── 工具定义（JSON Schema）──
TOOLS_SCHEMA = [
    # ═══════════ 文件操作 ═══════════
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
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "将内容写入指定文件（自动创建父目录）。支持 HTML、CSS、JS、Python 等多种文件。",
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
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "删除指定文件。用于清理项目中的文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "要删除的文件路径"}
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_directory",
            "description": "删除目录。recursive=True 可递归删除非空目录（谨慎使用）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dir_path": {"type": "string", "description": "要删除的目录路径"},
                    "recursive": {
                        "type": "boolean",
                        "description": "是否递归删除（如果目录非空，需要设为 true）",
                    },
                },
                "required": ["dir_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "列出指定目录下的文件和子目录（显示文件名和大小）。支持通配符过滤，如 *.html 只显示 HTML 文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dir_path": {
                        "type": "string",
                        "description": "目录路径（默认当前目录）",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "文件名过滤模式，如 '*.html', '*.css', '*.js'",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "创建目录（可递归创建多级目录）。用于搭建项目结构。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dir_path": {"type": "string", "description": "要创建的目录路径"}
                },
                "required": ["dir_path"],
            },
        },
    },
    # ═══════════ Shell ═══════════
    {
        "type": "function",
        "function": {
            "name": "run_shell_command",
            "description": "执行 Shell 命令（可用于运行 Go、Python、Node.js 等脚本，也可用于安装 npm 包、启动构建工具等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的 Shell 命令",
                    }
                },
                "required": ["command"],
            },
        },
    },
    # ═══════════ 语法检查 ═══════════
    {
        "type": "function",
        "function": {
            "name": "check_python_syntax",
            "description": "检查 Python 文件的语法是否正确",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Python 文件路径",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_yaml_syntax",
            "description": "检查 YAML 文件的语法是否正确",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "YAML 文件路径",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_html_syntax",
            "description": "检查 HTML 文件的语法是否正确（标签闭合、嵌套、DOCTYPE、charset 等）。优先使用 HTML Tidy 工具，更准确全面。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "HTML 文件路径",
                    },
                    "use_tidy": {
                        "type": "boolean",
                        "description": "是否使用 HTML Tidy（更准确，默认 true）",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_css_syntax",
            "description": "检查 CSS 文件的语法是否正确（花括号匹配、属性声明格式、@规则等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "CSS 文件路径",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_js_syntax",
            "description": "检查 JavaScript 文件的语法是否正确。使用 Node.js --check 进行准确校验。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "JavaScript 文件路径",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    # ═══════════ 联网搜索 ═══════════
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "🔍 通过 Bing 搜索互联网（原始接口）。返回标题、链接和摘要列表。完全免费，无需 API Key。内置缓存机制，60秒内重复搜索相同关键词直接返回缓存结果。适合查询最新资讯、技术文档、API 用法等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词（支持中文）",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数量（1~20，默认5）",
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "是否使用缓存（默认 true，60秒内重复搜索相同关键词直接返回缓存结果）",
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
            "description": "📄 搜索并打开网页（原始接口）。搜索互联网并自动获取第一条结果的页面正文内容。适合需要深入阅读某个网页内容来回答问题的场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
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
    {
        "type": "function",
        "function": {
            "name": "smart_search",
            "description": "🔬 智能搜索 — 支持多引擎切换、时间筛选、语言选择。可在 Bing、DuckDuckGo、Bing News 三个引擎间切换，支持按时间范围过滤（24h/7d/30d/1y），支持多语言搜索。适合需要灵活切换搜索引擎或按时间筛选的场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词（支持中文）",
                    },
                    "engine": {
                        "type": "string",
                        "description": "搜索引擎：'bing'（默认，稳定可靠）、'duckduckgo'（注重隐私）、'bing_news'（新闻搜索）",
                        "enum": ["bing", "duckduckgo", "bing_news"],
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数量（1~20，默认5）",
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "是否使用缓存（默认 true）",
                    },
                    "time_range": {
                        "type": "string",
                        "description": "时间范围过滤：None（不过滤）、'24h'（过去24小时）、'7d'（过去7天）、'30d'（过去30天）、'1y'（过去1年）",
                        "enum": ["24h", "7d", "30d", "1y"],
                    },
                    "language": {
                        "type": "string",
                        "description": "搜索语言：'zh'（中文，默认）、'en'（英文）、'ja'（日文）等",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "📰 新闻搜索 — 专门针对时事政治新闻，支持中英文双语。自动从 Bing News 获取最新新闻，支持按时间范围筛选（24h/7d/30d/1y），支持中英文双语同时搜索并合并去重。适合搜索热点事件、时事政治等时效性强的信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "新闻搜索关键词（如'中美关系 最新'）",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数量（1~30，默认10）",
                    },
                    "language": {
                        "type": "string",
                        "description": "新闻语言：'zh'（中文，默认）、'en'（英文）、'ja'（日文）等",
                    },
                    "time_period": {
                        "type": "string",
                        "description": "时间范围：'24h'（过去24小时）、'7d'（过去7天，默认）、'30d'（过去30天）、'1y'（过去1年）",
                        "enum": ["24h", "7d", "30d", "1y"],
                    },
                    "bilingual": {
                        "type": "boolean",
                        "description": "是否启用中英文双语搜索（默认 false）。启用后会同时搜索中英文新闻并合并去重",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "aggregate_search",
            "description": "🔗 聚合搜索 — 多引擎同时搜索，结果去重后按相关性/时间排序。默认同时搜索 Bing 和 DuckDuckGo，合并结果后去重并按指定方式排序，获取最全面的信息。适合需要全面覆盖、不遗漏关键信息的场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                    "engines": {
                        "type": "array",
                        "description": "搜索引擎列表，默认 ['bing', 'duckduckgo']。可选值：'bing', 'duckduckgo', 'bing_news'",
                        "items": {
                            "type": "string",
                            "enum": ["bing", "duckduckgo", "bing_news"],
                        },
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数量（1~30，默认10）",
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "排序方式：'relevance'（按相关性，默认）、'time'（按时间）",
                        "enum": ["relevance", "time"],
                    },
                    "language": {
                        "type": "string",
                        "description": "搜索语言：'zh'（中文，默认）、'en'（英文）等",
                    },
                    "time_range": {
                        "type": "string",
                        "description": "时间范围过滤：None（不过滤）、'24h'、'7d'、'30d'、'1y'",
                        "enum": ["24h", "7d", "30d", "1y"],
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_images",
            "description": "🖼️ 图片搜索 — 通过 Bing Images 搜索图片，返回图片标题、链接和缩略图地址。适合搜索图片素材、产品截图等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数量（1~20，默认10）",
                    },
                    "language": {
                        "type": "string",
                        "description": "搜索语言：'zh'（中文，默认）、'en'（英文）等",
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "是否使用缓存（默认 true）",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_suggestions",
            "description": "💡 相关搜索建议 — 从搜索结果页面提取相关搜索词/建议。帮助用户发现更多搜索关键词和扩展搜索方向。适合在搜索前后获取相关主题扩展。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                    "engine": {
                        "type": "string",
                        "description": "搜索引擎：'bing'（默认）、'google'、'duckduckgo'",
                        "enum": ["bing", "google", "duckduckgo"],
                    },
                    "language": {
                        "type": "string",
                        "description": "搜索语言：'zh'（中文，默认）、'en'（英文）等",
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "是否使用缓存（默认 true）",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_engine_status",
            "description": "⚡ 搜索引擎健康检查 — 检测 Google、Bing、DuckDuckGo、Bing News、百度等搜索引擎的可用性状态。返回各引擎是否正常工作及响应时间。适合在搜索前诊断网络环境。",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_query": {
                        "type": "string",
                        "description": "用于测试的搜索词（默认 'test'）",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "每个引擎的超时时间（秒，默认5）",
                    },
                },
                "required": [],
            },
        },
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
    # ═══════════ Excel 生成 ═══════════
    {
        "type": "function",
        "function": {
            "name": "create_xlsx",
            "description": "创建格式美观的 Excel 文件。支持多工作表（传入 dict 即可）、表头样式（加粗居中）、斑马纹、单元格边框、自动列宽、自定义样式（styles 参数）。自动安装 openpyxl（如未安装）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "description": "数据内容。三种格式：(1) list[list] — 单工作表，第一行为表头；(2) dict[str, list[list]] — 多工作表，key 为 sheet 名；(3) list[dict] — 多工作表，每个 dict 包含 sheet_name/data/title 等",
                        "oneOf": [
                            {
                                "type": "array",
                                "description": "单工作表：二维列表，第一行为表头。如 [['姓名','年龄'], ['张三',28]]",
                                "items": {
                                    "type": "array",
                                    "items": {}
                                }
                            },
                            {
                                "type": "object",
                                "description": "多工作表：{sheet名: 数据二维列表}。如 {'员工表': [['姓名','年龄'], ['张三',28]], '薪资表': [...]}",
                                "additionalProperties": {
                                    "type": "array",
                                    "items": {
                                        "type": "array",
                                        "items": {}
                                    }
                                }
                            },
                            {
                                "type": "array",
                                "description": "多工作表（详细配置）：[{sheet_name, data, title, ...}]",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "sheet_name": {"type": "string"},
                                        "data": {
                                            "type": "array",
                                            "items": {
                                                "type": "array",
                                                "items": {}
                                            }
                                        },
                                        "title": {"type": "string"}
                                    }
                                }
                            }
                        ]
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出文件路径，需以 .xlsx 结尾"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "单工作表模式下的 sheet 名称，默认 'Sheet1'"
                    },
                    "title": {
                        "type": "string",
                        "description": "可选标题行（仅在单工作表模式下有效），在表格上方添加一行居中加粗标题"
                    },
                    "auto_install": {
                        "type": "boolean",
                        "description": "是否自动安装 openpyxl（若未安装），默认 true"
                    },
                    "styles": {
                        "type": "object",
                        "description": "全局样式配置（可选）：header_font/header_fill/header_alignment/data_font/data_alignment/even_fill/odd_fill/border/title_font/title_alignment",
                        "properties": {
                            "header_font": {"description": "表头字体（Font 对象）"},
                            "header_fill": {"description": "表头背景色（PatternFill 对象）"},
                            "header_alignment": {"description": "表头对齐（Alignment 对象）"},
                            "data_font": {"description": "数据字体（Font 对象）"},
                            "data_alignment": {"description": "数据对齐（Alignment 对象）"},
                            "even_fill": {"description": "偶数行背景（PatternFill 对象）"},
                            "odd_fill": {"description": "奇数行背景（PatternFill 对象）"},
                            "border": {"description": "单元格边框（Border 对象）"},
                            "title_font": {"description": "标题字体（Font 对象）"},
                            "title_alignment": {"description": "标题对齐（Alignment 对象）"}
                        }
                    }
                },
                "required": ["data", "output_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "convert_md_table_to_xlsx",
            "description": "将 Markdown 格式的表格文本转换为 .xlsx 文件。自动解析 Markdown 表格语法，提取表头和数据行，并应用与 create_xlsx 相同的格式化样式（表头加粗、斑马纹、边框、自动列宽）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "md_table_content": {
                        "type": "string",
                        "description": "Markdown 格式的表格内容字符串，格式如：'| 标题1 | 标题2 |\\n| --- | --- |\\n| 数据1 | 数据2 |'"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出文件路径，需以 .xlsx 结尾"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "工作表名称，默认为 'Sheet1'"
                    },
                    "auto_install": {
                        "type": "boolean",
                        "description": "是否自动安装 openpyxl（若未安装），默认 true"
                    }
                },
                "required": ["md_table_content", "output_path"]
            }
        }
    },
    # ═══════════ PDF 生成 ═══════════
    {
        "type": "function",
        "function": {
            "name": "create_pdf",
            "description": "从文本内容快速创建 PDF 文件（简易接口）。支持 Markdown 风格格式解析（标题#、列表-、代码块```、表格|等），自动排版生成美观的 PDF 文档。支持中文。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "文本内容（支持 Markdown 风格标记：标题#、列表-、代码块```、表格|、分隔线---等）"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出 PDF 文件路径"
                    },
                    "title": {
                        "type": "string",
                        "description": "文档标题（元数据，默认'文档'）"
                    },
                    "author": {
                        "type": "string",
                        "description": "作者（元数据，默认'KillerWhale'）"
                    }
                },
                "required": ["content", "output_path"]
            }
        }
    },
    # ═══════════ Markdown 输出 ═══════════
    {
        "type": "function",
        "function": {
            "name": "write_markdown",
            "description": "将 Markdown 内容写入文件。自动创建父目录、自动添加 .md 后缀、自动添加文档头部元信息（标题、作者、生成时间）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Markdown 格式的文本内容"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出文件路径（会自动补全 .md 后缀）"
                    },
                    "title": {
                        "type": "string",
                        "description": "文档标题（可选，会作为一级标题写入文件头部）"
                    },
                    "author": {
                        "type": "string",
                        "description": "作者名（可选，会写入文件头部元信息）"
                    }
                },
                "required": ["content", "output_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_markdown_table",
            "description": "生成 GFM 格式的 Markdown 表格。传入表头和数据行，返回格式化的 Markdown 表格字符串。",
            "parameters": {
                "type": "object",
                "properties": {
                    "headers": {
                        "type": "array",
                        "description": "表头列表，如 ['名称', '数值', '备注']",
                        "items": {"type": "string"}
                    },
                    "rows": {
                        "type": "array",
                        "description": "数据行列表，每行是一个列表，如 [['苹果', '5', '水果'], ['香蕉', '3', '水果']]",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                },
                "required": ["headers", "rows"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_markdown_code_block",
            "description": "生成围栏代码块（GFM 风格）。传入代码内容和语言名称，返回格式化的 Markdown 代码块字符串。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "代码内容"
                    },
                    "language": {
                        "type": "string",
                        "description": "编程语言名称（如 python, javascript, go, html 等），为空则不指定语言"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_markdown_task_list",
            "description": "生成 GFM 任务列表（可勾选清单）。传入任务项列表，每个任务项为 (描述, 是否已完成) 元组，返回格式化的 Markdown 任务列表字符串。",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "任务列表，每个元素是 [任务描述, 是否已完成] 的数组，例如 [['买菜', true], ['做饭', false]]",
                        "items": {
                            "type": "array",
                            "items": {},
                            "minItems": 2,
                            "maxItems": 2
                        }
                    }
                },
                "required": ["items"]
            }
        }
    },
    # ═══════════ Markdown 转 DOCX ═══════════
    {
        "type": "function",
        "function": {
            "name": "convert_md_to_docx",
            "description": "将 Markdown 文件转换为 Word (.docx) 文档。自动安装所需依赖（markdown, python-docx, beautifulsoup4），支持标题、段落、粗体/斜体、代码块、列表、表格、图片、链接等元素。",
            "parameters": {
                "type": "object",
                "properties": {
                    "md_file_path": {
                        "type": "string",
                        "description": "Markdown 文件路径"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出文件路径（默认与输入文件同名，扩展名为 .docx）"
                    },
                    "title": {
                        "type": "string",
                        "description": "文档标题（可选）"
                    },
                    "author": {
                        "type": "string",
                        "description": "作者名（可选）"
                    }
                },
                "required": ["md_file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "convert_md_content_to_docx",
            "description": "将 Markdown 文本内容直接转换为 Word (.docx) 文件（无需中间文件）。支持标题、段落、粗体/斜体、代码块、列表、表格、图片、链接等元素。",
            "parameters": {
                "type": "object",
                "properties": {
                    "md_content": {
                        "type": "string",
                        "description": "Markdown 格式的文本内容"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出文件路径（自动补全 .docx 后缀）"
                    },
                    "title": {
                        "type": "string",
                        "description": "文档标题（可选）"
                    },
                    "author": {
                        "type": "string",
                        "description": "作者名（可选）"
                    }
                },
                "required": ["md_content", "output_path"]
            }
        }
    },
    # ═══════════ Weather Agent ═══════════
    {
        "type": "function",
        "function": {
            "name": "run_weather_agent",
            "description": "🌤️ Dolphin — 天气查询助手。接收包含城市名称的任务描述，通过联网搜索获取天气信息，返回格式化的天气报告（包含温度、状况、湿度、风力、生活小提示等）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "任务描述，例如：'查询北京的天气'、'上海天气预报'、'Tokyo 天气怎么样'、'帮我查查纽约未来几天的气温'"
                    }
                },
                "required": ["task"]
            }
        }
    },
    # ═══════════ Modify Agent ═══════════
    {
        "type": "function",
        "function": {
            "name": "run_modify_agent",
            "description": "✏️ ModifyAgent — 内容优化助手。接收任务描述，分析目标受众和格式要求，返回优化后的内容。支持受众适配（developer/manager/executive/beginner/customer/non_technical）、格式转换（Markdown转纯文本）、文本简化、技术术语管理等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "任务描述，包含原始内容和目标受众/格式要求，例如：'把这段内容改写成面向初学者的版本：...内容...'、'面向高管总结：...报告内容...'、'把这篇技术文档转成纯文本'"
                    }
                },
                "required": ["task"]
            }
        }
    },
    # ═══════════ C 项目 ═══════════
    {
        "type": "function",
        "function": {
            "name": "create_c_project",
            "description": "创建标准 C 语言项目结构。支持 console(控制台)、library(库)、sdl(SDL图形) 三种类型。自动生成 src/main.c、include/、Makefile、.gitignore、README.md。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "项目名称（也是根目录名）"
                    },
                    "project_type": {
                        "type": "string",
                        "description": "项目类型：'console'(控制台,默认), 'library'(库), 'sdl'(SDL图形)",
                        "enum": ["console", "library", "sdl"]
                    }
                },
                "required": ["project_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "debug_c_project",
            "description": "调试 C 项目。检查 Makefile、检测 gcc 编译器、尝试编译 (make/gcc)、分析编译错误并给出修复建议。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "项目根目录路径"
                    }
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_c_module",
            "description": "在 C 项目中添加新模块。自动创建对应的 .c 和 .h 文件，包括头文件保护、初始化/清理函数框架，并更新 Makefile。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "项目根目录路径"
                    },
                    "module_name": {
                        "type": "string",
                        "description": "模块名称（将创建 module_name.c 和 module_name.h）"
                    }
                },
                "required": ["project_path", "module_name"]
            }
        }
    },
    # ═══════════ C++ 项目 ═══════════
    {
        "type": "function",
        "function": {
            "name": "create_cpp_project",
            "description": "创建标准 C++ 项目结构。支持 console(控制台)、library(库)、sdl(SDL图形)、qt(Qt框架) 四种类型。C++17 标准，自动生成 src/main.cpp、include/、Makefile、.gitignore、README.md。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "项目名称（也是根目录名）"
                    },
                    "project_type": {
                        "type": "string",
                        "description": "项目类型：'console'(控制台,默认), 'library'(库), 'sdl'(SDL图形), 'qt'(Qt框架)",
                        "enum": ["console", "library", "sdl", "qt"]
                    }
                },
                "required": ["project_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "debug_cpp_project",
            "description": "调试 C++ 项目。检查 Makefile、检测 g++ 编译器及 C++17 支持、尝试编译、分析编译错误并给出修复建议（模板/继承/覆盖等 C++ 特有错误）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "项目根目录路径"
                    }
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_cpp_module",
            "description": "在 C++ 项目中添加新模块。自动创建 .hpp 和 .cpp 文件，生成完整的 C++ 类框架（构造函数、析构函数、拷贝/移动禁用、init/name/printInfo 方法）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "项目根目录路径"
                    },
                    "module_name": {
                        "type": "string",
                        "description": "模块名称（将创建 PascalCase 类名，文件名为 module_name.hpp 和 module_name.cpp）"
                    }
                },
                "required": ["project_path", "module_name"]
            }
        }
    },
    # ═══════════ C# 项目 ═══════════
    {
        "type": "function",
        "function": {
            "name": "create_csharp_project",
            "description": "创建标准 C# 项目结构。优先使用 dotnet CLI 创建，不可用时手动创建 .csproj 和源代码。支持 console(控制台)、library(类库)、winforms(Windows窗体)、webapi(Web API)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "项目名称（也是根目录名）"
                    },
                    "project_type": {
                        "type": "string",
                        "description": "项目类型：'console'(控制台,默认), 'library'(类库), 'winforms'(Windows窗体), 'webapi'(Web API)",
                        "enum": ["console", "library", "winforms", "webapi"]
                    }
                },
                "required": ["project_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "debug_csharp_project",
            "description": "调试 C# 项目。检测 dotnet CLI 和 SDK 版本、检查 .csproj 和源代码结构、运行 dotnet build、分析编译错误（CS 错误码）并给出修复建议。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "项目根目录路径"
                    }
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_csharp_module",
            "description": "在 C# 项目中添加新模块。自动创建 .cs 类文件，自动检测命名空间（从 .csproj 读取 RootNamespace），生成完整的 C# 类框架（构造函数、属性、方法）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "项目根目录路径"
                    },
                    "module_name": {
                        "type": "string",
                        "description": "类/模块名称（将创建 PascalCase 类名 .cs 文件）"
                    }
                },
                "required": ["project_path", "module_name"]
            }
        }
    },
    # ═══════════ 语雀知识库 ═══════════
    {
        "type": "function",
        "function": {
            "name": "yuque_list_repos",
            "description": "📚 列出语雀知识库列表。获取指定用户（或 Token 对应用户）的所有知识库。需要 YUQUE_TOKEN。",
            "parameters": {
                "type": "object",
                "properties": {
                    "token_str": {"type": "string", "description": "语雀 API Token（必填，需在 .env 配置 YUQUE_TOKEN）"},
                    "user_login": {"type": "string", "description": "用户名（可选，默认使用 Token 对应用户）"}
                },
                "required": ["token_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "yuque_get_toc",
            "description": "📂 获取语雀知识库目录结构。展示层级目录结构，包含文档标题、层级和 ID。",
            "parameters": {
                "type": "object",
                "properties": {
                    "token_str": {"type": "string", "description": "语雀 API Token"},
                    "repo_id": {"description": "知识库 ID（数字或字符串）"}
                },
                "required": ["token_str", "repo_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "yuque_list_docs",
            "description": "📄 列出知识库中所有文档。返回文档标题、更新时间等信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "token_str": {"type": "string", "description": "语雀 API Token"},
                    "repo_id": {"description": "知识库 ID"}
                },
                "required": ["token_str", "repo_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "yuque_get_doc_content",
            "description": "📝 获取语雀文档的完整 Markdown 内容。获取指定文档的原始 Markdown 内容，便于阅读或进一步处理。",
            "parameters": {
                "type": "object",
                "properties": {
                    "token_str": {"type": "string", "description": "语雀 API Token"},
                    "repo_id": {"description": "知识库 ID"},
                    "doc_id_or_slug": {"type": "string", "description": "文档 ID（数字）或 Slug（路径名）"}
                },
                "required": ["token_str", "repo_id", "doc_id_or_slug"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "yuque_search_docs",
            "description": "🔍 在语雀知识库中搜索文档。通过获取所有文档标题进行本地关键词匹配搜索。",
            "parameters": {
                "type": "object",
                "properties": {
                    "token_str": {"type": "string", "description": "语雀 API Token"},
                    "repo_id": {"description": "知识库 ID"},
                    "keyword": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["token_str", "repo_id", "keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "yuque_ask",
            "description": "🤔 基于语雀知识库内容回答问题。获取目录和文档列表，关键词匹配找到最相关的文档后获取内容回答用户。",
            "parameters": {
                "type": "object",
                "properties": {
                    "token_str": {"type": "string", "description": "语雀 API Token"},
                    "repo_id": {"description": "知识库 ID"},
                    "question": {"type": "string", "description": "用户的问题"}
                },
                "required": ["token_str", "repo_id", "question"]
            }
        }
    },
    # ═══════════ 腾讯IMA知识库 ═══════════
    {
        "type": "function",
        "function": {
            "name": "tencent_kb_init",
            "description": "🔧 初始化 IMA 知识库连接配置。从参数或环境变量中读取 API 网关地址和密钥。",
            "parameters": {
                "type": "object",
                "properties": {
                    "api_url": {"type": "string", "description": "API 网关地址（可选，默认从 .env 的 TENCENT_KB_API_URL 读取）"},
                    "api_key": {"type": "string", "description": "API 密钥（可选，默认从 .env 的 TENCENT_KB_API_KEY 读取）"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tencent_kb_list_databases",
            "description": "📦 列出 IMA 知识库中的数据库/集合列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "api_url": {"type": "string", "description": "API 网关地址（可选）"},
                    "api_key": {"type": "string", "description": "API 密钥（可选）"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tencent_kb_search",
            "description": "🔍 在 IMA 知识库中搜索相关内容。使用 API 网关进行向量或关键词搜索。",
            "parameters": {
                "type": "object",
                "properties": {
                    "api_url": {"type": "string", "description": "API 网关地址（可选）"},
                    "api_key": {"type": "string", "description": "API 密钥（可选）"},
                    "query": {"type": "string", "description": "搜索查询词"},
                    "top_k": {"type": "integer", "description": "返回结果数量（默认5，范围1-20）"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tencent_kb_ask",
            "description": "🤔 基于 IMA 知识库回答问题。先搜索相关内容，再回答用户问题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "api_url": {"type": "string", "description": "API 网关地址（可选）"},
                    "api_key": {"type": "string", "description": "API 密钥（可选）"},
                    "question": {"type": "string", "description": "用户问题"}
                },
                "required": ["question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tencent_kb_status",
            "description": "📊 检查 IMA 知识库连接状态和基本信息。检测 API 连接、认证状态和配置信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "api_url": {"type": "string", "description": "API 网关地址（可选）"},
                    "api_key": {"type": "string", "description": "API 密钥（可选）"}
                },
                "required": []
            }
        }
    },
    # ═══════════ 文件处理 ═══════════
    {
        "type": "function",
        "function": {
            "name": "identify_file",
            "description": "🔍 识别常见文件类型并提取基本信息。支持图片(jpg/png/gif/bmp/webp/tiff)、Word(.docx)、PowerPoint(.pptx)、Excel(.xlsx)、PDF、文本文件(txt/csv/md/json等)。返回格式化的文件信息（大小、格式、行数、页数等）。自动安装缺失依赖。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "待识别文件的路径"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modify_docx",
            "description": "✏️ 修改 Word (.docx) 文件。支持替换文本、添加段落、添加表格、修改标题。自动安装 python-docx。operations 为操作列表，支持类型：replace_text(替换文本)、add_paragraph(添加段落)、add_table(添加表格)、set_title(修改标题)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "源 .docx 文件路径"
                    },
                    "operations": {
                        "type": "array",
                        "description": "操作列表，每个元素为一个 dict。示例：[{\"type\": \"replace_text\", \"old\": \"原文本\", \"new\": \"新文本\"}, {\"type\": \"add_paragraph\", \"text\": \"段落内容\", \"style\": \"Normal\"}, {\"type\": \"add_table\", \"rows\": 3, \"cols\": 4, \"data\": [[\"a\",\"b\"],[\"c\",\"d\"]]}, {\"type\": \"set_title\", \"text\": \"新标题\"}]",
                        "items": {
                            "type": "object"
                        }
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出文件路径（默认覆盖原文件）"
                    }
                },
                "required": ["file_path", "operations"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modify_pptx",
            "description": "✏️ 修改 PowerPoint (.pptx) 文件。支持替换幻灯片文本、添加幻灯片、修改幻灯片标题。自动安装 python-pptx。operations 为操作列表，支持类型：replace_text(替换文本,可指定slide_index)、add_slide(添加幻灯片,含标题和内容列表)、set_slide_title(修改幻灯片标题)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "源 .pptx 文件路径"
                    },
                    "operations": {
                        "type": "array",
                        "description": "操作列表。示例：[{\"type\": \"replace_text\", \"old\": \"旧文本\", \"new\": \"新文本\", \"slide_index\": 0}, {\"type\": \"add_slide\", \"title\": \"标题\", \"content\": [\"要点1\", \"要点2\"]}, {\"type\": \"set_slide_title\", \"slide_index\": 0, \"text\": \"新标题\"}]",
                        "items": {
                            "type": "object"
                        }
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出文件路径（默认覆盖原文件）"
                    }
                },
                "required": ["file_path", "operations"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modify_xlsx",
            "description": "✏️ 修改 Excel (.xlsx) 文件。支持修改单元格、追加行、重命名工作表、删除行。自动安装 openpyxl。operations 为操作列表，支持类型：set_cell(修改单元格)、add_row(追加行)、set_sheet_name(重命名工作表)、delete_row(删除行)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "源 .xlsx 文件路径"
                    },
                    "operations": {
                        "type": "array",
                        "description": "操作列表。示例：[{\"type\": \"set_cell\", \"sheet\": \"Sheet1\", \"row\": 1, \"col\": 1, \"value\": \"新值\"}, {\"type\": \"add_row\", \"sheet\": \"Sheet1\", \"data\": [\"a\",\"b\",\"c\"]}, {\"type\": \"set_sheet_name\", \"sheet\": \"Sheet1\", \"new_name\": \"新名称\"}, {\"type\": \"delete_row\", \"sheet\": \"Sheet1\", \"row_index\": 2}]",
                        "items": {
                            "type": "object"
                        }
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出文件路径（默认覆盖原文件）"
                    }
                },
                "required": ["file_path", "operations"]
            }
        }
    },
]

# ── 系统提示词 ──
SYSTEM_PROMPT = """
你是一个专业的 KillerWhale，可以帮助用户编写、检查、修改和删除代码项目文件。

## 📁 文件操作
- read_file: 读取文件内容
- write_file: 写入/覆盖文件（自动创建目录）
- delete_file: 删除文件
- delete_directory: 删除目录（可递归）
- list_directory: 列出目录内容（支持通配符过滤）
- create_directory: 创建目录

## 🛠 Shell 执行
- run_shell_command: 执行 Shell 命令（可用于运行脚本、安装包、启动服务等）

## ✅ 语法检查
- check_python_syntax: 检查 Python 语法
- check_yaml_syntax: 检查 YAML 语法
- check_html_syntax: 检查 HTML 语法（标签、嵌套、DOCTYPE 等）
- check_css_syntax: 检查 CSS 语法（花括号、属性声明等）
- check_js_syntax: 检查 JavaScript 语法（使用 Node.js）

## 🌐 联网搜索（多引擎支持）
- web_search: 🔍 通过 Bing 搜索互联网（原始接口）
- web_search_and_open: 📄 搜索并打开网页（获取页面内容）
- smart_search: 🔬 智能搜索 — 支持多引擎切换（Bing/DuckDuckGo/Bing News）、时间筛选、语言选择
- search_news: 📰 新闻搜索 — 专门针对时事政治新闻，支持中英文双语同时搜索
- aggregate_search: 🔗 聚合搜索 — 多引擎同时搜索，结果去重后按相关性/时间排序
- search_images: 🖼️ 图片搜索 — 通过 Bing Images 搜索图片，返回标题、链接和缩略图地址
- search_suggestions: 💡 相关搜索建议 — 获取与当前关键词相关的搜索建议
- search_engine_status: ⚡ 搜索引擎健康检查 — 检测各搜索引擎可用性

## 📊 Excel 文件生成
- create_xlsx: 创建格式美观的 Excel 文件。支持多工作表、表头样式、斑马纹、边框、自动列宽、自定义样式。自动安装 openpyxl。
- convert_md_table_to_xlsx: 将 Markdown 表格文本转换为 .xlsx 文件

## 📄 PDF 生成
- create_pdf: 从文本内容快速创建 PDF 文件。支持 Markdown 风格格式解析，自动排版，支持中文。

## 📝 Markdown 输出
- write_markdown: 将 Markdown 内容写入文件（自动添加头部元信息）
- generate_markdown_table: 生成 GFM 格式的 Markdown 表格
- generate_markdown_code_block: 生成围栏代码块
- generate_markdown_task_list: 生成 GFM 任务列表（可勾选清单）

## 📄 Markdown 转 DOCX
- convert_md_to_docx: 将 Markdown 文件转换为 Word (.docx) 文档
- convert_md_content_to_docx: 将 Markdown 文本内容直接转换为 Word (.docx) 文件

## 🌤️ Dolphin（天气查询）
- run_weather_agent: 天气查询助手。输入城市名称，返回格式化的天气预报（温度、状况、湿度、风力、生活小提示等）。

## ✏️ ModifyAgent（内容优化）
- run_modify_agent: 内容优化助手。支持受众适配（developer/manager/executive/beginner/customer/non_technical）、Markdown 转纯文本、文本简化、技术术语管理等。

## Git 操作
- check_git_installed: 检查 Git 版本/安装状态
- git_init: 初始化 Git 仓库
- git_clone: 克隆远程仓库
- git_status: 查看工作区状态
- git_add: 添加文件到暂存区
- git_commit: 提交变更
- git_log: 查看提交历史
- git_diff: 查看文件差异
- git_branch: 分支管理（列出/创建/删除）
- git_checkout: 切换分支
- git_pull: 拉取远程更新
- git_push: 推送至远程仓库
- git_ignore: 管理 .gitignore 规则
- git_config: 查看/设置 Git 配置
- git_reset: 重置仓库状态
- git_tag: 标签管理（列出/创建/删除）

## 📚 知识库接入

### 🦜 语雀（Yuque）知识库
- yuque_list_repos: 📚 列出语雀知识库列表（需要 YUQUE_TOKEN）
- yuque_get_toc: 📂 获取知识库目录结构
- yuque_list_docs: 📄 列出知识库中所有文档
- yuque_get_doc_content: 📝 获取文档的完整 Markdown 内容
- yuque_search_docs: 🔍 在知识库中搜索文档（关键词匹配标题）
- yuque_ask: 🤔 基于知识库内容回答问题

使用方式：在 .env 中配置 YUQUE_TOKEN，或在调用时传入 token_str 参数。
语雀 API Base: https://www.yuque.com/api/v2

### 🧠 腾讯IMA知识库
- tencent_kb_init: 🔧 初始化 IMA 知识库连接配置
- tencent_kb_list_databases: 📦 列出数据库/集合列表
- tencent_kb_search: 🔍 在知识库中搜索相关内容
- tencent_kb_ask: 🤔 基于知识库回答问题
- tencent_kb_status: 📊 检查知识库连接状态

使用方式：在 .env 中配置 TENCENT_KB_API_URL 和 TENCENT_KB_API_KEY，
或在调用时传入 api_url / api_key 参数。

## 📄 文件处理（识别与修改 Office 文档）
- identify_file: 🔍 识别常见文件类型并提取基本信息。支持图片(jpg/png/gif/bmp/webp/tiff)、Word(.docx)、PowerPoint(.pptx)、Excel(.xlsx)、PDF、文本文件(txt/csv/md/json等)。
- modify_docx: ✏️ 修改 Word (.docx) 文件。支持替换文本、添加段落、添加表格、修改标题。
- modify_pptx: ✏️ 修改 PowerPoint (.pptx) 文件。支持替换幻灯片文本、添加幻灯片、修改幻灯片标题。
- modify_xlsx: ✏️ 修改 Excel (.xlsx) 文件。支持修改单元格、追加行、重命名工作表、删除行。

## 💡 搜索工具选择指南
- 查普通信息 → web_search（简单快速）
- 需要看网页内容 → web_search_and_open
- 需要切换引擎/时间筛选 → smart_search（指定 engine="duckduckgo" 使用 DuckDuckGo）
- 查最新新闻/时事 → search_news（指定 bilingual=True 同时搜索中英文）
- 需要全面覆盖不遗漏 → aggregate_search（多引擎同时搜，去重排序）
- 搜索图片 → search_images
- 获取相关搜索词 → search_suggestions
- 诊断搜索环境 → search_engine_status
- 查语雀知识库 → yuque_list_repos / yuque_search_docs / yuque_ask
- 查腾讯IMA知识库 → tencent_kb_search / tencent_kb_ask

## HTML 项目开发指南
你可以使用上述工具完整地创建、检查、修改和删除 HTML 项目：
1. 使用 create_directory + write_file 搭建项目结构
2. 使用 list_directory 查看项目文件
3. 使用 check_html_syntax / check_css_syntax / check_js_syntax 验证代码
4. 使用 write_file 修改代码，delete_file 删除不需要的文件
5. 使用 run_shell_command 启动本地服务器或运行构建工具

## C/C++/C# 项目开发
### 🅲 C 项目
- create_c_project: 创建标准 C 项目（console/library/sdl）。生成 src/main.c、include/、Makefile
- debug_c_project: 调试 C 项目（检查 gcc、编译、分析错误）
- add_c_module: 添加 C 模块（.c + .h，含初始化/清理函数）

### ➕➕ C++ 项目
- create_cpp_project: 创建标准 C++ 项目（console/library/sdl/qt）。C++17 标准
- debug_cpp_project: 调试 C++ 项目（检查 g++、检测 C++17 支持、分析模板/继承错误）
- add_cpp_module: 添加 C++ 模块（.cpp + .hpp，生成完整类框架）

### #️⃣ C# 项目
- create_csharp_project: 创建 C# 项目。优先使用 dotnet CLI，支持 console/library/winforms/webapi
- debug_csharp_project: 调试 C# 项目（检测 dotnet SDK、运行 dotnet build、分析 CS 编译错误）
- add_csharp_module: 添加 C# 模块（.cs 类文件，自动检测命名空间）

对于 GoLang 和 Shell 脚本，你也可以使用 run_shell_command 来执行 go build、go test、bash -n 等检查命令。
当用户询问最新信息、技术文档、API 用法等需要联网获取的内容时，请优先使用联网搜索工具。
需要查天气时，使用 run_weather_agent（Dolphin）。需要优化内容时，使用 run_modify_agent。
需要查企业内部知识库时，优先使用语雀或腾讯IMA知识库工具。
如需识别或修改 Office 文档（Word/PPT/Excel）或图片等文件，使用 identify_file / modify_docx / modify_pptx / modify_xlsx 工具。
请根据用户的需求，合理使用这些工具。
"""


class Agent:
    """KillerWhale 主类"""

    def __init__(self, llm_client: LLMClient):
        """初始化 Agent

        Args:
            llm_client: LLM 客户端实例
        """
        self.llm_client = llm_client
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT.strip()}
        ]

    def reset_conversation(self):
        """重置对话历史"""
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT.strip()}
        ]

    def process_message(self, user_input: str) -> str:
        """处理用户单条消息（非交互式调用）

        Args:
            user_input: 用户输入

        Returns:
            Agent 的最终文本回复
        """
        self.messages.append({"role": "user", "content": user_input})

        # 首次调用
        assistant_msg = self.llm_client.stream_chat_with_tools(
            self.messages, TOOLS_SCHEMA
        )
        print()  # 流式输出结束换行
        self.messages.append(assistant_msg)

        # 处理 tool_calls 循环
        max_iterations = 15
        iteration = 0
        while assistant_msg.get("tool_calls") and iteration < max_iterations:
            iteration += 1
            tool_calls = assistant_msg["tool_calls"]

            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                tool_args = json.loads(tc["function"]["arguments"])

                print(f"\n🔧 调用工具: {tool_name} | 参数: {tool_args}")

                # 执行工具
                if tool_name in TOOL_FUNCTIONS:
                    result = TOOL_FUNCTIONS[tool_name](**tool_args)
                else:
                    result = f"Unknown tool: {tool_name}"

                # 将工具结果返回给模型
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    }
                )

            # 再次调用模型
            assistant_msg = self.llm_client.stream_chat_with_tools(
                self.messages, TOOLS_SCHEMA
            )
            print()
            self.messages.append(assistant_msg)

        # 返回最终的文本内容
        return assistant_msg.get("content") or ""

    def run_interactive(self):
        """运行交互式对话模式"""
        print("🤖 KillerWhale 已启动（流式输出 | 60 个工具 | 支持多引擎搜索 | 支持知识库接入 | 支持文件处理）")
        print("   输入 exit / quit / 再见 退出\n")

        EXIT_KEYWORDS = {"exit", "quit", "再见"}

        while True:
            try:
                user_input = input("[You] ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 再见！")
                break

            if not user_input:
                continue

            # 检查退出条件
            if user_input.lower() in {"exit", "quit"} or user_input == "再见":
                print("👋 再见！")
                break

            # 处理消息
            print("[Agent] ", end="", flush=True)
            try:
                self.process_message(user_input)
            except Exception as e:
                print(f"\n❌ 发生错误: {e}")
