# AgentSkills - Coding Agent 技能包

基于 DeepSeek API（兼容 OpenAI 格式）的智能 Coding Agent。

## 特性

- 🛠 **文件操作**：读取、写入、删除文件和目录
- 💻 **Shell 执行**：在本地执行 Shell 命令
- ✅ **语法检查**：检查 Python、YAML、HTML、CSS、JS 语法
- 🌐 **联网搜索**：支持 Bing、DuckDuckGo 等多引擎搜索，含新闻/图片/聚合搜索
- 📊 **Excel 生成**：创建格式美观的 .xlsx 文件，支持多工作表、斑马纹、自动列宽
- 📄 **PDF 生成**：从文本内容快速生成 PDF，支持 Markdown 风格标记
- 📝 **Markdown 输出**：写入 .md 文件、生成表格/代码块/任务列表
- 🔄 **Markdown 转 DOCX**：将 Markdown 文件或内容转换为 Word 文档
- 🌤 **天气查询**：输入城市名，获取格式化天气预报
- ✏️ **内容优化**：支持受众适配、格式转换、文本简化
- 🗃 **Git 操作**：完整 Git 工作流支持（init/clone/commit/push/pull/branch/tag 等）
- 🔄 **流式输出**：实时流式输出 LLM 回复
- 🎯 **工具自动调用**：LLM 自主决定何时调用工具

## 目录结构

```
AgentSkills/
├── __init__.py              # 包入口，导出 Skill 类
├── skill.py                 # Skill 类（统一对外接口）
├── config.yaml              # 配置文件
├── README.md                # 本文件
├── requirements.txt         # 依赖清单
├── skills/                  # 技能模块（重命名自 tools/）
│   ├── __init__.py          # 技能导出
│   ├── file_ops.py          # 文件操作
│   ├── shell_ops.py         # Shell 命令执行
│   ├── syntax_checker.py    # 语法检查
│   ├── web_search.py        # 联网搜索（多引擎）
│   ├── git_ops.py           # Git 操作
│   ├── xlsx_generator.py    # Excel 文件生成
│   ├── pdf_generator.py     # PDF 文件生成
│   ├── markdown_writer.py   # Markdown 输出
│   ├── md_to_docx.py        # Markdown 转 DOCX
│   ├── weather_tool.py      # 天气查询
│   └── modify_tool.py       # 内容优化
├── core/
│   ├── __init__.py
│   ├── agent.py             # Agent 主循环
│   └── llm_client.py        # LLM 客户端封装
└── backup/                  # 其他备份文件
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your_api_key_here
```

### 3. 使用示例

```python
from AgentSkills import Skill

# 创建 Skill 实例
skill = Skill()

# 方式一：单次处理
reply = skill.process("读取当前目录下的文件列表")
print(reply)

# 方式二：交互式对话
skill.run()
```

### 4. 自定义配置

```python
skill = Skill(
    api_key="your-api-key",         # 自定义 API 密钥
    base_url="https://api.deepseek.com",
    model="deepseek-v4-flash",      # 自定义模型
    temperature=0.5,                 # 自定义温度
)
```

## 技能清单

| 技能模块 | 文件 | 主要功能 |
|---------|------|---------|
| 文件操作 | `skills/file_ops.py` | read_file, write_file, delete_file, list_directory 等 |
| Shell 执行 | `skills/shell_ops.py` | run_shell_command |
| 语法检查 | `skills/syntax_checker.py` | Python/YAML/HTML/CSS/JS 语法检查 |
| 联网搜索 | `skills/web_search.py` | web_search, smart_search, search_news, aggregate_search 等 |
| Git 操作 | `skills/git_ops.py` | init/clone/commit/push/pull/branch/tag 等 16 个操作 |
| Excel 生成 | `skills/xlsx_generator.py` | create_xlsx, convert_md_table_to_xlsx |
| PDF 生成 | `skills/pdf_generator.py` | create_pdf（支持 Markdown 风格标记） |
| Markdown 输出 | `skills/markdown_writer.py` | write_markdown, 生成表格/代码块/任务列表 |
| Markdown 转 DOCX | `skills/md_to_docx.py` | convert_md_to_docx, convert_md_content_to_docx |
| 天气查询 | `skills/weather_tool.py` | run_weather_agent |
| 内容优化 | `skills/modify_tool.py` | run_modify_agent |

## 依赖

- Python >= 3.9
- openai >= 1.0.0
- python-dotenv >= 1.0.0
- pyyaml >= 6.0
- fpdf2 >= 2.8.0
- openpyxl >= 3.1.0
- markdown >= 3.5.0
- python-docx >= 1.1.0
- beautifulsoup4 >= 4.12.0

## 许可证

MIT
