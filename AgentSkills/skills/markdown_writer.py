"""
markdown_writer.py - Markdown 文件输出工具

提供 Markdown 格式文件的生成和写入功能，
支持 GFM (GitHub Flavored Markdown) 语法规范。
"""

import os
from datetime import datetime
from typing import Optional


def write_markdown(
    content: str,
    output_path: str,
    title: Optional[str] = None,
    author: Optional[str] = None,
) -> str:
    """将 Markdown 内容写入文件

    支持自动创建父目录、自动添加 .md 后缀、自动添加文档头部元信息。

    Args:
        content: Markdown 格式的文本内容
        output_path: 输出文件路径（会自动补全 .md 后缀）
        title: 文档标题（可选，会作为一级标题写入文件头部）
        author: 作者名（可选，会写入文件头部元信息）

    Returns:
        成功或失败的消息
    """
    try:
        # 确保路径以 .md 结尾
        if not output_path.endswith(".md"):
            output_path = output_path + ".md"

        # 自动创建父目录
        parent_dir = os.path.dirname(output_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        # 构建完整的文件内容
        full_content_parts = []

        # 添加文档头部
        header_lines = []
        if title:
            header_lines.append(f"# {title}")
        if author:
            header_lines.append(f"> **作者**: {author}")
        header_lines.append(f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        header_lines.append("")
        header_lines.append("---")
        header_lines.append("")

        if header_lines:
            full_content_parts.append("\n".join(header_lines))

        # 添加正文内容
        full_content_parts.append(content)

        full_content = "\n".join(full_content_parts)

        # 写入文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_content)

        # 获取文件大小
        file_size = os.path.getsize(output_path)
        if file_size < 1024:
            size_str = f"{file_size} B"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"

        return f"✅ Markdown 文件已生成: {output_path} ({size_str})"

    except Exception as e:
        return f"❌ Markdown 文件生成失败: {e}"


def generate_markdown_table(headers: list, rows: list[list]) -> str:
    """生成 GFM 格式的 Markdown 表格

    Args:
        headers: 表头列表，如 ["名称", "数值", "备注"]
        rows: 数据行列表，每行是一个列表，如 [["苹果", "5", "水果"], ["香蕉", "3", "水果"]]

    Returns:
        格式化的 Markdown 表格字符串
    """
    if not headers:
        return ""

    # 生成分隔行（默认左对齐）
    separator = "|" + "|".join([" --- " for _ in headers]) + "|"

    # 生成表头行
    header_row = "| " + " | ".join(str(h) for h in headers) + " |"

    # 生成数据行
    data_rows = []
    for row in rows:
        # 确保每行数据与表头列数一致
        padded_row = row + [""] * (len(headers) - len(row)) if len(row) < len(headers) else row[:len(headers)]
        data_rows.append("| " + " | ".join(str(cell) for cell in padded_row) + " |")

    # 组装完整表格
    table = header_row + "\n" + separator + "\n" + "\n".join(data_rows)
    return table


def generate_markdown_code_block(code: str, language: str = "") -> str:
    """生成围栏代码块（GFM 风格）

    Args:
        code: 代码内容
        language: 编程语言名称（如 python, javascript, go, html 等），为空则不指定语言

    Returns:
        格式化的 Markdown 代码块字符串
    """
    lang_tag = language if language else ""
    return f"```{lang_tag}\n{code}\n```"


def generate_markdown_task_list(items: list[tuple[str, bool]]) -> str:
    """生成 GFM 任务列表

    Args:
        items: 任务列表，每个元素是 (任务描述, 是否已完成) 的元组
               例如: [("买菜", True), ("做饭", False), ("洗碗", False)]

    Returns:
        格式化的 Markdown 任务列表字符串
    """
    lines = []
    for description, completed in items:
        checkbox = "x" if completed else " "
        lines.append(f"- [{checkbox}] {description}")
    return "\n".join(lines)
