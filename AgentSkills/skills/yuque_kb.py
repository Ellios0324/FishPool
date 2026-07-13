"""
yuque_kb.py - 语雀（Yuque）知识库接入工具模块

通过语雀开放 API v2 获取知识库内容，支持：
- 列出知识库
- 获取目录结构
- 列出文档列表
- 关键词搜索文档
- 获取文档 Markdown 内容
- 基于知识库内容回答问题

需要环境变量 YUQUE_TOKEN（在 .env 中配置或在语雀设置中生成 Personal Token）。
所有函数使用 try/except 包裹，requests 动态导入。
"""

import os
import json
import re
from typing import Optional, Any

# ── 语雀 API 基础配置 ──
YUQUE_API_BASE = "https://www.yuque.com/api/v2"


def _get_requests():
    """动态导入 requests 库，未安装时给出友好提示"""
    try:
        import requests
        return requests
    except ImportError:
        raise ImportError(
            "需要安装 requests 库才能使用语雀功能。\n"
            "请运行: pip install requests"
        )


def _get_headers(token_str: str) -> dict:
    """构建语雀 API 请求头

    Args:
        token_str: 语雀 Personal Token

    Returns:
        包含认证信息的请求头字典
    """
    return {
        "X-Auth-Token": token_str,
        "User-Agent": "CodingAgent-YuqueKB/1.0",
        "Accept": "application/json",
    }


def _api_get(token_str: str, path: str, params: Optional[dict] = None) -> dict:
    """通用语雀 API GET 请求

    Args:
        token_str: API Token
        path: API 路径（如 /users/:login/repos）
        params: 查询参数

    Returns:
        解析后的 JSON 响应

    Raises:
        Exception: 当 API 返回错误时抛出
    """
    requests = _get_requests()
    url = f"{YUQUE_API_BASE}{path}" if not path.startswith("http") else path
    headers = _get_headers(token_str)

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise Exception(f"语雀 API 错误: {data.get('error_description', data['error'])}")
        return data
    except requests.exceptions.Timeout:
        raise Exception("请求语雀 API 超时，请检查网络连接")
    except requests.exceptions.ConnectionError:
        raise Exception("无法连接到语雀 API，请检查网络连接")
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code
        if status == 401:
            raise Exception("语雀 Token 无效或已过期，请检查 YUQUE_TOKEN 配置")
        elif status == 403:
            raise Exception("没有权限访问该资源")
        elif status == 404:
            raise Exception("请求的资源不存在")
        else:
            raise Exception(f"语雀 API HTTP {status} 错误: {e}")


def _get_user_login(token_str: str) -> str:
    """获取当前 Token 对应的用户 login

    通过获取用户信息来确定用户 login 值。

    Args:
        token_str: API Token

    Returns:
        用户 login（字符串形式的 ID）
    """
    data = _api_get(token_str, "/user")
    user = data.get("data", {})
    return user.get("login", str(user.get("id", "")))


def yuque_list_repos(token_str: str, user_login: Optional[str] = None) -> str:
    """
    列出语雀知识库列表

    获取指定用户（或 Token 对应用户）的所有知识库。

    Args:
        token_str: 语雀 API Token（必填，需在 .env 配置 YUQUE_TOKEN）
        user_login: 用户名（可选，默认使用 Token 对应用户）

    Returns:
        格式化的知识库列表，包含名称、ID、类型、更新时间、文档数等信息
    """
    try:
        login = user_login or _get_user_login(token_str)
        data = _api_get(token_str, f"/users/{login}/repos")

        repos = data.get("data", [])
        if not repos:
            return "📚 没有找到知识库。"

        lines = ["📚 语雀知识库列表", f"{'═' * 60}", ""]
        for i, repo in enumerate(repos, 1):
            name = repo.get("name", "未知名称")
            repo_id = repo.get("id", "")
            repo_type = repo.get("type", "")
            namespace = repo.get("namespace", "")
            updated_at = repo.get("updated_at", "").replace("T", " ").split("+")[0]
            items_count = repo.get("items_count", "N/A")
            description = repo.get("description", "") or ""

            type_map = {"Book": "📖 文档库", "Design": "🎨 设计稿", "Whiteboard": "📋 白板"}
            type_str = type_map.get(repo_type, f"📦 {repo_type}")

            lines.append(f"  {i}. {name}")
            lines.append(f"     ├ ID: {repo_id}")
            lines.append(f"     ├ 类型: {type_str}")
            lines.append(f"     ├ 命名空间: {namespace}")
            lines.append(f"     ├ 文档数: {items_count}")
            lines.append(f"     └ 更新: {updated_at}")
            if description:
                lines.append(f"     📝 {description}")
            lines.append("")

        lines.append(f"{'═' * 60}")
        lines.append(f"  共计 {len(repos)} 个知识库")
        lines.append("  💡 使用 yuque_get_toc('<token>', <repo_id>) 查看目录")
        lines.append("  💡 使用 yuque_list_docs('<token>', <repo_id>) 查看文档列表")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 获取知识库列表失败: {e}\n\n请检查:\n1. YUQUE_TOKEN 是否配置正确\n2. 网络连接是否正常"


def yuque_get_toc(token_str: str, repo_id: Any) -> str:
    """
    获取知识库目录结构

    获取指定知识库的 TOC（Table of Contents），展示层级目录结构。

    Args:
        token_str: 语雀 API Token
        repo_id: 知识库 ID（数字或字符串）

    Returns:
        格式化的目录结构，包含文档标题、层级和 ID
    """
    try:
        data = _api_get(token_str, f"/repos/{repo_id}/toc")
        toc_items = data.get("data", [])

        if not toc_items:
            return "📂 该知识库目录为空。"

        lines = ["📂 知识库目录结构", f"{'═' * 60}", ""]

        for item in toc_items:
            title = item.get("title", "无标题")
            item_id = item.get("id", "")
            item_type = item.get("type", "DOC")
            depth = item.get("depth", 0)
            slug = item.get("slug", "")
            indent = "  " * depth

            if item_type == "DOC":
                prefix = "📄"
                lines.append(f"{indent}  {prefix} {title}")
                if slug:
                    lines.append(f"{indent}    📎 ID: {item_id} | Slug: {slug}")
                else:
                    lines.append(f"{indent}    📎 ID: {item_id}")
            elif item_type == "TITLE":
                prefix = "📁"
                lines.append(f"{indent}  {prefix} {title}")
                lines.append(f"{indent}  │  📎 ID: {item_id}")

        lines.append("")
        lines.append(f"{'═' * 60}")
        lines.append(f"  共计 {len(toc_items)} 个条目")
        lines.append("  💡 使用 yuque_get_doc_content() 查看文档内容")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 获取目录失败: {e}\n\n请检查 repo_id 是否正确"


def yuque_list_docs(token_str: str, repo_id: Any) -> str:
    """
    列出知识库中的所有文档

    获取指定知识库的文档列表，返回文档标题、更新时间等信息。

    Args:
        token_str: 语雀 API Token
        repo_id: 知识库 ID

    Returns:
        格式化的文档列表
    """
    try:
        data = _api_get(token_str, f"/repos/{repo_id}/docs")
        docs = data.get("data", [])

        if not docs:
            return "📄 该知识库中没有文档。"

        lines = ["📄 知识库文档列表", f"{'═' * 60}", ""]
        for i, doc in enumerate(docs, 1):
            title = doc.get("title", "无标题")
            doc_id = doc.get("id", "")
            slug = doc.get("slug", "")
            updated_at = doc.get("updated_at", "").replace("T", " ").split("+")[0]
            word_count = doc.get("word_count", "N/A")

            lines.append(f"  {i:2d}. {title}")
            lines.append(f"      ├ ID: {doc_id}")
            if slug:
                lines.append(f"      ├ Slug: {slug}")
            lines.append(f"      ├ 字数: {word_count}")
            lines.append(f"      └ 更新: {updated_at}")
            lines.append("")

        lines.append(f"{'═' * 60}")
        lines.append(f"  共计 {len(docs)} 篇文档")
        lines.append("  💡 使用 yuque_get_doc_content() 查看文档内容")
        lines.append("  💡 使用 yuque_search_docs() 搜索文档")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 获取文档列表失败: {e}"


def yuque_get_doc_content(token_str: str, repo_id: Any, doc_id_or_slug: str) -> str:
    """
    获取文档的完整 Markdown 内容

    获取指定文档的原始 Markdown 内容，便于阅读或进一步处理。

    Args:
        token_str: 语雀 API Token
        repo_id: 知识库 ID
        doc_id_or_slug: 文档 ID（数字）或 Slug（路径名）

    Returns:
        文档的 Markdown 内容，包含文档头部元信息
    """
    try:
        # 使用 ?raw=1 获取原始 Markdown
        data = _api_get(token_str, f"/repos/{repo_id}/docs/{doc_id_or_slug}", {"raw": 1})
        doc = data.get("data", {})

        title = doc.get("title", "无标题")
        doc_id = doc.get("id", "")
        slug = doc.get("slug", "")
        content = doc.get("body", doc.get("body_html", doc.get("raw_content", "")))
        updated_at = doc.get("updated_at", "").replace("T", " ").split("+")[0]
        description = doc.get("description", "") or ""
        word_count = doc.get("word_count", "N/A")

        lines = [
            f"# {title}",
            "",
            f"> 📎 ID: {doc_id} | Slug: {slug} | 字数: {word_count} | 更新: {updated_at}",
        ]
        if description:
            lines.append(f"> 📝 {description}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(content if content else "（文档内容为空）")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 获取文档内容失败: {e}\n\n请检查 repo_id 和 doc_id/slug 是否正确"


def yuque_search_docs(token_str: str, repo_id: Any, keyword: str) -> str:
    """
    在知识库中搜索文档

    通过获取知识库所有文档，在本地进行关键词匹配搜索。
    注意：语雀 API 没有提供全文搜索端点，因此通过遍历文档标题来匹配。

    Args:
        token_str: 语雀 API Token
        repo_id: 知识库 ID
        keyword: 搜索关键词

    Returns:
        匹配的文档列表及简要信息
    """
    try:
        data = _api_get(token_str, f"/repos/{repo_id}/docs")
        docs = data.get("data", [])

        if not docs:
            return "📄 该知识库中没有文档。"

        # 本地关键词匹配
        keyword_lower = keyword.lower()
        matched = []

        for doc in docs:
            title = doc.get("title", "")
            description = doc.get("description", "") or ""
            slug = doc.get("slug", "")
            if (keyword_lower in title.lower() or
                keyword_lower in description.lower() or
                keyword_lower in slug.lower()):
                matched.append(doc)

        if not matched:
            return f"🔍 在知识库中未找到包含「{keyword}」的文档。"

        lines = [f"🔍 搜索关键词: 「{keyword}」", f"{'═' * 60}", ""]
        lines.append(f"  找到 {len(matched)} 篇匹配文档：")
        lines.append("")

        for i, doc in enumerate(matched, 1):
            title = doc.get("title", "无标题")
            doc_id = doc.get("id", "")
            slug = doc.get("slug", "")
            updated_at = doc.get("updated_at", "").replace("T", " ").split("+")[0]
            description = doc.get("description", "") or ""

            lines.append(f"  {i:2d}. {title}")
            lines.append(f"      ├ ID: {doc_id}")
            if slug:
                lines.append(f"      ├ Slug: {slug}")
            lines.append(f"      └ 更新: {updated_at}")
            if description:
                lines.append(f"      📝 {description[:100]}{'...' if len(description) > 100 else ''}")
            lines.append("")

        lines.append(f"{'═' * 60}")
        lines.append("  💡 使用 yuque_get_doc_content() 查看文档内容")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 搜索文档失败: {e}"


def yuque_ask(token_str: str, repo_id: Any, question: str) -> str:
    """
    基于知识库内容回答问题

    通过获取知识库的目录和文档列表，对文档标题进行关键词匹配，
    找到最相关的文档后获取其内容，基于内容回答用户问题。

    这是一个轻量级的本地检索方案。对于大规模知识库，
    建议使用专业的全文搜索或向量检索方案。

    Args:
        token_str: 语雀 API Token
        repo_id: 知识库 ID
        question: 用户的问题

    Returns:
        基于知识库内容的回答
    """
    try:
        # 1. 获取知识库基本信息
        data = _api_get(token_str, f"/repos/{repo_id}")
        repo_info = data.get("data", {})
        repo_name = repo_info.get("name", "知识库")

        # 2. 获取文档列表
        docs_data = _api_get(token_str, f"/repos/{repo_id}/docs")
        docs = docs_data.get("data", [])

        if not docs:
            return f"📚 知识库「{repo_name}」中暂无文档，无法回答您的问题。"

        # 3. 提取问题中的关键词
        stop_words = ["什么", "怎么", "如何", "为什么", "哪个", "哪里", "多少",
                      "请问", "告诉", "是", "的", "了", "吗", "吧", "呢", "啊", "呀"]
        keywords = []
        for word in re.split(r'[，。！？、；：""''（）\(\)\[\]\s]', question):
            word = word.strip()
            if word and word not in stop_words and len(word) >= 2:
                keywords.append(word)

        if not keywords:
            keywords = [w for w in re.split(r'\s+', question) if len(w) >= 2]
        if not keywords:
            keywords = [question]

        # 4. 文档匹配评分
        scored_docs = []
        for doc in docs:
            title = doc.get("title", "")
            description = doc.get("description", "") or ""
            score = 0
            matched_keywords = []

            for kw in keywords:
                if kw.lower() in title.lower():
                    score += 3
                    matched_keywords.append(kw)
                if kw.lower() in description.lower():
                    score += 1
                    matched_keywords.append(kw)

            if score > 0:
                scored_docs.append((score, doc, matched_keywords))

        scored_docs.sort(key=lambda x: x[0], reverse=True)

        # 5. 构建回答
        result_lines = [
            f"📚 知识库: {repo_name}",
            f"❓ 问题: {question}",
            f"{'═' * 60}",
            "",
        ]

        if not scored_docs:
            result_lines.append(f"🤷 未在知识库中找到与问题「{question}」高度相关的文档。")
            result_lines.append("")
            result_lines.append("💡 建议：")
            result_lines.append("  1. 使用 yuque_search_docs() 搜索相关关键词")
            result_lines.append("  2. 使用 yuque_list_docs() 浏览所有文档")
            result_lines.append("  3. 尝试换一种表述方式提问")
            return "\n".join(result_lines)

        # 获取最匹配的 1~2 篇文档
        top_docs = scored_docs[:min(2, len(scored_docs))]

        for idx, (score, doc, matched_kws) in enumerate(top_docs, 1):
            title = doc.get("title", "无标题")
            doc_id = doc.get("id", "")
            slug = doc.get("slug", "")
            description = doc.get("description", "") or ""

            result_lines.append(f"📄 相关文档 {idx}: {title}")
            result_lines.append(f"   匹配关键词: {', '.join(set(matched_kws))}")
            result_lines.append(f"   相关度评分: {score}")
            if description:
                result_lines.append(f"   简介: {description}")

            # 获取文档内容摘要
            try:
                content_data = _api_get(token_str, f"/repos/{repo_id}/docs/{doc_id}", {"raw": 1})
                content_doc = content_data.get("data", {})
                body = content_doc.get("body", "") or content_doc.get("raw_content", "") or ""

                body_text = re.sub(r'<[^>]+>', '', body)
                summary = body_text[:2000]
                if len(body_text) > 2000:
                    summary += "\n...（内容较长，已截取）"

                if summary.strip():
                    result_lines.append("")
                    result_lines.append(f"  内容摘要:")
                    result_lines.append(f"  {'─' * 40}")
                    for line in summary.split('\n'):
                        if line.strip():
                            result_lines.append(f"  {line}")
                else:
                    result_lines.append("  （文档内容为空）")
            except Exception as e:
                result_lines.append(f"  （无法获取文档内容: {e}）")

            result_lines.append("")
            result_lines.append(f"  💡 使用 yuque_get_doc_content() 查看完整内容")
            result_lines.append("")

        result_lines.append(f"{'═' * 60}")
        result_lines.append(f"  共检索 {len(docs)} 篇文档，找到 {len(scored_docs)} 篇相关文档")

        return "\n".join(result_lines)

    except Exception as e:
        return f"❌ 回答问题失败: {e}"
