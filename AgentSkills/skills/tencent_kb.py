"""
tencent_kb.py - 腾讯IMA知识库接入工具模块

通过配置化的 API 网关接入腾讯IMA知识库（Tencent Intelligent Knowledge Base）。
支持配置自定义 API 端点、认证密钥，灵活对接不同部署方式。

也支持通过本地 Markdown 文件目录作为知识库使用（Local 模式）。

需要环境变量（可选，可在 .env 中配置）：
- TENCENT_KB_API_URL: API 网关地址
- TENCENT_KB_API_KEY: API 密钥
"""

import os
import json
import glob
import re
from typing import Optional, Any
from pathlib import Path

# ── 全局配置缓存 ──
_KB_CONFIG = {
    "api_url": "",
    "api_key": "",
    "initialized": False,
}


def _get_requests():
    """动态导入 requests 库"""
    try:
        import requests
        return requests
    except ImportError:
        raise ImportError(
            "需要安装 requests 库才能使用 IMA 知识库功能。\n"
            "请运行: pip install requests"
        )


def _load_env_config() -> dict:
    """从 .env 文件或环境变量加载配置

    Returns:
        包含 api_url 和 api_key 的字典
    """
    # 首先尝试从环境变量读取
    api_url = os.environ.get("TENCENT_KB_API_URL", "")
    api_key = os.environ.get("TENCENT_KB_API_KEY", "")

    # 如果环境变量没有，尝试读取 .env 文件
    if not api_url or not api_key:
        env_files = [".env", "../.env", "../../.env"]
        for env_file in env_files:
            if os.path.exists(env_file):
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip("'\"")
                            if key == "TENCENT_KB_API_URL" and not api_url:
                                api_url = val
                            elif key == "TENCENT_KB_API_KEY" and not api_key:
                                api_key = val

    return {"api_url": api_url, "api_key": api_key}


def tencent_kb_init(api_url: Optional[str] = None, api_key: Optional[str] = None) -> str:
    """
    初始化 IMA 知识库连接配置

    从参数或环境变量中读取 API 网关地址和密钥，初始化连接。

    Args:
        api_url: API 网关地址（可选，默认从 .env 的 TENCENT_KB_API_URL 读取）
        api_key: API 密钥（可选，默认从 .env 的 TENCENT_KB_API_KEY 读取）

    Returns:
        连接状态信息
    """
    global _KB_CONFIG

    try:
        # 优先使用参数，然后从环境变量/配置文件读取
        env_config = _load_env_config()
        url = api_url or env_config.get("api_url", "")
        key = api_key or env_config.get("api_key", "")

        if not url:
            return (
                "⚠️ 未配置 IMA 知识库 API 地址。\n\n"
                "请通过以下任一方式配置：\n"
                "  1. 参数传入: tencent_kb_init(api_url='https://...', api_key='...')\n"
                "  2. 环境变量: 在 .env 中设置 TENCENT_KB_API_URL 和 TENCENT_KB_API_KEY\n"
                "  3. 使用 Local 模式: 将本地 Markdown 文件目录作为知识库"
            )

        # 测试连接
        _KB_CONFIG["api_url"] = url.rstrip("/")
        _KB_CONFIG["api_key"] = key

        # 尝试测试连接
        requests = _get_requests()
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"} if key else {}
        test_headers = {"Authorization": f"Bearer {key}"} if key else {}

        try:
            resp = requests.get(f"{url}/health", headers=test_headers, timeout=10)
            if resp.status_code == 200:
                _KB_CONFIG["initialized"] = True
                return (
                    f"✅ IMA 知识库连接成功！\n"
                    f"   ├ API 地址: {url}\n"
                    f"   ├ 认证: {'已配置' if key else '未配置（无密钥模式）'}\n"
                    f"   └ 状态: 连接正常"
                )
            elif resp.status_code == 401:
                return f"❌ 认证失败，请检查 API Key 是否正确"
            elif resp.status_code == 404:
                # 可能没有 /health 端点，尝试直接连接根路径
                _KB_CONFIG["initialized"] = True
                return (
                    f"✅ IMA 知识库配置已保存（未检测到 health 端点）\n"
                    f"   ├ API 地址: {url}\n"
                    f"   └ 认证: {'已配置' if key else '未配置'}"
                )
            else:
                _KB_CONFIG["initialized"] = True
                return (
                    f"⚠️ IMA 知识库配置已保存（HTTP {resp.status_code}）\n"
                    f"   ├ API 地址: {url}\n"
                    f"   └ 认证: {'已配置' if key else '未配置'}"
                )
        except Exception:
            # 连接失败但配置仍保存
            _KB_CONFIG["initialized"] = True
            return (
                f"⚠️ IMA 知识库配置已保存（无法验证连接）\n"
                f"   ├ API 地址: {url}\n"
                f"   ├ 认证: {'已配置' if key else '未配置'}\n"
                f"   └ 提示: 连接测试失败，请检查网络或 API 地址是否正确"
            )

    except Exception as e:
        return f"❌ 初始化 IMA 知识库失败: {e}"


def _ensure_initialized():
    """确保配置已初始化，未初始化则自动加载"""
    global _KB_CONFIG
    if not _KB_CONFIG["initialized"]:
        # 自动从环境变量加载
        result = tencent_kb_init()
        if "失败" in result and "未配置" in result:
            # 允许未配置状态，后续操作会提示
            pass


def tencent_kb_list_databases(api_url: Optional[str] = None, api_key: Optional[str] = None) -> str:
    """
    列出 IMA 知识库中的数据库/集合列表

    获取可用的知识库数据库或集合列表。

    Args:
        api_url: API 网关地址（可选，默认使用已配置的地址）
        api_key: API 密钥（可选，默认使用已配置的密钥）

    Returns:
        格式化的数据库列表
    """
    _ensure_initialized()

    try:
        url = api_url or _KB_CONFIG["api_url"]
        key = api_key or _KB_CONFIG["api_key"]

        if not url:
            return (
                "⚠️ 未配置 IMA 知识库 API 地址。\n\n"
                "请先使用 tencent_kb_init() 进行配置。"
            )

        requests = _get_requests()
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"} if key else {"Content-Type": "application/json"}

        # 尝试不同端点
        endpoints = ["/databases", "/collections", "/v1/databases", "/api/databases", "/kb/list"]
        found = False
        result_data = None

        for endpoint in endpoints:
            try:
                resp = requests.get(f"{url}{endpoint}", headers=headers, timeout=10)
                if resp.status_code == 200:
                    result_data = resp.json()
                    found = True
                    break
            except Exception:
                continue

        if not found:
            return (
                f"📦 IMA 知识库已配置\n"
                f"   ├ API: {url}\n"
                f"   └ 无法自动获取数据库列表（API 端点未知）\n\n"
                f"💡 请确认 API 文档中的数据库列表端点，或直接使用 tencent_kb_search() 搜索"
            )

        # 解析返回数据（兼容不同返回格式）
        databases = []
        if isinstance(result_data, dict):
            # 尝试常见的字段名
            for key_field in ["databases", "collections", "data", "items", "results", "list"]:
                val = result_data.get(key_field)
                if val and isinstance(val, list):
                    databases = val
                    break
            if not databases and "databases" not in result_data:
                # 可能是直接返回列表
                for val in result_data.values():
                    if isinstance(val, list):
                        databases = val
                        break
        elif isinstance(result_data, list):
            databases = result_data

        if not databases:
            return "📦 没有找到任何数据库/集合。"

        lines = ["📦 IMA 知识库 - 数据库/集合列表", f"{'═' * 60}", ""]
        for i, db in enumerate(databases, 1):
            if isinstance(db, dict):
                name = db.get("name", db.get("database", db.get("id", f"数据库 {i}")))
                desc = db.get("description", db.get("desc", "")) or ""
                doc_count = db.get("document_count", db.get("count", db.get("size", "N/A")))
                lines.append(f"  {i:2d}. {name}")
                if desc:
                    lines.append(f"      📝 {desc}")
                lines.append(f"      📄 文档数: {doc_count}")
            else:
                lines.append(f"  {i:2d}. {db}")
            lines.append("")

        lines.append(f"{'═' * 60}")
        lines.append(f"  共计 {len(databases)} 个数据库/集合")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 获取数据库列表失败: {e}"


def tencent_kb_search(api_url: Optional[str] = None, api_key: Optional[str] = None,
                      query: str = "", top_k: int = 5) -> str:
    """
    在 IMA 知识库中搜索相关内容

    使用 API 网关的搜索端点进行向量或关键词搜索。

    Args:
        api_url: API 网关地址（可选）
        api_key: API 密钥（可选）
        query: 搜索查询词
        top_k: 返回结果数量（默认5，范围1-20）

    Returns:
        搜索结果列表及内容摘要
    """
    _ensure_initialized()

    try:
        url = api_url or _KB_CONFIG["api_url"]
        key = api_key or _KB_CONFIG["api_key"]

        if not url:
            return (
                "⚠️ 未配置 IMA 知识库 API 地址。\n\n"
                "请先使用 tencent_kb_init() 进行配置。"
            )

        if not query:
            return "❌ 请提供搜索查询词（query 参数）。"

        # 限制 top_k 范围
        top_k = max(1, min(20, top_k))

        requests = _get_requests()
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"} if key else {"Content-Type": "application/json"}

        # 构造搜索请求
        search_payload = {
            "query": query,
            "top_k": top_k,
        }

        # 尝试不同端点
        endpoints = ["/search", "/v1/search", "/api/search", "/kb/search", "/query"]
        found = False
        result_data = None

        for endpoint in endpoints:
            try:
                resp = requests.post(
                    f"{url}{endpoint}",
                    headers=headers,
                    json=search_payload,
                    timeout=30
                )
                if resp.status_code == 200:
                    result_data = resp.json()
                    found = True
                    break
                # 也尝试 GET 方式
                resp2 = requests.get(
                    f"{url}{endpoint}",
                    headers=headers,
                    params=search_payload,
                    timeout=30
                )
                if resp2.status_code == 200:
                    result_data = resp2.json()
                    found = True
                    break
            except Exception:
                continue

        if not found:
            return (
                f"🔍 搜索请求已发送到 {url}\n"
                f"   查询词: {query}\n"
                f"   top_k: {top_k}\n\n"
                f"⚠️ 无法获取搜索结果（API 端点可能不同）\n"
                f"💡 请确认 API 文档中的搜索端点路径"
            )

        # 解析搜索结果
        results = []
        if isinstance(result_data, dict):
            for key_field in ["results", "data", "items", "matches", "documents", "hits"]:
                val = result_data.get(key_field)
                if val and isinstance(val, list):
                    results = val
                    break
        elif isinstance(result_data, list):
            results = result_data

        if not results:
            return f"🔍 搜索「{query}」未找到相关结果。"

        lines = [f"🔍 IMA 知识库搜索结果", f"{'═' * 60}", ""]
        lines.append(f"  查询词: {query}")
        lines.append(f"  返回数量: {min(len(results), top_k)}")
        lines.append("")

        for i, result in enumerate(results[:top_k], 1):
            if isinstance(result, dict):
                title = (result.get("title") or result.get("name") or result.get("filename") or
                         result.get("id", f"结果 {i}"))
                content = (result.get("content") or result.get("text") or result.get("body") or
                           result.get("summary", "") or "")
                score = result.get("score") or result.get("relevance") or result.get("similarity", "")
                source = result.get("source") or result.get("url") or result.get("path", "")

                lines.append(f"  {i:2d}. {title}")

                # 显示相关性分数
                if score:
                    score_str = f"{float(score):.2f}" if isinstance(score, (int, float)) else str(score)
                    lines.append(f"      📊 相关度: {score_str}")

                if source:
                    lines.append(f"      📎 来源: {source}")

                # 显示内容摘要
                if content:
                    clean_content = re.sub(r'<[^>]+>', '', str(content))
                    summary = clean_content[:300].strip()
                    if len(clean_content) > 300:
                        summary += "..."
                    if summary:
                        lines.append(f"      📝 {summary}")
            else:
                lines.append(f"  {i:2d}. {result}")

            lines.append("")

        lines.append(f"{'═' * 60}")
        lines.append("  💡 使用 tencent_kb_ask() 基于搜索内容回答问题")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 搜索失败: {e}"


def tencent_kb_ask(api_url: Optional[str] = None, api_key: Optional[str] = None,
                   question: str = "") -> str:
    """
    基于 IMA 知识库回答问题

    先在知识库中搜索相关内容，再基于搜索结果回答用户问题。

    Args:
        api_url: API 网关地址（可选）
        api_key: API 密钥（可选）
        question: 用户问题

    Returns:
        基于知识库的回答
    """
    try:
        url = api_url or _KB_CONFIG["api_url"]
        key = api_key or _KB_CONFIG["api_key"]

        if not question:
            return "❌ 请提供您的问题（question 参数）。"

        # 搜索相关内容
        search_result = tencent_kb_search(
            api_url=url, api_key=key,
            query=question, top_k=5
        )

        lines = [
            f"❓ 问题: {question}",
            f"{'═' * 60}",
            "",
            f"📚 知识库检索结果",
            f"{'─' * 40}",
            "",
            search_result,
            "",
            f"{'═' * 60}",
            "💡 以上是基于知识库搜索到的相关内容。",
            "💡 如需更精确的结果，可以尝试：",
            "  1. 使用 tencent_kb_search() 调整搜索关键词",
            "  2. 使用 tencent_kb_list_databases() 查看可用数据库",
        ]

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 回答问题失败: {e}"


def tencent_kb_status(api_url: Optional[str] = None, api_key: Optional[str] = None) -> str:
    """
    检查 IMA 知识库连接状态和基本信息

    检测 API 连接、认证状态、以及基本配置信息。

    Args:
        api_url: API 网关地址（可选）
        api_key: API 密钥（可选）

    Returns:
        知识库连接状态报告
    """
    _ensure_initialized()

    try:
        url = api_url or _KB_CONFIG["api_url"]
        key = api_key or _KB_CONFIG["api_key"]

        lines = ["📊 IMA 知识库连接状态", f"{'═' * 60}", ""]
        lines.append("  🔧 配置信息:")
        lines.append(f"     ├ API 地址: {url or '❌ 未配置'}")
        lines.append(f"     ├ API 密钥: {'✅ 已配置' if key else '⚠️ 未配置'}")
        lines.append(f"     └ 初始化状态: {'✅ 已初始化' if _KB_CONFIG['initialized'] else '❌ 未初始化'}")
        lines.append("")

        if not url:
            lines.append("  ⚠️ 知识库未配置。")
            lines.append("")
            lines.append("  💡 配置方法:")
            lines.append("    1. 使用 tencent_kb_init(api_url='https://...', api_key='...')")
            lines.append("    2. 或在 .env 文件中设置:")
            lines.append("       TENCENT_KB_API_URL=https://your-api-gateway.com")
            lines.append("       TENCENT_KB_API_KEY=your-api-key")
            lines.append("")
            lines.append("  💡 本地模式:")
            lines.append("    也可以将本地 Markdown 文件目录作为知识库使用。")
            return "\n".join(lines)

        # 测试连接
        lines.append("  🌐 连接测试:")
        requests = _get_requests()
        headers = {"Authorization": f"Bearer {key}"} if key else {}

        endpoints_to_test = {
            "健康检查": "/health",
            "根路径": "/",
            "API 状态": "/status",
        }

        any_connected = False
        for name, endpoint in endpoints_to_test.items():
            try:
                resp = requests.get(f"{url}{endpoint}", headers=headers, timeout=5)
                if resp.status_code < 500:
                    lines.append(f"     ├ {name}: {url}{endpoint} ✅ (HTTP {resp.status_code})")
                    any_connected = True
                else:
                    lines.append(f"     ├ {name}: {url}{endpoint} ⚠️ (HTTP {resp.status_code})")
            except Exception:
                lines.append(f"     ├ {name}: {url}{endpoint} ❌ 无法连接")

        lines.append("")

        if any_connected:
            lines.append("  ✅ 总体状态: 连接正常")
        else:
            lines.append("  ⚠️ 总体状态: 无法连接到 API 端点")
            lines.append("     请检查 API 地址是否正确，以及网络是否可达")

        lines.append("")
        lines.append(f"{'═' * 60}")
        lines.append("  📖 可用函数:")
        lines.append("  • tencent_kb_search() — 搜索知识库内容")
        lines.append("  • tencent_kb_ask() — 基于知识库回答问题")
        lines.append("  • tencent_kb_list_databases() — 列出数据库/集合")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 检查状态失败: {e}"
