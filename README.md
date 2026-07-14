# 🐟 FishPool — AI 智能调度大脑 v1.5.0

> **FishPool**（原名 Leader Agent）是一个基于 **DeepSeek API** 的智能 AI 助手调度系统。
> 它就像您的"AI 大管家"——将复杂需求自动拆解、调度最合适的 AI 助手执行，
> 支持编程、搜索、天气查询、文档处理、知识库管理等多种任务。
>
> ✅ 支持 **macOS** · **Linux** · **Windows**

---

## ✨ v1.5.0 新特性

### 🤖 QQ 机器人接入
- **OneBot v11 协议支持** — 接入 NapCatQQ / Lagrange / LLOneBot 等框架，在 QQ 中直接与 FishPool 对话
- **QQ 官方机器人 API 适配器** — 直接使用 [QQ 开放平台](https://q.qq.com/) 官方 API，无需第三方框架
- **WebSocket 鉴权修复** — 完成 IDENTIFY 鉴权流程（OpCode 2），正确处理 READY 事件获取 session_id
- **access_token 获取机制** — 支持通过 app_secret 换取 access_token 进行鉴权

### 🔧 架构升级
- **多平台消息适配器架构** — 插件式设计，支持 QQ、微信等消息平台统一接入
- **AdapterManager 管理器** — 统一的消息路由和生命周期管理
- **统一消息模型** — 跨平台消息标准化（Message 数据模型）

### 🐛 Bug 修复
- 修复 QQ 官方适配器缺少 IDENTIFY 鉴权步骤的严重 Bug
- 修复 adapter_manager 中协程未被 await 的问题
- 修复 .env 文件未被自动加载的问题
- 修复 `__init__.py` 模块导出不完整的问题

---

## 📖 项目简介

FishPool 是一个**多 Agent 协作系统**。您只需要用自然语言告诉它想要什么，它就会：

1. 🧩 **拆解需求** — 分析复杂任务，拆分为可执行的子任务
2. 🎯 **分配任务** — 路由到最合适的子 Agent（编程/搜索/天气/内容优化等）
3. 🚀 **唤醒执行** — 实时流式输出执行过程，所见即所得

所有 Agent 共享一套丰富的**技能工具箱**（AgentSkills），包括文件操作、Shell 执行、联网搜索、PDF/Excel 生成、Git 操作等。

---

## 🚀 快速开始

### 前置条件

1. **Python 3.9+**
2. **DeepSeek API 密钥** — 从 [platform.deepseek.com](https://platform.deepseek.com/) 获取

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/Ellios0324/FishPool.git
cd FishPool

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API 密钥
# 在 .env 文件中设置：
echo "DEEPSEEK_API_KEY=sk-你的密钥" > .env
```

### QQ 机器人接入（两种方式）

#### 方式一：OneBot v11 协议（需 NapCatQQ 等框架）

1. 在 `.env` 中配置：
```env
FISHPOOL_ADAPTERS_QQ_ENABLED=true
FISHPOOL_ADAPTERS_QQ_WS_URL=ws://localhost:8080/ws
FISHPOOL_ADAPTERS_QQ_BOT_QQ=你的机器人QQ号
FISHPOOL_ADAPTERS_QQ_OFFICIAL_ENABLED=false
```

2. 启动 FishPool：
```bash
python3 -m fishpool.bot
```

#### 方式二：QQ 官方 API（无需第三方框架）

1. 在 [QQ 开放平台](https://q.qq.com/) 创建机器人应用，获取 APPID、AppSecret、Token
2. 在 `.env` 中配置：
```env
FISHPOOL_ADAPTERS_QQ_ENABLED=false
FISHPOOL_ADAPTERS_QQ_OFFICIAL_ENABLED=true
FISHPOOL_ADAPTERS_QQ_OFFICIAL_APP_ID=你的APPID
FISHPOOL_ADAPTERS_QQ_OFFICIAL_APP_SECRET=你的AppSecret
FISHPOOL_ADAPTERS_QQ_OFFICIAL_TOKEN=你的Token
FISHPOOL_ADAPTERS_QQ_OFFICIAL_SANDBOX=true
```

3. 启动 FishPool：
```bash
python3 -m fishpool.bot
```

---

## 🧠 Agent 矩阵

| Agent | 职责 |
|-------|------|
| 🐟 **FishPool** (Leader) | **总指挥官** — 需求拆解、任务分配、唤醒子 Agent |
| 💻 **KillerWhale** | **编程助手** — 代码编写、项目创建、语法检查、Git 操作 |
| 🔧 **FishFarmer** | **技能管理** — 管理 AgentSkills 技能包的增删改查 |
| ✏️ **ModifyAgent** | **内容优化** — 受众适配、格式转换、多语言翻译 |
| 🌤️ **Dolphin** | **天气查询** — 多数据源天气预报 |

---

## 📁 项目结构

```
FishPool/
├── fishpool/                    # 🐟 FishPool 核心模块
│   ├── bot.py                   #   Bot 主入口
│   ├── __init__.py              #   版本信息
│   ├── adapters/                #   📱 消息适配器
│   │   ├── base.py              #     抽象基类
│   │   ├── manager.py           #     适配器管理器
│   │   ├── message.py           #     统一消息模型
│   │   ├── qq_adapter.py        #     QQ OneBot v11 适配器
│   │   ├── qq_official_adapter.py  #  QQ 官方 API 适配器
│   │   └── wechat_adapter.py    #     微信适配器
│   └── core/                    #   🧠 核心逻辑
│       └── dispatcher.py        #     消息调度器
├── AgentSkills/                 # 📦 技能包
├── LeaderAgent.py               # 🧠 总指挥官
├── CodingAgent.py               # 💻 编程助手
├── SkillsManager.py             # 🔧 技能管理
├── ModifyAgent.py               # ✏️ 内容优化
├── WeatherAgent.py              # 🌤️ 天气查询
├── .env                         # 🔑 环境配置
├── requirements.txt             # 依赖清单
└── README.md                    # 本文档
```

---

## 📜 变更日志

### v1.5.0（当前版本）
- ✨ **QQ 机器人接入**：OneBot v11 + QQ 官方 API 双方案
- ✨ **多平台适配器架构**：插件式消息适配器设计模式
- 🐛 **修复 IDENTIFY 鉴权**：QQ 官方 API WebSocket 完整连接流程
- 📝 **更新 README**：完善项目文档和配置指南

### v1.1.1
- ✨ Shift+Enter 多行输入支持
- 🐛 修复长内容显示残留问题
- 🐛 修复导入顺序导致的 NameError

### v1.0.0
- 🎉 初始发布：多 Agent 协作系统
- ✨ 5 个核心 Agent + 16 个技能模块
