# 📚 知识库 API 服务器

> 轻量级 RAG 知识库 API 服务 — 将本地 Markdown 文件目录封装为 REST API

## 功能特性

- ✅ 自动扫描 Markdown 文件目录，按标题切分文档块
- ✅ 使用 `sentence-transformers` 生成向量嵌入（all-MiniLM-L6-v2，~80MB）
- ✅ 使用 ChromaDB 作为本地向量数据库，持久化存储
- ✅ **语义搜索** — 基于向量相似度的智能检索
- ✅ **AI 问答** — 可选集成 LLM，基于知识库内容生成回答
- ✅ 支持热重载 — 文档更新后无需重启服务
- ✅ 跨平台支持 — macOS / Linux / Windows
- ✅ 轻量级 — 适合小规模知识库（几百篇文档以内）

## 快速开始

### 1. 安装依赖

```bash
cd kb_api_server
pip install -r requirements.txt
```

> ⚠️ 首次运行会自动下载嵌入模型 `all-MiniLM-L6-v2`（约 80MB），请确保网络通畅。
>
> 如果下载慢，可以设置国内镜像源：
> ```bash
> export HF_ENDPOINT=https://hf-mirror.com
> ```

### 2. 准备知识库文档

将您的 Markdown 文件放入 `docs` 目录：

```
kb_api_server/
├── docs/                   # 📂 知识库文档目录
│   ├── 产品手册.md
│   ├── 技术文档.md
│   ├── FAQ.md
│   └── subfolder/          # 支持子目录递归
│       └── 开发指南.md
├── chroma_db/              # 📂 向量数据库（自动创建）
├── server.py               # 🚀 主程序
├── requirements.txt
└── README.md
```

**文档格式要求：**

- 使用 Markdown 格式（`.md` 或 `.mdx`）
- 使用 `#` 标题组织内容（`#`、`##`、`###` 等）
- 每个标题下的内容会被作为一个独立的知识块
- 过长的段落会自动按 token 数切分

**示例文档 (`docs/example.md`)：**
```markdown
# 产品名称

## 功能简介
这是一个示例产品，主要功能包括...

## 使用方法
### 安装
通过 pip 安装：pip install example

### 配置
修改配置文件中的...

## 常见问题
Q: 如何解决...
A: 可以尝试...
```

### 3. 启动服务

#### macOS / Linux

```bash
cd kb_api_server
bash start.sh
```

#### Windows

```batch
cd kb_api_server
start.bat
```

#### 或直接启动

```bash
cd kb_api_server
python server.py
```

### 4. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 预期返回:
# {"status":"ok","version":"1.0.0","docs_count":5,"chunks_count":50}
```

## API 文档

### 基础信息

| 项目 | 说明 |
|------|------|
| 基础 URL | `http://localhost:8000` |
| API 文档 | `http://localhost:8000/docs` (Swagger UI) |
| 备用文档 | `http://localhost:8000/redoc` (ReDoc) |
| 格式 | JSON |

### `GET /health` — 健康检查

检查服务是否正常运行。

```bash
curl http://localhost:8000/health
```

**返回示例：**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "docs_count": 10,
  "chunks_count": 150
}
```

### `POST /search` — 向量搜索

基于语义相似度搜索知识库。

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何安装配置",
    "top_k": 3
  }'
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | ✅ | — | 搜索关键词 |
| `top_k` | number | ❌ | 5 | 返回结果数量 |

**返回示例：**
```json
{
  "results": [
    {
      "title": "安装指南",
      "content": "## 安装步骤\n首先从官网下载安装包...",
      "score": 0.9256,
      "source": "产品手册.md"
    },
    {
      "title": "配置说明",
      "content": "## 配置文件\n修改 config.yaml 中的参数...",
      "score": 0.8732,
      "source": "技术文档.md"
    }
  ],
  "total": 2
}
```

### `POST /ask` — 基于知识库问答

根据问题检索相关文档，并使用 AI 生成回答。

> 💡 需要设置 `LLM_API_KEY` 环境变量以启用 AI 回答功能。
> 如果未配置，将直接返回最相关的文档内容。

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "这个产品支持哪些功能？",
    "top_k": 5
  }'
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `question` | string | ✅ | — | 用户问题 |
| `top_k` | number | ❌ | 5 | 检索参考文档数 |

**返回示例（AI 回答模式）：**
```json
{
  "answer": "根据产品手册，该产品支持以下功能：\n1. 数据采集与分析\n2. 实时监控告警\n3. 自动化报表生成\n4. 多用户权限管理",
  "sources": [
    {
      "title": "功能列表",
      "content": "## 功能列表\n该产品包含以下核心功能..."
    },
    {
      "title": "产品概述",
      "content": "## 产品概述\n这是一款企业级数据分析平台..."
    }
  ],
  "total": 2
}
```

### `POST /reload` — 重新加载知识库

当文档目录中的文件有新增、修改或删除时，重新加载并建立索引。

```bash
curl -X POST http://localhost:8000/reload
```

**返回示例：**
```json
{
  "status": "ok",
  "docs_count": 12,
  "chunks_count": 180
}
```

### `GET /stats` — 知识库统计

```bash
curl http://localhost:8000/stats
```

**返回示例：**
```json
{
  "docs_count": 10,
  "chunks_count": 150,
  "model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

## 配置说明

所有配置通过环境变量进行，无需修改代码：

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `KB_DOCS_DIR` | 知识库文档目录 | `./docs` |
| `LLM_API_KEY` | LLM API 密钥（可选） | 未设置（纯检索模式） |
| `LLM_BASE_URL` | LLM API 基础地址 | `https://api.deepseek.com` |
| `LLM_MODEL` | LLM 模型名称 | `deepseek-v4-flash` |
| `HOST` | 监听地址 | `0.0.0.0` |
| `PORT` | 监听端口 | `8000` |
| `CHROMA_DB_DIR` | 向量数据库目录 | `./chroma_db` |

### 配置示例

```bash
# 使用自定义知识库目录
export KB_DOCS_DIR=/path/to/your/docs

# 启用 AI 问答（使用 DeepSeek）
export LLM_API_KEY=sk-your-api-key-here
export LLM_BASE_URL=https://api.deepseek.com
export LLM_MODEL=deepseek-v4-flash

# 启用 AI 问答（使用 OpenAI）
export LLM_API_KEY=sk-your-openai-key
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_MODEL=gpt-4o-mini

# 更改端口
export PORT=8080

# 启动服务
python server.py
```

## 环境变量配置文件

可以创建 `.env` 文件来管理配置：

```bash
# .env
KB_DOCS_DIR=./my_docs
LLM_API_KEY=sk-xxxxxxxxxxxx
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
PORT=8000
```

然后在启动时加载：
```bash
export $(grep -v '^#' .env | xargs) && python server.py
```

## 与十方技能对接

### 对接 tencent_kb_search 技能

在 LeaderAgent 的 `tencent_kb_search` 技能中，将 API 调用地址改为本地服务：

**修改前（调用腾讯云 API）：**
```python
url = "https://api.tencent.com/kb/search"
```

**修改后（调用本地服务）：**
```python
url = "http://localhost:8000/search"
```

请求体示例（Python）：
```python
import requests

response = requests.post(
    "http://localhost:8000/search",
    json={
        "query": "搜索关键词",
        "top_k": 5
    }
)
results = response.json()
```

### 对接 tencent_kb_ask 技能

```python
import requests

response = requests.post(
    "http://localhost:8000/ask",
    json={
        "question": "用户问题",
        "top_k": 5
    }
)
answer = response.json()
```

### 在 Agent 中使用

```python
class KBSearchSkill:
    """知识库搜索技能"""
    
    def __init__(self, api_base_url="http://localhost:8000"):
        self.api_base_url = api_base_url
    
    def search(self, query: str, top_k: int = 5) -> dict:
        """搜索知识库"""
        resp = requests.post(
            f"{self.api_base_url}/search",
            json={"query": query, "top_k": top_k}
        )
        return resp.json()
    
    def ask(self, question: str, top_k: int = 5) -> dict:
        """基于知识库提问"""
        resp = requests.post(
            f"{self.api_base_url}/ask",
            json={"question": question, "top_k": top_k}
        )
        return resp.json()
    
    def reload(self) -> dict:
        """重新加载知识库"""
        resp = requests.post(f"{self.api_base_url}/reload")
        return resp.json()
```

## 完整的测试流程

```bash
# 1. 启动服务
cd kb_api_server
python server.py

# 2. 新开终端，测试健康检查
curl http://localhost:8000/health

# 3. 测试搜索
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "示例", "top_k": 3}'

# 4. 测试问答（不需要 LLM 也能工作）
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "如何开始使用？", "top_k": 3}'

# 5. 查看统计
curl http://localhost:8000/stats
```

## 生产环境建议

本服务适用于：
- ✅ 个人知识库
- ✅ 小团队内部文档检索
- ✅ 原型验证和 MVP
- ✅ 本地开发测试

对于生产环境，建议：
- ❌ 使用 Elasticsearch 替换 ChromaDB（大规模全文搜索）
- ❌ 使用 Milvus / Qdrant 替换 ChromaDB（大规模向量搜索）
- ❌ 增加 Redis 缓存层
- ❌ 使用 Docker 容器化部署
- ❌ 添加认证鉴权机制
- ❌ 使用专业的 LLM API 管理

## 常见问题

**Q: 启动时模型下载很慢怎么办？**
A: 设置国内镜像源：
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

**Q: 如何更新知识库？**
A: 修改 `docs` 目录下的文件后，调用 `POST /reload` 即可热更新。

**Q: 支持哪些文件格式？**
A: 支持 `.md` 和 `.mdx` 格式，递归搜索子目录。

**Q: 最大支持多少文档？**
A: 建议几百篇文档以内，ChromaDB 在小规模场景下性能良好。
超过 1000 篇建议使用专业向量数据库。

**Q: 内存占用如何？**
A: 嵌入模型约占用 200-300MB 内存，向量数据库按文档量线性增长。
100 篇文档约占用 50MB 额外内存。
