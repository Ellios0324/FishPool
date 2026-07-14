# 🎉 FishPool v1.2.0 Release Note

> **发布日期：** 2025-07-14
> **标签：** `v1.2.0`
> **分支：** `dev`
> **提交：** `42ed6ce`
> **仓库：** [Ellios0324/FishPool](https://github.com/Ellios0324/FishPool)

---

## ✨ 新功能：文件识别与 Office 文档编辑

本次发布为 AgentSkills 新增了 **4 个核心文件处理技能**，使 FishPool 具备识别常见文件类型和直接修改 Office 文档的能力。

### 1️⃣ `identify_file` 🔍 — 文件智能识别

一键识别 **10+ 种常见文件类型**，并提取关键元信息：

| 文件类型 | 识别信息 |
|:---------|:---------|
| 🖼️ 图片（jpg/png/gif/bmp/webp/tiff） | 格式、宽高、色彩模式、文件大小 |
| 📄 Word（.docx） | 段落数、表格数、字符数、文档标题 |
| 📑 PowerPoint（.pptx） | 幻灯片数、幻灯片尺寸、标题列表 |
| 📊 Excel（.xlsx） | 工作表名、行/列数 |
| 📕 PDF | 页数（需 pdfplumber/PyPDF2） |
| 📄 文本文件（txt/csv/md/json/py 等 30+ 种） | 行数、字符数、编码类型 |

> 自动安装缺失依赖（Pillow、python-docx、python-pptx、openpyxl）

---

### 2️⃣ `modify_docx` ✏️ — Word 文档修改

直接编辑 `.docx` 文件，支持 **4 种操作类型**：

| 操作 | 功能 | 示例 |
|:----|:-----|:-----|
| `replace_text` | 全文/表格内文本替换 | `"OLD_TEXT" → "新文本"` |
| `add_paragraph` | 末尾添加段落（支持样式） | 可指定 Normal / Heading 1 等 |
| `add_table` | 末尾添加表格（可预填充数据） | `3×2` 表格含表头和数据 |
| `set_title` | 修改文档标题 | 自动查找 Title 样式段落 |

✅ 支持同时执行多个操作，结果可覆盖原文件或另存为新文件

---

### 3️⃣ `modify_pptx` ✏️ — PowerPoint 修改

直接编辑 `.pptx` 文件，支持 **3 种操作类型**：

| 操作 | 功能 | 示例 |
|:----|:-----|:-----|
| `replace_text` | 替换幻灯片文本（可指定某张或全部） | `slide_index: 0` 仅替换第1张 |
| `add_slide` | 末尾添加新幻灯片（含标题和要点） | 自动查找正文占位符或创建文本框 |
| `set_slide_title` | 修改指定幻灯片标题 | 自动定位标题占位符 |

---

### 4️⃣ `modify_xlsx` ✏️ — Excel 工作表修改

直接编辑 `.xlsx` 文件，支持 **4 种操作类型**：

| 操作 | 功能 | 示例 |
|:----|:-----|:-----|
| `set_cell` | 修改指定单元格值 | `(2,2) = 29` |
| `add_row` | 工作表末尾追加行 | 追加 `["王五", 25, "广州"]` |
| `set_sheet_name` | 重命名工作表 | `"Sheet1" → "员工信息"` |
| `delete_row` | 删除指定行 | 删除第 3 行数据 |

---

## 🐛 Bug 修复

- **修复 `_identify_pptx` 依赖检查 bug**：`python-pptx` 包的导入名为 `pptx`，原 `_ensure_dependency("python-pptx")` 缺少 `import_name` 参数导致自动安装失败，已修复为 `_ensure_dependency("python-pptx", "pptx")`

---

## 🔧 工程变更

| 文件 | 变更类型 | 说明 |
|:----|:--------|:-----|
| `AgentSkills/skills/file_processor.py` | 🆕 新建 | 文件处理技能模块（780 行） |
| `AgentSkills/skills/__init__.py` | 🔄 修改 | 注册 4 个新技能到导出列表 |
| `AgentSkills/core/agent.py` | 🔄 修改 | 注册新技能到 TOOL_FUNCTIONS、TOOLS_SCHEMA、SYSTEM_PROMPT |
| `AgentSkills/skills/yuque_kb.py` | 🔄 修改 | 附带的其他优化 |

---

## 📊 技能总览

```
工具总数: 56 → 60（+4）
模块覆盖: 17 个模块 / 72 个工具函数
```

使用方式：

```python
from AgentSkills.skills.file_processor import identify_file, modify_docx, modify_pptx, modify_xlsx

# 识别文件
result = identify_file("report.docx")

# 修改 Word 文档
modify_docx("report.docx", [
    {"type": "replace_text", "old": "旧文本", "new": "新文本"},
    {"type": "add_paragraph", "text": "新增段落"},
    {"type": "add_table", "rows": 3, "cols": 4, "data": [["A","B"],["C","D"]]},
    {"type": "set_title", "text": "新标题"},
])

# 修改 PowerPoint
modify_pptx("slides.pptx", [
    {"type": "replace_text", "old": "旧内容", "new": "新内容"},
    {"type": "add_slide", "title": "总结", "content": ["要点1", "要点2"]},
])

# 修改 Excel
modify_xlsx("data.xlsx", [
    {"type": "set_cell", "sheet": "Sheet1", "row": 1, "col": 1, "value": "更新值"},
    {"type": "add_row", "sheet": "Sheet1", "data": ["新行数据"]},
    {"type": "set_sheet_name", "sheet": "Sheet1", "new_name": "数据表"},
])
```

---

## 🙏 致谢

感谢所有贡献者的支持与反馈！欢迎提交 Issue 或 PR 参与项目改进。
