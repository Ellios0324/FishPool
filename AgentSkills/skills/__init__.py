"""
工具模块 - 提供文件操作、Shell 执行、语法检查、联网搜索、PDF生成、项目构建、
Git操作、语雀知识库、腾讯IMA知识库、文件处理等基础工具
"""

from .file_ops import (
    read_file,
    write_file,
    delete_file,
    delete_directory,
    list_directory,
    create_directory,
)
from .shell_ops import run_shell_command
from .syntax_checker import (
    check_python_syntax,
    check_yaml_syntax,
    check_html_syntax,
    check_css_syntax,
    check_js_syntax,
)
from .web_search import (
    web_search,
    web_search_and_open,
    smart_search,
    search_news,
    aggregate_search,
    search_images,
    search_suggestions,
    search_engine_status,
)
from .pdf_generator import create_pdf, PDFGenerator
from .markdown_writer import (
    write_markdown,
    generate_markdown_table,
    generate_markdown_code_block,
    generate_markdown_task_list,
)
from .md_to_docx import (
    convert_md_to_docx,
    convert_md_content_to_docx,
)
from .git_ops import (
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
from .xlsx_generator import (
    create_xlsx,
    convert_md_table_to_xlsx,
)
from .weather_tool import (
    run_weather_agent,
)
from .modify_tool import (
    run_modify_agent,
)
from .c_project import (
    create_c_project,
    debug_c_project,
    add_c_module,
)
from .cpp_project import (
    create_cpp_project,
    debug_cpp_project,
    add_cpp_module,
)
from .csharp_project import (
    create_csharp_project,
    debug_csharp_project,
    add_csharp_module,
)
# ── 语雀知识库 ──
from .yuque_kb import (
    yuque_list_repos,
    yuque_get_toc,
    yuque_list_docs,
    yuque_get_doc_content,
    yuque_search_docs,
    yuque_ask,
)
# ── 腾讯IMA知识库 ──
from .tencent_kb import (
    tencent_kb_init,
    tencent_kb_list_databases,
    tencent_kb_search,
    tencent_kb_ask,
    tencent_kb_status,
)
# ── 文件处理（识别/修改 docx/pptx/xlsx）──
from .file_processor import (
    identify_file,
    modify_docx,
    modify_pptx,
    modify_xlsx,
)

__all__ = [
    # 文件操作
    "read_file",
    "write_file",
    "delete_file",
    "delete_directory",
    "list_directory",
    "create_directory",
    # Shell 执行
    "run_shell_command",
    # 语法检查
    "check_python_syntax",
    "check_yaml_syntax",
    "check_html_syntax",
    "check_css_syntax",
    "check_js_syntax",
    # 联网搜索
    "web_search",
    "web_search_and_open",
    "smart_search",
    "search_news",
    "aggregate_search",
    "search_images",
    "search_suggestions",
    "search_engine_status",
    # PDF 生成
    "create_pdf",
    "PDFGenerator",
    # Markdown 输出
    "write_markdown",
    "generate_markdown_table",
    "generate_markdown_code_block",
    "generate_markdown_task_list",
    # Markdown 转 DOCX
    "convert_md_to_docx",
    "convert_md_content_to_docx",
    # Git 操作
    "check_git_installed",
    "git_init",
    "git_clone",
    "git_status",
    "git_add",
    "git_commit",
    "git_log",
    "git_diff",
    "git_branch",
    "git_checkout",
    "git_pull",
    "git_push",
    "git_ignore",
    "git_config",
    "git_reset",
    "git_tag",
    # Excel 生成
    "create_xlsx",
    "convert_md_table_to_xlsx",
    # Weather Agent
    "run_weather_agent",
    # Modify Agent
    "run_modify_agent",
    # C 项目
    "create_c_project",
    "debug_c_project",
    "add_c_module",
    # C++ 项目
    "create_cpp_project",
    "debug_cpp_project",
    "add_cpp_module",
    # C# 项目
    "create_csharp_project",
    "debug_csharp_project",
    "add_csharp_module",
    # ── 语雀知识库 ──
    "yuque_list_repos",
    "yuque_get_toc",
    "yuque_list_docs",
    "yuque_get_doc_content",
    "yuque_search_docs",
    "yuque_ask",
    # ── 腾讯IMA知识库 ──
    "tencent_kb_init",
    "tencent_kb_list_databases",
    "tencent_kb_search",
    "tencent_kb_ask",
    "tencent_kb_status",
    # ── 文件处理 ──
    "identify_file",
    "modify_docx",
    "modify_pptx",
    "modify_xlsx",
]
