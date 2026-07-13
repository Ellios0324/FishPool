"""
PDF 生成工具模块

提供将文本内容转换为 PDF 文件的功能。
支持中文，支持标题/段落/列表/代码块/表格等多种格式。
"""

import os
import re
from datetime import datetime
from typing import Optional

from fpdf import FPDF


# macOS 系统可用中文字体路径
_CHINESE_FONTS = [
    "/System/Library/Fonts/STHeiti Medium.ttc",        # 华文黑体
    "/System/Library/Fonts/Hiragino Sans GB.ttc",      # 冬青黑体
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",      # 苹果 Gothic
    "/System/Library/Fonts/STHeiti Light.ttc",         # 华文黑体细体
]


def _get_chinese_font() -> str:
    """获取系统中第一个可用的中文字体路径"""
    for font_path in _CHINESE_FONTS:
        if os.path.exists(font_path):
            return font_path
    # 如果没有找到，尝试更广泛的搜索
    for root in ["/System/Library/Fonts", "/Library/Fonts",
                  os.path.expanduser("~/Library/Fonts")]:
        if os.path.exists(root):
            for f in os.listdir(root):
                if any(kw in f.lower()
                       for kw in ["chinese", "ping", "heiti", "songti",
                                  "noto", "wqy", "cjk", "hira"]):
                    full_path = os.path.join(root, f)
                    if os.path.isfile(full_path):
                        return full_path
    return ""


class PDFGenerator:
    """PDF 生成器

    支持中文文本，自动排版，支持标题/段落/列表/代码块/表格等格式。

    用法:
        gen = PDFGenerator()
        gen.add_title("报告标题")
        gen.add_paragraph("这是一段正文内容...")
        gen.add_list(["项目1", "项目2", "项目3"])
        gen.save("output.pdf")
    """

    def __init__(self, font_name: str = "ChineseFont"):
        """初始化 PDF 生成器

        Args:
            font_name: 字体名称标识
        """
        self.pdf = FPDF(orientation="P", unit="mm", format="A4")
        self.pdf.set_auto_page_break(auto=True, margin=20)
        self.font_name = font_name

        # 注册中文字体（仅注册常规样式，加粗/斜体用同一样式模拟）
        font_path = _get_chinese_font()
        if font_path:
            self.pdf.add_font(self.font_name, "", font_path)
            # fpdf2 中加粗/斜体需要单独注册字体文件
            # 对于没有独立粗体字库的字体，我们通过常规字体+字号增大来模拟
            self.font_available = True
        else:
            self.font_available = False

        # 添加第一页
        self.pdf.add_page()

    def _set_font(self, bold: bool = False, size: int = 12):
        """设置字体

        fpdf2 中粗体/斜体需要独立的字体文件注册。
        这里统一使用常规样式，通过 size 来控制视觉效果。

        Args:
            bold: 是否加粗（对中文无独立粗体字库时，仅作标记）
            size: 字号
        """
        if self.font_available:
            self.pdf.set_font(self.font_name, style="", size=size)
        else:
            self.pdf.set_font("Helvetica", style="B" if bold else "", size=size)

    def _write_title_line(self, text: str, size: int, align: str = "L"):
        """写标题行（解决 fpdf2 中文无粗体问题，用大字号模拟）"""
        if self.font_available:
            self.pdf.set_font(self.font_name, style="", size=size)
        else:
            self.pdf.set_font("Helvetica", style="B", size=size)
        self.pdf.cell(0, size * 0.65, text, new_x="LMARGIN", new_y="NEXT", align=align)

    def add_title(self, text: str, level: int = 1):
        """添加标题

        Args:
            text: 标题文本
            level: 标题级别 (1=大标题, 2=中标题, 3=小标题)
        """
        if level == 1:
            self._write_title_line(text, 22, align="C")
            self.pdf.ln(5)
        elif level == 2:
            self._write_title_line(text, 16, align="L")
            self.pdf.ln(3)
        else:
            self._write_title_line(text, 13, align="L")
            self.pdf.ln(2)

    def add_paragraph(self, text: str):
        """添加正文段落

        Args:
            text: 段落文本（支持中文、英文混排）
        """
        self._set_font(size=11)
        self.pdf.multi_cell(0, 6, text)
        self.pdf.ln(2)

    def add_list(self, items: list[str], ordered: bool = False):
        """添加列表

        Args:
            items: 列表项
            ordered: True=编号列表, False=无序列表
        """
        self._set_font(size=11)
        for i, item in enumerate(items, 1):
            prefix = f"{i}. " if ordered else "• "
            indent = 10  # 缩进
            self.pdf.set_x(indent)
            available_width = self.pdf.w - indent - self.pdf.r_margin
            self.pdf.multi_cell(available_width, 6, f"{prefix}{item}")
        self.pdf.ln(2)

    def add_code_block(self, code: str):
        """添加代码块（灰色背景）

        Args:
            code: 代码文本
        """
        self.pdf.set_fill_color(240, 240, 240)  # 浅灰色背景
        self._set_font(size=9)

        lines = code.split("\n")
        for line in lines:
            self.pdf.set_x(15)
            display_line = line[:90] if len(line) > 90 else line
            self.pdf.cell(0, 5, f"  {display_line}", fill=True,
                          new_x="LMARGIN", new_y="NEXT")
        self.pdf.ln(3)

    def add_horizontal_line(self):
        """添加水平分隔线"""
        y = self.pdf.get_y()
        self.pdf.line(15, y, self.pdf.w - 15, y)
        self.pdf.ln(3)

    def add_metadata(self, title: str = "", author: str = "LeaderAgent"):
        """添加 PDF 文档元数据

        Args:
            title: 文档标题
            author: 作者
        """
        self.pdf.set_title(title)
        self.pdf.set_author(author)
        self.pdf.set_creator("LeaderAgent - PDF Generator Tool")

    def save(self, file_path: str) -> str:
        """保存 PDF 文件

        Args:
            file_path: 输出文件路径

        Returns:
            成功或失败消息
        """
        try:
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            self.pdf.output(file_path)
            size = os.path.getsize(file_path)
            size_str = (f"{size / 1024:.1f} KB"
                        if size < 1024 * 1024
                        else f"{size / (1024 * 1024):.1f} MB")
            return f"✅ PDF 文件已生成: {file_path} ({size_str})"
        except Exception as e:
            return f"❌ PDF 生成失败: {e}"

    def add_table(self, headers: list[str], data: list[list[str]]):
        """添加表格

        Args:
            headers: 表头列表
            data: 数据行列表，每行是一个字符串列表
        """
        col_width = (self.pdf.w - self.pdf.l_margin - self.pdf.r_margin) / len(headers)

        # 表头（蓝色背景 + 白字）
        self.pdf.set_fill_color(70, 130, 180)
        self.pdf.set_text_color(255, 255, 255)
        self._set_font(size=10)
        # 用 cell 模拟粗体效果（对于无独立粗体的中文字体）
        for header in headers:
            self.pdf.cell(col_width, 8, f"  {header}", border=1, fill=True, align="C")
        self.pdf.ln()

        # 数据行
        self.pdf.set_text_color(0, 0, 0)
        self._set_font(size=9)
        for row_idx, row in enumerate(data):
            if row_idx % 2 == 0:
                self.pdf.set_fill_color(245, 245, 245)
            else:
                self.pdf.set_fill_color(255, 255, 255)

            cell_height = 7
            for i, cell_text in enumerate(row):
                self.pdf.cell(col_width, cell_height, f"  {cell_text}",
                              border=1, fill=True, align="L")
            self.pdf.ln()

        self.pdf.ln(3)
        self.pdf.set_text_color(0, 0, 0)  # 重置文字颜色


def create_pdf(
    content: str,
    output_path: str,
    title: str = "文档",
    author: str = "LeaderAgent",
) -> str:
    """从文本内容快速创建 PDF 文件（简易接口）

    自动解析内容中的 Markdown 风格格式：
    - # 一级标题, ## 二级标题, ### 三级标题
    - - 无序列表, 1. 有序列表
    - ``` 代码块 ```
    - --- 分隔线
    - | 表格 |
    - 普通文本作为段落

    Args:
        content: 文本内容（支持 Markdown 风格标记）
        output_path: 输出 PDF 文件路径
        title: 文档标题（元数据）
        author: 作者（元数据）

    Returns:
        成功或失败的消息
    """
    try:
        gen = PDFGenerator()
        gen.add_metadata(title=title, author=author)

        # 添加封面信息
        if title:
            gen.add_title(title, level=1)
            if author:
                gen._set_font(size=11)
                gen.pdf.cell(0, 8, f"作者: {author}",
                             new_x="LMARGIN", new_y="NEXT", align="C")
                gen.pdf.cell(0, 8,
                             f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                             new_x="LMARGIN", new_y="NEXT", align="C")
                gen.add_horizontal_line()

        # 解析内容
        lines = content.split("\n")
        i = 0
        in_code_block = False
        code_buffer = []
        in_table = False
        table_headers = []
        table_data = []

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # ── 代码块 ──
            if stripped.startswith("```"):
                if in_code_block:
                    gen.add_code_block("\n".join(code_buffer))
                    code_buffer = []
                    in_code_block = False
                else:
                    in_code_block = True
                i += 1
                continue

            if in_code_block:
                code_buffer.append(line)
                i += 1
                continue

            # ── 空行 ──
            if not stripped:
                # 如果有正在收集的表格，处理它
                if in_table and table_headers:
                    gen.add_table(table_headers, table_data)
                    table_headers = []
                    table_data = []
                    in_table = False
                i += 1
                continue

            # ── 表格（| ... | ... |）──
            if stripped.startswith("|") and stripped.endswith("|"):
                cells = [c.strip() for c in stripped.split("|") if c.strip()]
                # 跳过分隔行（如 |---|---|）
                if all(re.match(r"^[-:\s]+$", c) for c in cells):
                    i += 1
                    continue
                if not in_table:
                    table_headers = cells
                    in_table = True
                else:
                    table_data.append(cells)
                i += 1
                continue

            # 如果之前在处理表格但当前行不是表格行，结束表格
            if in_table and table_headers:
                gen.add_table(table_headers, table_data)
                table_headers = []
                table_data = []
                in_table = False

            # ── 分隔线 ──
            if stripped in ("---", "___", "***"):
                gen.add_horizontal_line()
                i += 1
                continue

            # ── 一级标题 ──
            if stripped.startswith("# ") and not stripped.startswith("## "):
                gen.add_title(stripped[2:].strip(), level=1)
                i += 1
                continue

            # ── 二级标题 ──
            if stripped.startswith("## ") and not stripped.startswith("### "):
                gen.add_title(stripped[3:].strip(), level=2)
                i += 1
                continue

            # ── 三级标题 ──
            if stripped.startswith("### "):
                gen.add_title(stripped[4:].strip(), level=3)
                i += 1
                continue

            # ── 有序列表 ──
            if re.match(r"^\d+[.、]\s", stripped):
                items = []
                while i < len(lines):
                    s = lines[i].strip()
                    m = re.match(r"^\d+[.、]\s(.*)", s)
                    if m:
                        items.append(m.group(1))
                        i += 1
                    else:
                        break
                gen.add_list(items, ordered=True)
                continue

            # ── 无序列表 ──
            if stripped.startswith("- ") or stripped.startswith("* "):
                items = []
                while i < len(lines):
                    s = lines[i].strip()
                    if s.startswith("- "):
                        items.append(s[2:].strip())
                        i += 1
                    elif s.startswith("* "):
                        items.append(s[2:].strip())
                        i += 1
                    else:
                        break
                gen.add_list(items, ordered=False)
                continue

            # ── 普通段落 ──
            paragraph = line
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if (not next_line or
                        next_line.startswith("#") or
                        next_line.startswith("- ") or
                        next_line.startswith("* ") or
                        next_line.startswith("|") or
                        re.match(r"^\d+[.、]\s", next_line) or
                        next_line in ("---", "___", "***") or
                        next_line.startswith("```")):
                    break
                paragraph += " " + next_line
                i += 1
            gen.add_paragraph(paragraph)

        # 处理末尾未关闭的代码块
        if in_code_block and code_buffer:
            gen.add_code_block("\n".join(code_buffer))

        # 处理末尾未关闭的表格
        if in_table and table_headers:
            gen.add_table(table_headers, table_data)

        return gen.save(output_path)

    except Exception as e:
        return f"❌ PDF 生成失败: {e}"
