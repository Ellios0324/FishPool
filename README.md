# 🧠 AI 智能助手系统 — Leader Agent

> 一个**智能的 AI 助手调度系统**，就像您有一个"AI 大管家"，
> 可以帮您写代码、查资料、查天气、整理文档……什么都能干！
>
> ✅ 支持 **Windows** · **macOS** · **Linux**

---

## 📖 这是做什么的？

想象一下，您有一个**超级聪明的 AI 助手团队**，而 Leader Agent 就是这些助手的"总指挥官"。

您只需要**用中文**告诉它您想要什么，它就会自动调度最合适的助手来完成工作。

### 它能做什么？

| 功能 | 说明 |
|------|------|
| 💻 **写代码/改代码** | 告诉它"帮我创建一个 Python 计算器"，它就能直接生成代码 |
| 🔍 **联网搜索** | 问它"今天有什么科技新闻？"，它会搜索并总结给您 |
| 🌤️ **查天气** | 问它"北京明天天气怎么样？"，它会给出详细预报和穿衣建议 |
| 📝 **整理文档** | 可以把 Markdown 转成 Word 文档，或者生成漂亮的 PDF |
| 📊 **生成表格** | 告诉它数据，它能生成 Excel 表格（.xlsx 格式） |
| ✏️ **改写内容** | 可以把技术文档改写成小朋友都能看懂的文章 |

---

> 🧭 **给第一次使用命令行的朋友**
>
> 本教程会用到一些终端命令，别担心——我们会一步步告诉您怎么做！
> - **终端/Terminal**：就是一个黑色的输入命令的窗口
> - **💻 Windows**：按 `Win+R` → 输入 `cmd` → 回车
> - **🍎 macOS**：按 `Command+空格` → 搜索"终端" → 回车
> - **🐧 Linux**：按 `Ctrl+Alt+T`

---

## 📋 前置条件（请先准备好这些）

### 1️⃣ Python 3.9 或更高版本

> Python 是一种编程语言，这个程序就是用 Python 写的，所以需要先安装它。

| 操作系统 | 下载链接 | 安装注意事项 |
|---------|---------|-------------|
| 🪟 **Windows** | [python.org/downloads](https://www.python.org/downloads/) | ⚠️ **一定要勾选 "Add Python to PATH"**（看下面的截图） |
| 🍎 **macOS** | [python.org/downloads](https://www.python.org/downloads/) | 下载 macOS 版安装包，正常安装即可 |
| 🐧 **Linux** | 系统自带或 `sudo apt install python3` | 一般已预装，用 `python3 --version` 检查 |

> **Windows 用户注意！** 安装 Python 时，这一步**至关重要**👇
>
> ```
>  ┌─────────────────────────────────────────────────────────┐
>  │  ☐ Install launcher for all users (recommended)        │
>  │  ☑ **Add Python 3.x to PATH**  ← 一定要勾选这个！      │
>  │                                                         │
>  │  [Install Now]  [Customize installation]                │
>  └─────────────────────────────────────────────────────────┘
> ```
>
> 如果忘记勾选，可以卸载重装，或者手动把 Python 添加到系统路径。

### 2️⃣ DeepSeek API 密钥（API Key）

> 这是一个"钥匙🔑"，让程序能够调用 AI 大脑。

1. 打开 [platform.deepseek.com](https://platform.deepseek.com/)
2. 注册账号 → 登录
3. 找到 **API Keys** → 创建一个新的 Key
4. 复制这个 Key（一串以 `sk-` 开头的文本，类似 `sk-xxx...`）

---

## 🚀 快速启动（选您的操作系统）

### 🆕 第一次使用？试试"一键安装启动"

如果您是**第一次使用**，推荐运行以下脚本，它会自动完成**环境检查 + 依赖安装 + 配置引导 + 启动**：

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   一键安装启动（自动检查环境 + 安装依赖 + 启动）        │
│                                                         │
│   🪟 [Windows]  → 双击  install.bat                    │
│   🍎 [macOS]    → 终端  bash install.sh                │
│   🐧 [Linux]    → 终端  bash install.sh                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### ⚡ 已安装过依赖？用"快速启动"

如果已经运行过安装脚本，下次可以直接快速启动：

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   快速启动（假设已安装依赖，直接启动）                   │
│                                                         │
│   🪟 [Windows]  → 双击  launch_leader_terminal.bat     │
│   🍎 [macOS]    → 双击  launch_leader_terminal.command  │
│   🐧 [Linux]    → 运行  bash launch_leader_terminal.command │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🪟 Windows 用户请看这里

### 第 1 步：解压文件

找到下载的 `FishPool.zip` 压缩包。

- **右键点击** → **"全部解压缩"**（Windows 自带）
- 或者用 7-Zip / WinRAR 解压
- 解压后会得到一个名为 `FishPool` 的文件夹

### 第 2 步：运行 🎉

进入 `FishPool` 文件夹，您有两种选择：

#### 🆕 方式一：一键安装启动（推荐首次使用）

双击 **`install.bat`** — 自动完成环境检查、依赖安装、API Key 配置引导，然后启动程序。

#### ⚡ 方式二：快速启动（已安装过依赖）

双击 **`launch_leader_terminal.bat`** — 直接启动（假设依赖已安装）。

如果双击后弹出黑色窗口并显示乱码？别担心，这是正常现象，程序会自动解决这个问题。

### 遇到问题？

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| 🔴 提示"python 不是内部或外部命令" | Python 没装好或没加到 PATH | 重新安装 Python，**一定勾选 "Add Python to PATH"** |
| 🔴 提示"pip 不是内部或外部命令" | pip 没装好 | 试试 `python -m pip install -r AgentSkills\requirements.txt` |
| 🔴 窗口一闪就没了 | 出错了但来不及看 | 按住 Shift 键，右键点击文件夹空白处 → "在此处打开 PowerShell 窗口" → 输入脚本名运行 |
| 🔴 显示乱码、方块字 | 编码问题 | 本程序已自动处理（`chcp 65001`），如果还有问题请用 Windows Terminal |

---

## 🍎 macOS 用户请看这里

### 第 1 步：解压文件

找到下载的 `FishPool.zip` 压缩包，**双击**即可自动解压。
解压后会得到一个名为 `FishPool` 的文件夹。

### 第 2 步：运行 🎉

打开终端后，**先进入项目文件夹**。可以输入 `cd `（注意后面有空格），然后把 `FishPool` 文件夹从访达拖到终端窗口，按回车即可。

进入 `FishPool` 文件夹后，您有两种选择：

#### 🆕 方式一：一键安装启动（推荐首次使用）

```bash
bash install.sh
```

#### ⚡ 方式二：快速启动（已安装过依赖）

直接双击 `launch_leader_terminal.command` 文件即可启动。

> 双击 .command 文件时，如果提示"无法打开，因为无法验证开发者"，
> 请右键点击 → **打开方式** → **终端**（Terminal）。

### 遇到问题？

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| 🔴 提示"权限不足" | 文件没有执行权限 | 运行 `chmod +x install.sh` 或右键 → 打开方式 → 终端 |
| 🔴 双击后闪一下没反应 | 系统安全限制 | 右键 → 打开方式 → 终端 |
| 🔴 提示"python3: command not found" | 没安装 Python | 从 python.org 下载安装 |
| 🔴 终端里显示乱码 | 终端编码问题 | 终端菜单 → 偏好设置 → 编码 → 选择 UTF-8 |

---

## 🐧 Linux 用户请看这里

### 第 1 步：解压文件

```bash
# 在终端中进入下载目录
cd ~/Downloads

# 解压
unzip FishPool.zip -d FishPool

# 进入项目目录
cd FishPool
```

### 第 2 步：运行 🎉

进入 `FishPool` 文件夹，您有两种选择：

#### 🆕 方式一：一键安装启动（推荐首次使用）

```bash
bash install.sh
```

#### ⚡ 方式二：快速启动（已安装过依赖）

```bash
bash launch_leader_terminal.command
```

或者直接用 Python 运行：

```bash
# 安装依赖
pip3 install -r AgentSkills/requirements.txt

# 启动
python3 LeaderAgent.py
```

> 💡 `pip` 是 Python 的"软件管家"，负责安装程序所需的依赖包。上面的命令会用 pip 读取 `requirements.txt` 中的依赖列表，自动下载并安装。

### 遇到问题？

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| 🔴 提示"python3: not found" | 没安装 Python | `sudo apt install python3 python3-pip` (Debian/Ubuntu) 或 `sudo dnf install python3` (Fedora) |
| 🔴 提示"command -v 不存在" | 使用古老 shell | 请使用 bash，本脚本需要 bash |

---

## 🌟 启动成功后会看到什么？

启动成功后，您会看到一个**漂亮的彩色界面**，类似这样：

```
╔══════════════════════════════════════════╗
║  🧠  Leader Agent — 智能调度大脑        ║
║  版本 v2.0.0                            ║
╚══════════════════════════════════════════╝

  🛠️  CodingAgent     ✅   编程任务
  📚  SkillsManager   ✅   技能管理
  ✏️  ModifyAgent     ✅   内容优化
  🌤️  WeatherAgent    ✅   天气查询

  /help  查看帮助  |  /exit  退出  |  Ctrl+C  中断

  🚀 Leader >
```

看到这个界面，就说明**启动成功了**！🎉🎉🎉

### 开始使用

在 `🚀 Leader >` 提示符后面直接输入您的需求，比如：

- "帮我创建一个 Python 计算器程序"
- "北京未来三天的天气怎么样？"
- "搜索一下最近的 AI 新闻"
- "帮我把这段文字翻译成英文：..."

输入后按回车，AI 就会开始工作啦！它会实时显示它的思考过程和执行结果。

### 退出程序

- 输入 `/exit` 或 `exit` 然后按回车
- 或按 `Ctrl+C`

---

## ❗ 常见问题（FAQ）

### Q1：我看不懂英文，有没有中文界面？
**答：** 有的！整个程序都是中文界面，包括提示信息和使用说明。如果看到乱码，请确保您的终端支持 UTF-8 编码。

### Q2：程序运行很慢或者没反应？
**答：**
1. 检查您的网络是否正常
2. AI 思考需要一些时间，特别是复杂任务
3. 如果超过 2 分钟没反应，按 `Ctrl+C` 中断后重试

### Q3：我改了 .env 文件，但程序还是说 API Key 不对？
**答：**
1. 确保 `.env` 文件内容是：`DEEPSEEK_API_KEY=sk-你的密钥`
2. `=` 前后**不要有空格**
3. 确保没有多余的空行或特殊字符
4. 保存文件后**重新运行程序**

### Q4：Windows 上双击 .bat 文件后窗口一闪就没了？
**答：**
按住 `Shift` 键，在文件夹空白处右键点击 → "在此处打开 PowerShell 窗口" → 输入以下命令：
```
.\install.bat
```
或
```
.\launch_leader_terminal.bat
```
这样窗口就不会关闭，您可以看到具体的错误信息。

### Q5：macOS 上双击 .command 文件打不开？
**答：**
1. 右键点击 `.command` 文件
2. 选择"打开方式" → "终端"
3. 或者打开"终端"应用，输入：
   ```bash
   cd 项目文件夹路径
   bash install.sh
   ```

### Q6：提示 "ModuleNotFoundError: No module named 'openai'"
**答：**
依赖没有安装成功。`pip` 是 Python 的"软件管家"，负责安装程序所需的依赖包。手动运行以下命令来安装：

```bash
pip install -r AgentSkills/requirements.txt
```
（Windows 用户用 `pip`，macOS/Linux 用户用 `pip3`）

### Q7：终端显示乱码或颜色不对？
**答：**
- **Windows 用户**：建议从微软商店免费安装 **Windows Terminal**
- **macOS 用户**：使用系统自带的"终端"应用即可
- 不影响程序功能，只是显示效果略有不同

---

## 📁 项目文件说明

| 文件/文件夹 | 说明 |
|------------|------|
| `LeaderAgent.py` | 🧠 **总指挥官** — 主程序，对话入口 |
| `CodingAgent.py` | 💻 **编程助手** — 处理编程任务 |
| `SkillsManager.py` | 🔧 **技能管理员** — 管理程序的各种能力 |
| `ModifyAgent.py` | ✏️ **内容优化师** — 改写/翻译内容 |
| `WeatherAgent.py` | 🌤️ **天气预报员** — 查询天气 |
| `AgentSkills/` | 📦 **技能包** — 所有能力的代码库 |
| `cli_input.py` | ⌨️ 中文输入优化（解决退格键问题） |
| `cli_style.py` | 🎨 界面美化（漂亮的颜色和图标） |
| `.env` | 🔑 **配置文件**（存放您的 API 密钥，请勿分享！） |
| `.env.example` | 📄 配置模板（告诉您 .env 应该长什么样） |
| `install.bat` | 🪟 **Windows 一键安装启动器**（首次使用推荐） |
| `install.sh` | 🐧🍎 **macOS/Linux 一键安装启动器**（首次使用推荐） |
| `launch_leader_terminal.bat` | 🪟 **Windows 快速启动脚本**（已安装依赖后用） |
| `launch_leader_terminal.command` | 🍎🐧 **macOS/Linux 快速启动脚本**（双击或终端运行） |
| `launch_leader_terminal.py` | 🐍 **Python 启动器**（命令行启动） |
| `LeaderAgent_Terminal.app/` | 🍎 macOS 应用程序包 |

---

## 🎯 使用技巧

- 💡 **说得越详细，结果越好**
  - 试试："帮我写一个 Python 计算器" → 一般
  - 试试："帮我写一个 Python 计算器，要有加、减、乘、除功能，界面是终端版的" → 更好！
- 🔄 **如果结果不满意**：直接说"改一下"，或者提出具体修改意见
- 🛑 **想中断当前任务**：按 `Ctrl+C`
- 📋 **想看所有命令**：输入 `/help`
- 🧹 **屏幕太乱了**：输入 `/clear` 清屏

---

## 📜 许可证

本项目使用 MIT 许可证。

---

> 💖 **感谢您的使用！**
>
> 如果遇到任何问题，请先看上面的"常见问题"部分。
> 如果还是搞不定，请联系给您这个程序的人寻求帮助。
>
> **祝您使用愉快！** 🎉
