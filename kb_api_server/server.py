#!/usr/bin/env python3
"""
📚 知识库 API 服务器 — RAG 知识库搜索与问答服务

轻量级本地知识库服务，基于向量检索 + LLM 增强生成。
支持从 Markdown 文件目录构建知识库，提供语义搜索和智能问答。

环境变量:
    KB_DOCS_DIR: 知识库文档目录路径 (默认: ./docs)
    LLM_API_KEY: 大语言模型 API 密钥 (可选，用于 /ask 端点的 AI 回答)
    LLM_BASE_URL: 大语言模型 API 基础地址 (默认: https://api.deepseek.com)
    LLM_MODEL: 大语言模型名称 (默认: deepseek-v4-flash)
    HOST: 服务器监听地址 (默认: 0.0.0.0)
    PORT: 服务器监听端口 (默认: 8000)
    CHROMA_DB_DIR: ChromaDB 持久化目录 (默认: ./chroma_db)
"""

import os
import sys
import re
import glob
import logging
import traceback
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("kb_api")

# ============================================================
# 导入与降级处理
# ============================================================
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    logger.error("缺少 FastAPI 依赖，请运行: pip install fastapi uvicorn")
    logger.error("或: pip install -r requirements.txt")
    sys.exit(1)

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError:
    logger.error("缺少 ChromaDB 依赖，请运行: pip install chromadb")
    sys.exit(1)

# sentence-transformers 加载可能需要时间或内存，加个降级提示
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    logger.error("缺少 sentence-transformers 依赖，请运行: pip install sentence-transformers")
    sys.exit(1)

# OpenAI 库用于 /ask 端点，可选
try:
    from openai import OpenAI
except ImportError:
    logger.warning("缺少 openai 库，/ask 端点将使用纯检索模式。安装: pip install openai")
    OpenAI = None


# ============================================================
# 配置
# ============================================================
@dataclass
class Settings:
    """应用配置，从环境变量读取"""
    kb_docs_dir: str = os.getenv("KB_DOCS_DIR", "./docs")
    llm_api_key: Optional[str] = os.getenv("LLM_API_KEY", None) or None
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-v4-flash")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    chroma_db_dir: str = os.getenv("CHROMA_DB_DIR", "./chroma_db")
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_max_tokens: int = 512
    chunk_overlap: int = 50


settings = Settings()
logger.info(f"📋 配置: KB_DOCS_DIR={settings.kb_docs_dir}")
logger.info(f"📋 配置: LLM_API_KEY={'已配置' if settings.llm_api_key else '未配置(纯检索模式)'}")
logger.info(f"📋 配置: LLM_BASE_URL={settings.llm_base_url}")
logger.info(f"📋 配置: LLM_MODEL={settings.llm_model}")
logger.info(f"📋 配置: CHROMA_DB_DIR={settings.chroma_db_dir}")


# ============================================================
# 数据模型
# ============================================================
class HealthResponse(BaseModel):
    status: str
    version: str
    docs_count: int
    chunks_count: int


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    title: str
    content: str
    score: float
    source: str


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class AskSource(BaseModel):
    title: str
    content: str


class AskResponse(BaseModel):
    answer: str
    sources: List[AskSource]
    total: int


class ReloadResponse(BaseModel):
    status: str
    docs_count: int
    chunks_count: int


class StatsResponse(BaseModel):
    docs_count: int
    chunks_count: int
    model: str


# ============================================================
# 文档处理
# ============================================================
@dataclass
class DocumentChunk:
    """文档块"""
    title: str      # 来源文档标题
    content: str    # 块内容
    source: str     # 来源文件路径
    chunk_id: str   # 唯一标识


def estimate_tokens(text: str) -> int:
    """
    估算文本的 token 数量。
    英文约 1 token/4 字符，中文约 1 token/1.5 字符。
    """
    # 简单估算：中英文混合场景
    char_count = len(text)
    # 假设平均每 token 约 2.5 个字符
    return int(char_count / 2.5)


def split_into_chunks(text: str, max_tokens: int = 512, overlap: int = 50) -> List[str]:
    """
    将文本按 token 数限制切分成块，带重叠。
    使用滑动窗口方式，尽量在段落边界处切分。
    """
    if estimate_tokens(text) <= max_tokens:
        return [text.strip()]

    # 先按段落分割
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 如果单个段落就超长，按句子切分
        if estimate_tokens(para) > max_tokens:
            # 先把当前块加入结果
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            # 按句子切分过长段落
            sentences = re.split(r'(?<=[。！？.!?])\s+', para)
            temp_chunk = ""
            for sent in sentences:
                if estimate_tokens(temp_chunk + sent) > max_tokens:
                    if temp_chunk:
                        chunks.append(temp_chunk.strip())
                    temp_chunk = sent
                else:
                    temp_chunk += (" " if temp_chunk else "") + sent
            if temp_chunk:
                chunks.append(temp_chunk.strip())
            continue

        # 尝试将段落加入当前块
        test_chunk = (current_chunk + "\n\n" + para) if current_chunk else para
        if estimate_tokens(test_chunk) <= max_tokens:
            current_chunk = test_chunk
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para

    # 最后一块
    if current_chunk:
        chunks.append(current_chunk.strip())

    # 如果没有切分成功，直接返回原文
    if not chunks:
        chunks = [text.strip()[:max_tokens * 3]]  # 粗略截断

    return chunks


def extract_title_from_markdown(filepath: str, content: Optional[str] = None) -> str:
    """从 Markdown 文件内容或文件名提取标题"""
    if content is None:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            pass

    if content:
        # 查找第一个 # 标题
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()

    # 用文件名作为标题
    return Path(filepath).stem


def load_markdown_file(filepath: str) -> List[DocumentChunk]:
    """
    加载单个 Markdown 文件，按标题切分成块。
    使用 # ## ### 等标题作为分割点。
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.warning(f"⚠️ 读取文件失败 {filepath}: {e}")
        return []

    doc_title = extract_title_from_markdown(filepath, content)
    source_name = Path(filepath).name
    chunks: List[DocumentChunk] = []

    # 使用标题分割文档
    # 匹配 # 标题 (支持 # ## ### #### 等)
    heading_pattern = r'^(#{1,4})\s+(.+)$'
    lines = content.split('\n')

    sections = []  # [(title, content_lines)]
    current_title = doc_title
    current_lines: List[str] = []

    for line in lines:
        heading_match = re.match(heading_pattern, line)
        if heading_match:
            # 保存前一个段落
            if current_lines:
                sections.append((current_title, current_lines))
            # 新标题
            current_title = heading_match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    # 最后一段
    if current_lines:
        sections.append((current_title, current_lines))

    # 如果没有按标题切分出段落，则将整个文档作为一个部分
    if not sections or len(sections) == 1:
        section_text = content.strip()
        if section_text:
            text_chunks = split_into_chunks(
                section_text,
                max_tokens=settings.chunk_max_tokens,
                overlap=settings.chunk_overlap
            )
            for i, chunk_text in enumerate(text_chunks):
                chunk = DocumentChunk(
                    title=doc_title,
                    content=chunk_text,
                    source=source_name,
                    chunk_id=f"{source_name}::{doc_title}::chunk_{i}"
                )
                chunks.append(chunk)
        return chunks

    # 遍历每个标题段落，进一步按 token 数切分
    for sec_title, sec_lines in sections:
        sec_text = "\n".join(sec_lines).strip()
        if not sec_text:
            continue

        text_chunks = split_into_chunks(
            sec_text,
            max_tokens=settings.chunk_max_tokens,
            overlap=settings.chunk_overlap
        )

        for i, chunk_text in enumerate(text_chunks):
            chunk = DocumentChunk(
                title=sec_title,
                content=chunk_text,
                source=source_name,
                chunk_id=f"{source_name}::{sec_title}::chunk_{i}"
            )
            chunks.append(chunk)

    return chunks


def load_all_documents(docs_dir: str) -> List[DocumentChunk]:
    """
    加载指定目录下所有 Markdown 文件。
    支持递归搜索子目录。
    """
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        logger.warning(f"⚠️ 知识库目录不存在: {docs_dir}")
        logger.info(f"📝 正在创建目录: {docs_dir}")
        docs_path.mkdir(parents=True, exist_ok=True)
        # 创建一个示例文档
        example_file = docs_path / "example.md"
        example_content = """# 示例知识库文档

## 简介

这是一个示例知识库文档。您可以将自己的 Markdown 文件放在这个目录下，
服务器会自动加载并建立索引。

## 使用方法

1. 将 Markdown 文件放入 docs 目录
2. 启动服务器（自动加载）
3. 调用 API 进行搜索和问答

## 支持的格式

- 标题：使用 # 号标记
- 列表：使用 - 或 * 标记
- 代码块：使用 ``` 包裹
- 链接：使用 [文本](URL) 格式

## 注意事项

- 每个 # 标题会作为一个独立的文档块
- 过长的段落会自动按 token 数切分
- 建议每个文档块保持主题独立
"""
        example_file.write_text(example_content, encoding="utf-8")
        logger.info(f"📝 已创建示例文档: {example_file}")

    # 递归搜索所有 .md 文件
    md_files = sorted(glob.glob(str(docs_path / "**" / "*.md"), recursive=True))
    # 也支持 .mdx 文件
    mdx_files = sorted(glob.glob(str(docs_path / "**" / "*.mdx"), recursive=True))
    all_files = md_files + mdx_files

    if not all_files:
        logger.warning(f"⚠️ 在 {docs_dir} 目录下未找到任何 .md 文件")
        return []

    logger.info(f"📄 找到 {len(all_files)} 个 Markdown 文件")

    all_chunks: List[DocumentChunk] = []
    for filepath in all_files:
        chunks = load_markdown_file(filepath)
        all_chunks.extend(chunks)
        logger.debug(f"  📄 {Path(filepath).name}: {len(chunks)} 个块")

    logger.info(f"📊 共切分为 {len(all_chunks)} 个文档块")
    return all_chunks


# ============================================================
# 知识库引擎
# ============================================================
class KnowledgeBase:
    """
    知识库引擎：管理文档加载、向量化、存储和检索。
    """

    def __init__(self, docs_dir: str, chroma_dir: str):
        self.docs_dir = docs_dir
        self.chroma_dir = chroma_dir
        self.docs_count = 0
        self.chunks_count = 0
        self.model_name = settings.embedding_model_name

        # 初始化嵌入模型
        logger.info(f"🧠 正在加载嵌入模型: {self.model_name} ...")
        logger.info(f"⏳ 首次加载可能需要下载模型 (~80MB)，请耐心等待...")
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"✅ 嵌入模型加载完成 (维度: {self.model.get_sentence_embedding_dimension()})")
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            logger.error("💡 提示: 可以尝试设置环境变量 HF_ENDPOINT=https://hf-mirror.com")
            raise

        # 初始化 ChromaDB
        logger.info(f"🗄️ 初始化向量数据库: {chroma_dir}")
        os.makedirs(chroma_dir, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )
        self.collection_name = "knowledge_base"

        # 加载文档
        self._load_and_index()

    def _load_and_index(self) -> None:
        """加载文档并建立索引"""
        # 重置集合（重新加载时清空旧数据）
        try:
            self.chroma_client.delete_collection(self.collection_name)
        except Exception:
            pass

        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        # 加载文档
        all_chunks = load_all_documents(self.docs_dir)
        if not all_chunks:
            logger.warning("⚠️ 知识库为空，请添加一些 Markdown 文件")
            self.docs_count = 0
            self.chunks_count = 0
            return

        # 准备批量插入数据
        ids = []
        texts = []
        metadatas = []
        titles_seen = set()

        for chunk in all_chunks:
            chunk_id = chunk.chunk_id
            # 确保 ID 唯一
            if chunk_id in titles_seen:
                chunk_id = f"{chunk_id}_{len(titles_seen)}"
            titles_seen.add(chunk_id)

            ids.append(chunk_id)
            texts.append(chunk.content)
            metadatas.append({
                "title": chunk.title,
                "source": chunk.source,
            })

        # 批量生成嵌入并插入
        logger.info(f"🔮 正在生成 {len(texts)} 个文档块的向量嵌入...")
        batch_size = 64
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(texts))
            batch_texts = texts[start_idx:end_idx]
            batch_ids = ids[start_idx:end_idx]
            batch_metadatas = metadatas[start_idx:end_idx]

            try:
                embeddings = self.model.encode(
                    batch_texts,
                    show_progress_bar=False,
                    normalize_embeddings=True
                ).tolist()

                self.collection.add(
                    ids=batch_ids,
                    embeddings=embeddings,
                    documents=batch_texts,
                    metadatas=batch_metadatas,
                )
            except Exception as e:
                logger.error(f"❌ 批次 {batch_idx + 1}/{total_batches} 插入失败: {e}")
                continue

            if (batch_idx + 1) % 5 == 0 or batch_idx == total_batches - 1:
                logger.info(f"  📊 进度: {end_idx}/{len(texts)} ({batch_idx + 1}/{total_batches})")

        # 统计文档数量（去重）
        unique_sources = set(m["source"] for m in metadatas)
        self.docs_count = len(unique_sources)
        self.chunks_count = len(ids)

        logger.info(f"✅ 知识库加载完成！")
        logger.info(f"   📄 文档数量: {self.docs_count}")
        logger.info(f"   📊 文档块数量: {self.chunks_count}")

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """向量搜索，返回最相似的文档块"""
        if self.chunks_count == 0:
            logger.warning("⚠️ 知识库为空，无法搜索")
            return []

        try:
            # 生成查询向量
            query_embedding = self.model.encode(
                query,
                normalize_embeddings=True
            ).tolist()

            # 执行搜索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self.chunks_count),
                include=["documents", "metadatas", "distances"]
            )

            # 整理结果 (ChromaDB 返回的是嵌套列表)
            documents = results["documents"][0] if results["documents"] else []
            metadatas = results["metadatas"][0] if results["metadatas"] else []
            distances = results["distances"][0] if results["distances"] else []

            search_results = []
            for i in range(len(documents)):
                # ChromaDB 使用 cosine 距离，转换为相似度分数 (0~1)
                score = 1.0 - distances[i] if distances else 0.0
                # 确保分数在合理范围
                score = max(0.0, min(1.0, score))

                search_results.append({
                    "title": metadatas[i].get("title", "未知标题"),
                    "content": documents[i],
                    "score": round(score, 4),
                    "source": metadatas[i].get("source", "未知来源"),
                })

            # 按分数降序排列
            search_results.sort(key=lambda x: x["score"], reverse=True)
            return search_results

        except Exception as e:
            logger.error(f"❌ 搜索失败: {e}")
            logger.error(traceback.format_exc())
            return []

    def reload(self) -> None:
        """重新加载知识库"""
        logger.info("🔄 正在重新加载知识库...")
        self._load_and_index()

    def get_stats(self) -> Dict:
        """获取知识库统计信息"""
        return {
            "docs_count": self.docs_count,
            "chunks_count": self.chunks_count,
            "model": self.model_name,
        }


# ============================================================
# LLM 问答
# ============================================================
class LLMClient:
    """大语言模型客户端（可选）"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = None

        if OpenAI is None:
            logger.warning("⚠️ openai 库未安装，LLM 功能不可用")
            return

        try:
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            logger.info(f"✅ LLM 客户端初始化完成: {base_url} | 模型: {model}")
        except Exception as e:
            logger.error(f"❌ LLM 客户端初始化失败: {e}")

    def is_available(self) -> bool:
        return self.client is not None

    def ask(self, question: str, context: List[Dict]) -> str:
        """
        基于上下文回答问题。
        """
        if not self.is_available():
            return "LLM 服务不可用"

        # 构建上下文文本
        context_text = ""
        for i, ctx in enumerate(context, 1):
            context_text += f"\n[文档 {i}] 标题: {ctx['title']}\n"
            context_text += f"来源: {ctx['source']}\n"
            context_text += f"内容: {ctx['content']}\n"

        system_prompt = (
            "你是一个知识库问答助手。请根据提供的文档内容回答用户的问题。\n\n"
            "要求：\n"
            "1. 只使用提供的文档内容来回答问题\n"
            "2. 如果文档内容不足以回答问题，请明确告知「知识库中没有相关信息」\n"
            "3. 引用来源时，请注明文档标题\n"
            "4. 回答要简洁、准确、有条理\n"
            "5. 使用中文回答\n"
        )

        user_prompt = f"## 相关文档\n{context_text}\n\n## 用户问题\n{question}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2048,
                stream=False,
            )
            answer = response.choices[0].message.content
            return answer

        except Exception as e:
            logger.error(f"❌ LLM 调用失败: {e}")
            return f"抱歉，AI 回答时出现错误: {str(e)}"


# ============================================================
# FastAPI 应用
# ============================================================
app = FastAPI(
    title="📚 知识库 API 服务",
    description="RAG 知识库搜索与问答 API — 支持向量检索和 LLM 增强生成",
    version="1.0.0",
)

# CORS 中间件（允许跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局实例
kb: Optional[KnowledgeBase] = None
llm: Optional[LLMClient] = None


# ============================================================
# 应用生命周期
# ============================================================
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化知识库和 LLM"""
    global kb, llm

    logger.info("=" * 60)
    logger.info("🚀 知识库 API 服务器启动中...")
    logger.info("=" * 60)

    # 初始化知识库
    try:
        kb = KnowledgeBase(
            docs_dir=settings.kb_docs_dir,
            chroma_dir=settings.chroma_db_dir,
        )
        logger.info(f"✅ 知识库加载完成: {kb.docs_count} 篇文档, {kb.chunks_count} 个块")
    except Exception as e:
        logger.error(f"❌ 知识库初始化失败: {e}")
        logger.error(traceback.format_exc())
        logger.warning("⚠️ 服务器将启动，但知识库不可用。请检查配置后通过 /reload 重新加载。")

    # 初始化 LLM（如果配置了 API Key）
    if settings.llm_api_key:
        llm = LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
        )
        if llm.is_available():
            logger.info("✅ LLM 问答功能已启用")
        else:
            logger.warning("⚠️ LLM 客户端不可用，/ask 端点将使用纯检索模式")
            llm = None
    else:
        logger.info("ℹ️ 未配置 LLM_API_KEY，/ask 端点将使用纯检索模式")
        logger.info("💡 如需启用 AI 问答，请设置环境变量: export LLM_API_KEY=your_key")

    logger.info("=" * 60)
    logger.info(f"🌐 服务器监听: http://{settings.host}:{settings.port}")
    logger.info(f"📖 API 文档: http://{settings.host}:{settings.port}/docs")
    logger.info("=" * 60)


# ============================================================
# API 端点
# ============================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    docs_count = kb.docs_count if kb else 0
    chunks_count = kb.chunks_count if kb else 0
    return HealthResponse(
        status="ok",
        version="1.0.0",
        docs_count=docs_count,
        chunks_count=chunks_count,
    )


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    向量搜索知识库
    
    使用语义搜索找到与查询最相关的文档块。
    """
    if kb is None:
        raise HTTPException(status_code=503, detail="知识库未初始化")

    if not request.query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")

    results = kb.search(request.query, top_k=request.top_k)
    return SearchResponse(
        results=[
            SearchResult(**r) for r in results
        ],
        total=len(results),
    )


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """
    基于知识库回答问题
    
    如果配置了 LLM_API_KEY，将使用 AI 生成回答；
    否则直接返回检索到的相关文档作为上下文。
    """
    if kb is None:
        raise HTTPException(status_code=503, detail="知识库未初始化")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    # 第一步：检索相关文档
    search_results = kb.search(request.question, top_k=request.top_k)

    # 整理来源
    sources = [
        AskSource(title=r["title"], content=r["content"])
        for r in search_results
    ]

    if not sources:
        return AskResponse(
            answer="知识库中未找到与问题相关的信息。",
            sources=[],
            total=0,
        )

    # 第二步：生成回答（LLM 或纯检索）
    if llm and llm.is_available():
        # 使用 LLM 生成回答
        answer = llm.ask(request.question, search_results)
    else:
        # 纯检索模式：将最相关的内容拼接返回
        if sources:
            top_source = sources[0]
            answer = (
                f"根据知识库中的「{top_source.title}」相关文档，"
                f"找到以下相关内容：\n\n{top_source.content}"
            )
            if len(sources) > 1:
                answer += f"\n\n---\n💡 还有 {len(sources) - 1} 个相关文档片段，"
                answer += "请配置 LLM_API_KEY 以获得更完整的 AI 回答。"
        else:
            answer = "知识库中未找到相关信息。"

    return AskResponse(
        answer=answer,
        sources=sources,
        total=len(sources),
    )


@app.post("/reload", response_model=ReloadResponse)
async def reload_knowledge_base():
    """
    重新加载知识库
    
    扫描文档目录，重新切分、向量化并建立索引。
    适用于文档新增或修改后需要更新索引的场景。
    """
    if kb is None:
        raise HTTPException(status_code=503, detail="知识库未初始化，请检查启动日志")

    try:
        kb.reload()
        return ReloadResponse(
            status="ok",
            docs_count=kb.docs_count,
            chunks_count=kb.chunks_count,
        )
    except Exception as e:
        logger.error(f"❌ 重新加载失败: {e}")
        raise HTTPException(status_code=500, detail=f"重新加载失败: {str(e)}")


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    知识库统计信息
    
    返回文档数量、文档块数量、使用的嵌入模型等信息。
    """
    if kb is None:
        raise HTTPException(status_code=503, detail="知识库未初始化")

    stats = kb.get_stats()
    return StatsResponse(**stats)


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    import uvicorn

    logger.info("📚 知识库 API 服务器 v1.0.0")
    logger.info(f"📂 知识库目录: {settings.kb_docs_dir}")
    logger.info(f"🗄️  向量数据库: {settings.chroma_db_dir}")
    logger.info(f"🔗 服务地址: http://{settings.host}:{settings.port}")
    logger.info(f"📖 API 文档: http://{settings.host}:{settings.port}/docs")

    uvicorn.run(
        "server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info",
    )
