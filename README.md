# 🐟 FishPool — AI 智能调度大脑

> **FishPool**（原名 Leader Agent）是一个基于 **DeepSeek API** 的智能 AI 助手调度系统。
> 它就像您的"AI 大管家"——将复杂需求自动拆解、调度最合适的 AI 助手执行，
> 支持编程、搜索、天气查询、文档处理、知识库管理等多种任务。
>
> ✅ 支持 **macOS** · **Linux** · **Windows**（Git Bash）

---

## 📖 项目简介

FishPool 是一个**多 Agent 协作系统**。您只需要用自然语言告诉它想要什么，它就会：

1. 🧩 **拆解需求** — 分析复杂任务，拆分为可执行的子任务
2. 🎯 **分配任务** — 路由到最合适的子 Agent（编程/搜索/天气/内容优化等）
3. 🚀 **唤醒执行** — 实时流式输出执行过程，所见即所得

所有 Agent 共享一套丰富的**技能工具箱**（AgentSkills），包括文件操作、Shell 执行、联网搜索、PDF/Excel 生成、Git 操作等。

---

## ✨ 功能特性

### 🧠 Agent 矩阵

| Agent | 文件名 | 职责 |
|-------|--------|------|
| 🐟 **FishPool** (Leader) | `LeaderAgent.py` | **总指挥官** — 需求拆解、任务分配、唤醒子 Agent |
| 💻 **CodingAgent** | `CodingAgent.py` | **编程助手** — 代码编写、项目创建、语法检查、Git 操作 |
| 🔧 **SkillsManager** | `SkillsManager.py` | **技能管理** — 管理 AgentSkills 技能包的增删改查 |
| ✏️ **ModifyAgent** | `ModifyAgent.py` | **内容优化** — 受众适配、格式转换、多语言翻译 |
| 🌤️ **WeatherAgent** | `WeatherAgent.py` | **天气查询** — 多数据源（wttr.in / Open-Meteo）天气预报 |

### 🛠️ AgentSkills 技能工具箱

AgentSkills 是系统核心的**可复用技能包**，为所有 Agent 提供基础能力：

| 类别 | 技能模块 | 主要功能 |
|------|---------|---------|
| 📂 **文件操作** | `file_ops.py` | 读写文件、创建/删除目录、列出文件列表 |
| 💻 **Shell 执行** | `shell_ops.py` | 在本地执行 Shell 命令，支持超时控制 |
| ✅ **语法检查** | `syntax_checker.py` | 检查 Python / YAML / HTML / CSS / JS 语法 |
| 🌐 **联网搜索** | `web_search.py` | Bing 搜索（免费，无需 API Key）、新闻/图片/聚合搜索 |
| 🗃️ **Git 操作** | `git_ops.py` | init/clone/commit/push/pull/branch/tag 等 16 个操作 |
| 📊 **Excel 生成** | `xlsx_generator.py` | 生成格式美观的 .xlsx，支持多工作表、斑马纹 |
| 📄 **PDF 生成** | `pdf_generator.py` | 从文本/Markdown 生成 PDF，支持中文 |
| 📝 **Markdown 输出** | `markdown_writer.py` | 写入 .md 文件、生成表格/代码块/任务列表 |
| 🔄 **Markdown 转 DOCX** | `md_to_docx.py` | 将 Markdown 转换为 Word 文档 |
| 🌤️ **天气查询** | `weather_tool.py` | 输入城市名获取格式化天气预报 |
| ✏️ **内容优化** | `modify_tool.py` | 受众适配、格式转换、文本简化 |
| 🖥️ **C 语言项目** | `c_project.py` | 创建/调试 C 项目，添加模块 |
| ⚡ **C++ 项目** | `cpp_project.py` | 创建/调试 C++ 项目，添加模块 |
| 🔷 **C# 项目** | `csharp_project.py` | 创建/调试 C# 项目，添加模块 |
| 📚 **语雀知识库** | `yuque_kb.py` | 语雀知识库的搜索、问答、文档管理 |
| 🏢 **腾讯 IMA 知识库** | `tencent_kb.py` | 腾讯 IMA 知识库的搜索与问答 |

### 📚 知识库 API 服务器（kb_api_server）

内置轻量级 **RAG 知识库服务**，将本地 Markdown 文件目录封装为 REST API：

- 🔍 **语义搜索** — 基于 `sentence-transformers` + ChromaDB 的向量检索
- 🤖 **AI 问答** — 可选集成 LLM，基于知识库内容生成回答
- 🔄 **热重载** — 文档变更后无需重启服务
- 📖 自动生成 Swagger API 文档（`/docs`）

---

## 📁 项目结构

```
project/
├── LeaderAgent.py              # 🧠 FishPool 总指挥官（主入口）
├── CodingAgent.py              # 💻 编程助手
├── SkillsManager.py            # 🔧 技能管理
├── ModifyAgent.py              # ✏️ 内容优化
├── WeatherAgent.py             # 🌤️ 天气查询
├── SkillsManager.py            # 🔧 技能管理
├── cli_input.py                # ⌨️ 中文输入优化
├── cli_style.py                # 🎨 终端界面美化
│
├── AgentSkills/                # 📦 核心技能包
│   ├── __init__.py             #   包入口
│   ├── skill.py                #   Skill 统一对外接口
│   ├── config.yaml             #   配置文件
│   ├── requirements.txt        #   依赖清单
│   ├── core/
│   │   ├── agent.py            #   Agent 主循环
│   │   └── llm_client.py       #   LLM 客户端封装
│   └── skills/                 #   技能模块
│       ├── file_ops.py         #   文件操作
│       ├── shell_ops.py        #   Shell 命令执行
│       ├── syntax_checker.py   #   语法检查
│       ├── web_search.py       #   联网搜索
│       ├── git_ops.py          #   Git 操作
│       ├── xlsx_generator.py   #   Excel 生成
│       ├── pdf_generator.py    #   PDF 生成
│       ├── markdown_writer.py  #   Markdown 输出
│       ├── md_to_docx.py       #   Markdown 转 DOCX
│       ├── weather_tool.py     #   天气查询
│       ├── modify_tool.py      #   内容优化
│       ├── c_project.py        #   C 语言项目
│       ├── cpp_project.py      #   C++ 项目
│       ├── csharp_project.py   #   C# 项目
│       ├── yuque_kb.py         #   语雀知识库
│       └── tencent_kb.py       #   腾讯 IMA 知识库
│
├── kb_api_server/              # 📚 知识库 API 服务器
│   ├── server.py               #   主程序（FastAPI）
│   ├── requirements.txt        #   依赖清单
│   ├── start.sh                #   Linux/macOS 启动脚本
│   ├── start.bat               #   Windows 启动脚本
│   └── README.md               #   独立文档
│
├── launch_leader_terminal.command  # 🚀 macOS/Linux 启动脚本
├── launch_leader_terminal.py       # 🐍 Python 启动器
├── LeaderAgent_Terminal.app/       # 🍎 macOS 应用程序包
│
├── requirements.txt                # 系统依赖清单
├── .env                            # 🔑 环境配置（含 API Key）
├── .gitignore                      # Git 忽略规则
└── README.md                       # 本文件
```

---

## 🚀 快速开始

### 前置条件

1. **Python 3.9 或更高版本**
2. **DeepSeek API 密钥** — 从 [platform.deepseek.com](https://platform.deepseek.com/) 获取

### 1️⃣ 安装依赖

```bash
# 安装核心依赖
pip install -r AgentSkills/requirements.txt

# 如果使用知识库服务器，额外安装
pip install -r kb_api_server/requirements.txt
```

### 2️⃣ 配置 API 密钥

在项目根目录创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=sk-你的密钥
```

> ⚠️ `=` 前后不要有空格，不要有多余空行

### 3️⃣ 启动系统

#### 🍎 macOS / 🐧 Linux

```bash
# 方式一：双击启动（macOS）
# 双击 launch_leader_terminal.command

# 方式二：终端启动
bash launch_leader_terminal.command

# 方式三：直接运行
python3 LeaderAgent.py
```

#### 🪟 Windows

在 **Git Bash** 中运行：

```bash
bash launch_leader_terminal.command
```

或直接：

```bash
python LeaderAgent.py
```

### 4️⃣ 使用示例

启动后在 `🚀 Leader >` 提示符后输入：

```
# 编程任务
"帮我创建一个 Python 计算器程序"

# 天气查询
"北京未来三天的天气怎么样？"

# 联网搜索
"搜索一下最近的 AI 新闻"

# 文档处理
"帮我把这篇 Markdown 转成 Word 文档"

# 知识库问答（需要先启动 kb_api_server）
"根据知识库回答：这个产品支持哪些功能？"
```

---

## 📚 知识库服务器（可选）

FishPool 自带 RAG 知识库服务，可将本地文档转为可检索的知识库：

```bash
# 1. 准备文档
mkdir kb_api_server/docs
# 将 .md 文件放入 kb_api_server/docs/ 目录

# 2. 启动服务
cd kb_api_server
bash start.sh

# 3. 验证服务
curl http://localhost:8000/health

# 4. 搜索/问答
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "搜索关键词", "top_k": 3}'
```

详见 `kb_api_server/README.md`。

---

## 🎯 使用技巧

| 技巧 | 说明 |
|------|------|
| 💡 | **说得越详细，结果越好** — 明确描述需求和约束 |
| 🔄 | **结果不满意？** 直接说"改一下"，或提出具体意见 |
| 🛑 | **中断任务** — 按 `Ctrl+C` |
| 📋 | **查看帮助** — 输入 `/help` |
| 🧹 | **清屏** — 输入 `/clear` |
| 🚪 | **退出程序** — 输入 `/exit` 或按 `Ctrl+C` |

---

## 🛠️ 开发者指南

### 在代码中使用 AgentSkills

```python
from AgentSkills import Skill

# 创建 Skill 实例
skill = Skill()

# 单次处理
reply = skill.process("读取当前目录下的文件列表")
print(reply)

# 交互式对话
skill.run()
```

### 自定义配置

```python
skill = Skill(
    api_key="your-api-key",
    base_url="https://api.deepseek.com",
    model="deepseek-v4-flash",
    temperature=0.3,
)
```

### 配置文件 (`AgentSkills/config.yaml`)

```yaml
llm:
  api_key: "${DEEPSEEK_API_KEY}"
  base_url: "https://api.deepseek.com"
  model: "deepseek-v4-flash"
  temperature: 0.3
```

---

## 🔧 技术栈

| 类别 | 技术 |
|------|------|
| 🐍 **编程语言** | Python 3.9+ |
| 🤖 **AI 模型** | DeepSeek API（兼容 OpenAI 格式） |
| 🌐 **API 框架** | FastAPI（知识库服务器） |
| 📦 **向量检索** | sentence-transformers + ChromaDB |
| 🎨 **终端美化** | ANSI 转义码（零依赖） |
| 📊 **文件处理** | openpyxl, fpdf2, python-docx, markdown |
| 🌤️ **天气数据** | wttr.in, Open-Meteo API |
| 🔍 **搜索引擎** | Bing Search API |

---

## ❓ 常见问题

### Q1: 提示 `ModuleNotFoundError`
**答：** 依赖未安装成功。运行：
```bash
pip install -r AgentSkills/requirements.txt
```

### Q2: 提示 API Key 错误
**答：** 检查 `.env` 文件：
- 确保内容为 `DEEPSEEK_API_KEY=sk-xxx`
- `=` 前后不要有空格
- 保存后重启程序

### Q3: 程序运行很慢
**答：** AI 思考需要时间，网络请求也可能有延迟。复杂任务请耐心等待。如果超过 2 分钟没反应，按 `Ctrl+C` 中断重试。

### Q4: macOS 双击 .command 文件打不开
**答：** 右键点击 → "打开方式" → "终端"，或在终端运行：
```bash
chmod +x launch_leader_terminal.command
./launch_leader_terminal.command
```

### Q5: 终端显示乱码
**答：** 确保终端使用 UTF-8 编码。Windows 建议使用 Windows Terminal。

---

## 📜 许可证

本项目使用 MIT 许可证。

---

> 💖 **感谢您的使用！**
>
> FishPool = 智能鱼池，汇集多种 AI 能力，让复杂任务变得简单。
>
> **祝您使用愉快！** 🎉
