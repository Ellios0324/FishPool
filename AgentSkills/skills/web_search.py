"""
🌐 增强型联网搜索工具模块 v2.1 — 全面优化版（编码修复版）

提供多引擎、多功能搜索能力，完全免费（无需 API Key）。
通过 HTML 解析方式获取搜索结果，稳定可靠。

【功能特性】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 多引擎切换     — Google / Bing / DuckDuckGo / Bing News / 百度 (Baidu)
✅ 新闻搜索模式   — 专门针对时事政治新闻优化
✅ 图片搜索       — 搜索图片并返回结果
✅ 时间筛选       — 按时间范围过滤结果（24h/7d/30d/1y）
✅ 中英文双语搜索 — 同时搜索中英文来源并合并
✅ 聚合搜索       — 多引擎同时搜索，结果去重排序
✅ 相关搜索建议   — 提取相关搜索词供参考
✅ 智能重试       — 请求失败时自动重试
✅ LRU 缓存       — 限制最大缓存条目，防内存泄漏
✅ 引擎健康检查   — 检测各搜索引擎可用性
✅ 编码自动检测   — 自动检测网页编码，解决乱码问题
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

公开工具函数：
  - web_search()              — 🔍 Bing 搜索（原始接口，保持兼容）
  - web_search_and_open()     — 📄 搜索并打开网页（增强版）
  - smart_search()            — 🔬 智能搜索（多引擎切换/时间筛选/语言选择）
  - search_news()             — 📰 新闻搜索（中英文双语/时间范围）
  - aggregate_search()        — 🔗 聚合搜索（多引擎同时搜索/去重排序）
  - search_images()           — 🖼️ 图片搜索（新增！）
  - search_suggestions()      — 💡 相关搜索建议（新增！）
  - search_engine_status()    — ⚡ 搜索引擎健康检查（新增！）
"""

import re
import time
from typing import Optional
from urllib.parse import urlencode, urlparse, unquote, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from collections import OrderedDict

# ═══════════════════════════════════════════════════════════════
#  全局配置与缓存
# ═══════════════════════════════════════════════════════════════

_MAX_CACHE_SIZE = 200  # 最大缓存条目数
_CACHE_TTL = 60  # 缓存有效期（秒）

# 使用 OrderedDict 实现 LRU 缓存
_search_cache: OrderedDict[str, tuple[float, str]] = OrderedDict()

# 默认请求头（模拟真实浏览器）
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 备用 User-Agent 列表（用于轮换）
_BACKUP_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
]

# 时间范围映射
_TIME_FILTERS = {
    "24h": "-1",     # 过去24小时
    "7d": "-7",      # 过去7天
    "30d": "-30",    # 过去30天
    "1y": "-365",    # 过去1年
}

# 时间标签
_TIME_LABELS = {
    "24h": "过去24小时",
    "7d": "过去7天",
    "30d": "过去30天",
    "1y": "过去1年",
    None: "",
}

# 支持的语言市场代码
_LANG_MARKETS = {
    "zh": "zh-CN",
    "en": "en-US",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "fr": "fr-FR",
    "de": "de-DE",
    "es": "es-ES",
}

# Google 的国家代码
_GOOGLE_GL = {
    "zh": "cn",
    "en": "us",
    "ja": "jp",
    "ko": "kr",
    "fr": "fr",
    "de": "de",
    "es": "es",
}

# 最大重试次数
_MAX_RETRIES = 2


# ═══════════════════════════════════════════════════════════════
#  编码检测辅助函数
# ═══════════════════════════════════════════════════════════════

def _detect_encoding(raw_data: bytes, content_type: str = "") -> str:
    """自动检测网页字节数据的编码

    检测优先级：
    1. HTTP Content-Type 头的 charset 参数
    2. HTML <meta charset> 标签
    3. HTML <meta http-equiv="Content-Type"> 标签
    4. chardet 库自动检测（如已安装）
    5. 默认返回 utf-8

    Args:
        raw_data: 网页的原始字节数据
        content_type: HTTP 响应头的 Content-Type 值

    Returns:
        检测到的编码名称（如 "utf-8", "gb2312", "iso-8859-1" 等）
    """
    # 1. 从 Content-Type 头获取编码
    charset_match = re.search(r'charset=([\w-]+)', content_type, re.IGNORECASE)
    if charset_match:
        enc = charset_match.group(1).strip()
        try:
            # 验证编码是否有效
            "测试".encode(enc)
            return enc
        except (LookupError, UnicodeEncodeError):
            pass

    # 2. 从 HTML <meta charset> 标签获取编码
    meta_charset = re.search(
        rb'<meta[^>]+charset=["\']?([\w-]+)["\'>]',
        raw_data[:4096],  # 只搜索前 4KB，提高性能
        re.IGNORECASE,
    )
    if meta_charset:
        enc = meta_charset.group(1).decode("ascii", errors="ignore").strip()
        try:
            "测试".encode(enc)
            return enc
        except (LookupError, UnicodeEncodeError):
            pass

    # 3. 从 HTML <meta http-equiv="Content-Type"> 标签获取编码
    http_equiv = re.search(
        rb'<meta[^>]+http-equiv=["\']?Content-Type["\']?[^>]+content=["\']?[^"\']*charset=([\w-]+)',
        raw_data[:4096],
        re.IGNORECASE,
    )
    if http_equiv:
        enc = http_equiv.group(1).decode("ascii", errors="ignore").strip()
        try:
            "测试".encode(enc)
            return enc
        except (LookupError, UnicodeEncodeError):
            pass

    # 4. 尝试使用 chardet 自动检测（可选依赖，优先使用）
    try:
        import chardet
        detected = chardet.detect(raw_data[:10000])  # 检测前 10KB 即可
        if detected and detected["encoding"] and detected["confidence"] > 0.3:
            enc = detected["encoding"]
            try:
                "测试".encode(enc)
                return enc
            except (LookupError, UnicodeEncodeError):
                pass
    except ImportError:
        pass

    # 5. 默认返回 utf-8
    return "utf-8"


def _decode_with_fallback(raw_data: bytes, content_type: str = "") -> str:
    """使用自动检测的编码解码网页字节数据

    先用检测到的编码解码，如果失败则依次尝试常见编码。

    Args:
        raw_data: 网页的原始字节数据
        content_type: HTTP 响应头的 Content-Type 值

    Returns:
        解码后的文本字符串
    """
    # 检测编码
    encoding = _detect_encoding(raw_data, content_type)

    try:
        return raw_data.decode(encoding, errors="replace")
    except (LookupError, UnicodeDecodeError):
        pass

    # 检测到的编码失败时，尝试常见编码
    fallback_encodings = ["utf-8", "gbk", "gb2312", "latin-1", "iso-8859-1", "big5", "shift_jis", "euc-kr"]
    for enc in fallback_encodings:
        if enc.lower() == encoding.lower():
            continue  # 已经尝试过
        try:
            return raw_data.decode(enc, errors="replace")
        except (LookupError, UnicodeDecodeError):
            continue

    # 最后的保底方案
    return raw_data.decode("utf-8", errors="replace")


# ═══════════════════════════════════════════════════════════════
#  缓存管理
# ═══════════════════════════════════════════════════════════════

def _cache_get(key: str) -> Optional[str]:
    """从缓存中获取结果（LRU 策略）"""
    if key not in _search_cache:
        return None
    cached_time, cached_result = _search_cache[key]
    if time.time() - cached_time < _CACHE_TTL:
        # LRU: 移动到末尾（最近使用）
        _search_cache.move_to_end(key)
        return cached_result
    del _search_cache[key]
    return None


def _cache_set(key: str, value: str) -> None:
    """将结果存入缓存（LRU 策略，超出限制时淘汰最久未使用的）"""
    # 如果缓存已满，淘汰最久未使用的
    while len(_search_cache) >= _MAX_CACHE_SIZE:
        _search_cache.popitem(last=False)  # 移除最旧的
    _search_cache[key] = (time.time(), value)


def _get_user_agent(attempt: int = 0) -> str:
    """轮换 User-Agent，避免被识别"""
    return _BACKUP_USER_AGENTS[attempt % len(_BACKUP_USER_AGENTS)]


# ═══════════════════════════════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════════════════════════════

def _make_request(url: str, headers: Optional[dict] = None, timeout: int = 15, attempt: int = 0) -> str:
    """通用 HTTP 请求辅助函数（带自动重试 + 编码自动检测）

    Args:
        url: 请求 URL
        headers: 自定义请求头
        timeout: 超时时间（秒）
        attempt: 当前重试次数（内部使用）

    Returns:
        响应文本（自动检测编码，解决乱码问题）

    Raises:
        HTTPError: HTTP 请求失败
        URLError: 网络连接失败
    """
    req_headers = _DEFAULT_HEADERS.copy()
    req_headers["User-Agent"] = _get_user_agent(attempt)
    if headers:
        req_headers.update(headers)

    req = Request(url, headers=req_headers)
    try:
        with urlopen(req, timeout=timeout) as response:
            # 读取原始字节数据
            raw_data = response.read()
            # 获取 Content-Type 头中的编码信息
            content_type = response.headers.get("Content-Type", "")
            # 使用自动编码检测解码
            return _decode_with_fallback(raw_data, content_type)
    except (HTTPError, URLError) as e:
        if attempt < _MAX_RETRIES:
            # 等待后重试（指数退避）
            time.sleep(1.0 * (attempt + 1))
            return _make_request(url, headers, timeout, attempt + 1)
        raise


def _deduplicate_results(
    results: list[dict],
    url_key: str = "href",
    title_key: str = "title",
) -> list[dict]:
    """对搜索结果去重（基于 URL 和标题相似度）"""
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    deduplicated = []

    for r in results:
        url = (r.get(url_key) or "").strip().rstrip("/")
        title = (r.get(title_key) or "").strip().lower()

        if url and url in seen_urls:
            continue
        if title and len(title) > 5 and title in seen_titles:
            continue

        if url:
            seen_urls.add(url)
        if title and len(title) > 5:
            seen_titles.add(title)

        deduplicated.append(r)

    return deduplicated


def _truncate(text: str, max_len: int = 300) -> str:
    """截断文本到指定长度"""
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def _extract_date_timestamp(r: dict) -> float:
    """从结果字典中提取日期时间戳"""
    date_str = r.get("date") or r.get("pubDate") or ""
    if not date_str:
        return 0.0
    for fmt in [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S",
        "%m/%d/%Y",
    ]:
        try:
            return time.mktime(time.strptime(date_str[:19], fmt))
        except (ValueError, IndexError):
            continue
    return 0.0


def _format_search_results(
    query: str,
    results: list[dict],
    source: str = "",
    total_count: Optional[int] = None,
    time_info: str = "",
    related_searches: Optional[list[str]] = None,
) -> str:
    """统一的搜索结果格式化输出"""
    count = total_count or len(results)
    lines = [f"🔍 搜索「{query}」的结果"]

    if source:
        lines[0] += f" [来源: {source}]"
    if time_info:
        lines[0] += f" ({time_info})"

    lines.append(f"共找到 {count} 条结果：\n")

    for i, r in enumerate(results, 1):
        title = (r.get("title") or "无标题").strip()
        link = r.get("href") or r.get("url") or "无链接"
        snippet = (r.get("body") or r.get("snippet") or "").strip()
        date_str = r.get("date") or r.get("pubDate") or ""

        snippet = _truncate(snippet, 300)

        lines.append(f"{'─' * 60}")
        lines.append(f"  📌 {title}")
        lines.append(f"     🔗 {link}")
        if date_str:
            lines.append(f"     📅 {date_str}")
        if snippet:
            lines.append(f"     📝 {snippet}")
        lines.append("")

    # 相关搜索建议
    if related_searches:
        lines.append(f"{'═' * 60}")
        lines.append("💡 相关搜索：")
        for j, suggestion in enumerate(related_searches, 1):
            lines.append(f"   {j}. {suggestion}")
        lines.append("")

    if results:
        lines.append(f"{'═' * 60}")

    return "\n".join(lines)


def _merge_and_sort_results(
    results_list: list[list[dict]],
    sort_by: str = "relevance",
    max_results: int = 10,
    deduplicate: bool = True,
) -> list[dict]:
    """合并多个来源的结果并排序

    Args:
        results_list: 多个来源的结果列表
        sort_by: 排序方式（"relevance" 按相关性/"time" 按时间）
        max_results: 最大返回结果数
        deduplicate: 是否对结果去重

    Returns:
        合并排序后的结果列表
    """
    merged = []
    for results in results_list:
        merged.extend(results)

    if deduplicate:
        merged = _deduplicate_results(merged)

    if sort_by == "time":
        merged.sort(key=_extract_date_timestamp, reverse=True)

    return merged[:max_results]


def _parse_related_searches(html: str, engine: str = "bing") -> list[str]:
    """从搜索结果页面提取相关搜索建议"""
    suggestions = []

    if engine == "bing":
        # Bing 相关搜索
        patterns = [
            r'<a[^>]*class="[^"]*b_rs[^"]*"[^>]*>(.*?)</a>',
            r'<li[^>]*class="[^"]*b_rs[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>',
            r'<a[^>]*href="[^"]*"[^>]*aria-label="[^"]*"[^>]*>.*?<span[^>]*>(.*?)</span>',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            if matches:
                suggestions = [re.sub(r"<[^>]+>", "", m).strip() for m in matches]
                suggestions = [s for s in suggestions if s and len(s) > 2]
                if suggestions:
                    break

    elif engine == "duckduckgo":
        pattern = r'<a[^>]*class="[^"]*result--suggestion[^"]*"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL)
        suggestions = [re.sub(r"<[^>]+>", "", m).strip() for m in matches]

    elif engine == "google":
        pattern = r'<a[^>]*aria-label="[^"]*"[^>]*><div[^>]*class="[^"]*[Ss]uggestion[^"]*"[^>]*>(.*?)</div>'
        matches = re.findall(pattern, html, re.DOTALL)
        if not matches:
            pattern = r'<div[^>]*class="[^"]*[Ss]uggestion[^"]*"[^>]*>(.*?)</div>'
            matches = re.findall(pattern, html, re.DOTALL)
        suggestions = [re.sub(r"<[^>]+>", "", m).strip() for m in matches]

    # 去重和过滤
    seen = set()
    unique = []
    for s in suggestions:
        if s and len(s) > 2 and s not in seen:
            seen.add(s)
            unique.append(s)

    return unique[:8]  # 最多返回8个


# ═══════════════════════════════════════════════════════════════
#  Google 搜索引擎（新增！）
# ═══════════════════════════════════════════════════════════════

def _fetch_google_search(query: str, num_results: int = 10, language: str = "zh") -> str:
    """通过 Google HTML 页面获取搜索结果"""
    gl = _GOOGLE_GL.get(language, "cn")
    hl = language if language in _GOOGLE_GL else "zh-CN"
    params = {
        "q": query,
        "num": min(num_results, 20),
        "hl": hl,
        "gl": gl,
        "source": "lnms",
    }
    url = "https://www.google.com/search?" + urlencode(params)
    return _make_request(url, timeout=15)


def _parse_google_results(html: str, max_results: int) -> list[dict]:
    """从 Google HTML 中解析搜索结果"""
    results = []

    # Google 搜索结果块匹配
    # 方法1: 匹配 g 标签（Google 搜索结果的标准容器）
    block_pattern = re.compile(
        r'<div[^>]*class="[^"]*g[^"]*"[^>]*>(.*?)</div>\s*(?:</div>)?',
        re.DOTALL,
    )

    for block_match in block_pattern.finditer(html):
        block_html = block_match.group(0)

        # 提取标题和链接
        title_link_match = re.search(
            r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
            block_html,
            re.DOTALL,
        )
        if not title_link_match:
            continue

        link = title_link_match.group(1)
        title = re.sub(r"<[^>]+>", "", title_link_match.group(2)).strip()

        # 过滤掉无效结果
        if not title or not link or "google.com" in link:
            continue

        # 过滤掉广告
        if any(ad_word in block_html.lower() for ad_word in ["ad", "赞助", "广告"]):
            continue

        # 提取摘要
        snippet = ""
        snippet_match = re.search(
            r'<div[^>]*class="[^"]*(?:VwiC3b|BNeawe|snippet)[^"]*"[^>]*>(.*?)</div>',
            block_html,
            re.DOTALL,
        )
        if snippet_match:
            snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip()
            snippet = re.sub(r"\s+", " ", snippet)

        # 提取日期（如果有）
        date_str = ""
        date_match = re.search(
            r'<span[^>]*class="[^"]*[Dd]ate[^"]*"[^>]*>(.*?)</span>',
            block_html,
            re.DOTALL,
        )
        if date_match:
            date_str = re.sub(r"<[^>]+>", "", date_match.group(1)).strip()

        results.append({
            "title": title,
            "href": link,
            "body": snippet,
            "date": date_str,
        })

        if len(results) >= max_results:
            break

    return results


# ═══════════════════════════════════════════════════════════════
#  Bing 搜索引擎
# ═══════════════════════════════════════════════════════════════

def _fetch_bing_search(query: str, num_results: int = 10, market: str = "zh-CN") -> str:
    """通过 Bing HTML 页面获取搜索结果"""
    params = {
        "q": query,
        "count": min(num_results, 20),
        "mkt": market,
    }
    url = "https://www.bing.com/search?" + urlencode(params)
    return _make_request(url)


def _parse_bing_results(html: str, max_results: int) -> list[dict]:
    """从 Bing HTML 中解析搜索结果"""
    results = []

    h2_link_pattern = re.compile(
        r'<h2[^>]*>.*?<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>.*?</h2>',
        re.DOTALL | re.IGNORECASE,
    )

    for m in h2_link_pattern.finditer(html):
        link = m.group(1)
        title = re.sub(r"<[^>]+>", "", m.group(2)).strip()

        if not title or not link:
            continue

        snippet = ""
        after_h2 = html[m.end() : m.end() + 2000]
        snippet_match = re.search(r'<p[^>]*>(.*?)</p>', after_h2, re.DOTALL)
        if snippet_match:
            snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip()
            snippet = re.sub(r"\s+", " ", snippet)
            snippet = snippet.replace("&ensp;", " ").replace("&#0183;", "·")

        results.append({"title": title, "href": link, "body": snippet})
        if len(results) >= max_results:
            break

    return results


# ═══════════════════════════════════════════════════════════════
#  DuckDuckGo 搜索引擎
# ═══════════════════════════════════════════════════════════════

def _fetch_duckduckgo_search(query: str, num_results: int = 10) -> str:
    """通过 DuckDuckGo HTML 页面获取搜索结果"""
    params = {"q": query}
    url = "https://html.duckduckgo.com/html/?" + urlencode(params)
    return _make_request(url, timeout=20)


def _parse_duckduckgo_results(html: str, max_results: int) -> list[dict]:
    """从 DuckDuckGo HTML 中解析搜索结果"""
    results = []

    result_blocks = re.finditer(
        r'<div[^>]*class="result[^"]*result[^"]*"[^>]*>.*?</div>\s*</div>\s*</div>',
        html,
        re.DOTALL,
    )

    for block in result_blocks:
        block_html = block.group(0)

        title_match = re.search(
            r'<a[^>]*class="result__a"[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
            block_html,
            re.DOTALL,
        )
        if not title_match:
            continue

        link = title_match.group(1)
        title = re.sub(r"<[^>]+>", "", title_match.group(2)).strip()

        if not title or not link:
            continue

        snippet = ""
        snippet_match = re.search(
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            block_html,
            re.DOTALL,
        )
        if snippet_match:
            snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip()
            snippet = re.sub(r"\s+", " ", snippet)

        if link.startswith("//"):
            link = "https:" + link
        if "uddg.duckduckgo.com" in link:
            redirect_match = re.search(r"uddg=([^&]+)", link)
            if redirect_match:
                original_url = unquote(redirect_match.group(1))
                if original_url.startswith("http"):
                    link = original_url

        results.append({"title": title, "href": link, "body": snippet})
        if len(results) >= max_results:
            break

    return results


# ═══════════════════════════════════════════════════════════════
#  百度搜索引擎（新增！）
# ═══════════════════════════════════════════════════════════════

def _fetch_baidu_search(query: str, num_results: int = 10) -> str:
    """通过百度 HTML 页面获取搜索结果（免费，无需 API Key）
    
    备用 API（需要申请百度搜索API服务）：
    - API名称: 百度搜索API（Baidu Search API）
    - API文档: https://aip.baidubce.com/rest/2.0/solution/v1/search
    - 认证方式: Access Token（需在百度AI平台申请）
    - Base URL: https://aip.baidubce.com/rest/2.0/solution/v1/search
    
    Args:
        query: 搜索关键词
        num_results: 期望的结果数量
        
    Returns:
        搜索结果的 HTML 文本
    """
    # 百度每页显示10条，计算需要的页数
    pn = max(0, (num_results - 1) // 10 * 10)
    params = {
        "wd": query,
        "pn": pn,
        "rn": min(num_results, 10),
    }
    url = "https://www.baidu.com/s?" + urlencode(params)
    
    # 使用百度专用请求头（百度对 UA 较为敏感）
    baidu_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.baidu.com/",
        "Connection": "keep-alive",
    }
    
    return _make_request(url, headers=baidu_headers, timeout=15)


def _parse_baidu_results(html: str, max_results: int) -> list[dict]:
    """从百度 HTML 中解析搜索结果
    
    Args:
        html: 百度搜索结果页的 HTML
        max_results: 最大返回结果数
        
    Returns:
        解析后的结果列表，每项包含 title/href/body
    """
    results = []
    
    # 百度搜索结果在 class="result" 或 class="c-container" 的 div 中
    # 方法1: 匹配 c-container（新版百度）
    container_pattern = re.compile(
        r'<div[^>]*class="[^"]*c-container[^"]*"[^>]*>(.*?)</div>\s*</div>',
        re.DOTALL,
    )
    
    # 方法2: 匹配 result 容器（旧版百度或简化版）
    if not results:
        container_pattern = re.compile(
            r'<div[^>]*class="[^"]*result[^"]*"[^>]*>(.*?)</div>\s*</div>',
            re.DOTALL,
        )
    
    for block_match in container_pattern.finditer(html):
        block_html = block_match.group(0)
        
        # 提取标题和链接
        # 百度结果标题通常在 <h3> 内的 <a> 标签中
        title_link_match = re.search(
            r'<h3[^>]*>.*?<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>.*?</h3>',
            block_html,
            re.DOTALL,
        )
        
        if not title_link_match:
            # 备用：直接匹配 a 标签
            title_link_match = re.search(
                r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                block_html,
                re.DOTALL,
            )
        
        if not title_link_match:
            continue
            
        link = title_link_match.group(1)
        title = re.sub(r"<[^>]+>", "", title_link_match.group(2)).strip()
        
        # 过滤掉百度自身的链接和广告
        if not title or not link:
            continue
        if any(skip in link for skip in ["baidu.com/link?", "baidu.com/s?", "www.baidu.com"]):
            continue
        if "广告" in title or "ad" in block_html.lower():
            continue
        
        # 提取摘要
        snippet = ""
        
        # 方法1: class="c-abstract"（新版）
        snippet_match = re.search(
            r'<div[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</div>',
            block_html,
            re.DOTALL,
        )
        
        if not snippet_match:
            # 方法2: class="content-right_8Zs40" 或摘要文本
            snippet_match = re.search(
                r'<span[^>]*class="[^"]*content-right[^"]*"[^>]*>(.*?)</span>',
                block_html,
                re.DOTALL,
            )
        
        if not snippet_match:
            # 方法3: 提取 <div class="c-span-last"> 中的文本
            snippet_match = re.search(
                r'<div[^>]*class="[^"]*c-span-last[^"]*"[^>]*>(.*?)</div>',
                block_html,
                re.DOTALL,
            )
        
        if snippet_match:
            snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip()
            snippet = re.sub(r"\s+", " ", snippet)
            # 清理百度特有的 HTML 实体
            snippet = snippet.replace("&ensp;", " ").replace("&emsp;", " ")
            snippet = snippet.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
        
        # 百度结果中的日期（通常在摘要开头，如 "2024年6月20日 - "）
        date_str = ""
        if snippet:
            date_match = re.match(r'(\d{4}年\d{1,2}月\d{1,2}日)\s*[-–—]?\s*', snippet)
            if date_match:
                date_str = date_match.group(1)
                # 从摘要中移除日期前缀
                snippet = snippet[date_match.end():]
        
        results.append({
            "title": title,
            "href": link,
            "body": snippet.strip(),
            "date": date_str,
        })
        
        if len(results) >= max_results:
            break
    
    # 如果两种方法都没找到，尝试最后的备用方案：匹配所有带链接的 h3
    if not results:
        h3_pattern = re.compile(
            r'<h3[^>]*>.*?<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>.*?</h3>',
            re.DOTALL,
        )
        for m in h3_pattern.finditer(html):
            link = m.group(1)
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if title and link and "baidu.com" not in link:
                # 尝试提取附近的摘要
                after_h3 = html[m.end(): m.end() + 1500]
                snippet = ""
                for p_pattern in [r'<div[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</div>',
                                  r'<span[^>]*class="[^"]*content-right[^"]*"[^>]*>(.*?)</span>',
                                  r'<p[^>]*>(.*?)</p>']:
                    p_match = re.search(p_pattern, after_h3, re.DOTALL)
                    if p_match:
                        snippet = re.sub(r"<[^>]+>", "", p_match.group(1)).strip()
                        break
                
                results.append({
                    "title": title,
                    "href": link,
                    "body": _truncate(snippet, 300) if snippet else "",
                    "date": "",
                })
                if len(results) >= max_results:
                    break
    
    return results


# ═══════════════════════════════════════════════════════════════
#  Bing 新闻搜索引擎
# ═══════════════════════════════════════════════════════════════

def _fetch_bing_news(
    query: str,
    num_results: int = 10,
    time_range: str = "",
    market: str = "zh-CN",
) -> str:
    """通过 Bing News 获取新闻搜索结果"""
    params = {
        "q": query,
        "count": min(num_results, 20),
        "mkt": market,
        "setlang": market[:2],
    }
    if time_range:
        params["qft"] = f"+filterui:date:{time_range}"

    url = "https://www.bing.com/news/search?" + urlencode(params)
    return _make_request(url)


def _parse_bing_news_results(html: str, max_results: int) -> list[dict]:
    """从 Bing News HTML 中解析新闻搜索结果"""
    results = []

    # 主模式：新闻卡片
    news_card_pattern = re.compile(
        r'<a[^>]*class="[^"]*title[^"]*"[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    for m in news_card_pattern.finditer(html):
        link = m.group(1)
        title = re.sub(r"<[^>]+>", "", m.group(2)).strip()

        if not title or not link:
            continue

        snippet = ""
        after_link = html[m.end() : m.end() + 3000]
        snippet_match = re.search(
            r'<div[^>]*class="[^"]*(?:snippet|abstract)[^"]*"[^>]*>(.*?)</div>',
            after_link,
            re.DOTALL,
        )
        if snippet_match:
            snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip()
            snippet = re.sub(r"\s+", " ", snippet)

        date_str = ""
        date_match = re.search(
            r'<span[^>]*class="[^"]*date[^"]*"[^>]*>(.*?)</span>',
            after_link,
            re.DOTALL,
        )
        if date_match:
            date_str = re.sub(r"<[^>]+>", "", date_match.group(1)).strip()

        source = ""
        source_match = re.search(
            r'<span[^>]*class="[^"]*source[^"]*"[^>]*>(.*?)</span>',
            after_link,
            re.DOTALL,
        )
        if source_match:
            source = re.sub(r"<[^>]+>", "", source_match.group(1)).strip()

        results.append({
            "title": title,
            "href": link,
            "body": snippet,
            "date": date_str,
            "source": source,
        })

        if len(results) >= max_results:
            break

    # 备用模式
    if not results:
        alt_pattern = re.compile(
            r'<a[^>]*href="(https?://[^"]+)"[^>]*>.*?<div[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</div>',
            re.DOTALL | re.IGNORECASE,
        )
        for m in alt_pattern.finditer(html):
            link = m.group(1)
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if title and link:
                results.append({"title": title, "href": link, "body": "", "date": "", "source": ""})
                if len(results) >= max_results:
                    break

    return results


# ═══════════════════════════════════════════════════════════════
#  🖼️ 图片搜索引擎（新增！）
# ═══════════════════════════════════════════════════════════════

def _fetch_bing_images(query: str, num_results: int = 10, market: str = "zh-CN") -> str:
    """通过 Bing Images 获取图片搜索结果"""
    params = {
        "q": query,
        "count": min(num_results, 30),
        "mkt": market,
    }
    url = "https://www.bing.com/images/search?" + urlencode(params)
    return _make_request(url)


def _parse_bing_images_results(html: str, max_results: int) -> list[dict]:
    """从 Bing Images HTML 中解析图片搜索结果"""
    results = []

    # 匹配图片卡片
    img_pattern = re.compile(
        r'<a[^>]*class="[^"]*thumb[^"]*"[^>]*href="(https?://[^"]+)"[^>]*>.*?<img[^>]*src="(https?://[^"]+)"[^>]*alt="([^"]*)"',
        re.DOTALL | re.IGNORECASE,
    )

    for m in img_pattern.finditer(html):
        page_url = m.group(1)
        img_url = m.group(2)
        alt_text = m.group(3).strip()

        if not img_url or not page_url:
            continue

        # 获取图片尺寸（可选）
        dimensions = ""
        dim_match = re.search(r'width="(\d+)".*?height="(\d+)"', html[m.start():m.start()+500], re.DOTALL)
        if dim_match:
            dimensions = f"{dim_match.group(1)}×{dim_match.group(2)}"

        results.append({
            "title": alt_text or "无标题",
            "href": page_url,
            "img_url": img_url,
            "body": alt_text or "",
            "dimensions": dimensions,
        })

        if len(results) >= max_results:
            break

    return results


# ═══════════════════════════════════════════════════════════════
#  引擎调度函数
# ═══════════════════════════════════════════════════════════════

def _search_with_engine(
    query: str,
    engine: str,
    max_results: int,
    market: str,
    time_filter: str = "",
) -> tuple[list[dict], str]:
    """使用指定引擎搜索并返回结果

    Args:
        query: 搜索关键词
        engine: 引擎名称
        max_results: 最大结果数
        market: 语言市场代码
        time_filter: 时间过滤器

    Returns:
        (结果列表, 引擎显示名称) 的元组
    """
    engine = engine.lower().strip()

    if engine == "google":
        html = _fetch_google_search(query, max_results, market[:2])
        results = _parse_google_results(html, max_results)
        name = f"Google ({market[:2].upper()})"

    elif engine == "duckduckgo":
        html = _fetch_duckduckgo_search(query, max_results)
        results = _parse_duckduckgo_results(html, max_results)
        name = "DuckDuckGo"

    elif engine == "baidu":
        html = _fetch_baidu_search(query, max_results)
        results = _parse_baidu_results(html, max_results)
        name = "Baidu (中文)"

    elif engine == "bing_news":
        html = _fetch_bing_news(query, max_results, time_filter, market)
        results = _parse_bing_news_results(html, max_results)
        name = f"Bing News ({market[:2].upper()})"

    else:  # bing (default)
        html = _fetch_bing_search(query, max_results, market)
        results = _parse_bing_results(html, max_results)
        name = f"Bing ({market[:2].upper()})"

    return results, name


# ═══════════════════════════════════════════════════════════════
#  🔬 smart_search — 智能搜索（多引擎切换）
# ═══════════════════════════════════════════════════════════════

def smart_search(
    query: str,
    engine: str = "bing",
    max_results: int = 5,
    use_cache: bool = True,
    time_range: Optional[str] = None,
    language: str = "zh",
    show_related: bool = False,
) -> str:
    """🔬 智能搜索 — 支持多引擎切换、时间筛选、语言选择

    在基础搜索之上增强功能，支持切换搜索引擎、按时间范围过滤、
    选择搜索语言市场。新增 Google 引擎和搜索建议功能。

    支持的引擎：
    - "bing"        — Bing 搜索引擎（默认，稳定可靠）
    - "google"      — Google 搜索引擎（全球最大搜索引擎）
    - "duckduckgo"  — DuckDuckGo 搜索引擎（注重隐私）
    - "baidu"       — 百度搜索引擎（中文搜索首选，搜索不到时的备用引擎）
    - "bing_news"   — Bing 新闻搜索（专门针对新闻内容）

    支持的时间范围：
    - None   — 不过滤（默认）
    - "24h"  — 过去24小时
    - "7d"   — 过去7天
    - "30d"  — 过去30天
    - "1y"   — 过去1年

    支持的语言：
    - "zh" — 中文（默认）
    - "en" — 英文
    - "ja" — 日文
    - "ko" — 韩文
    - "fr" — 法文
    - "de" — 德文
    - "es" — 西文

    Args:
        query: 搜索关键词（支持中文）
        engine: 搜索引擎（"bing"/"google"/"duckduckgo"/"baidu"/"bing_news"）
        max_results: 最大返回结果数量（1~20，默认5）
        use_cache: 是否使用缓存（默认 True）
        time_range: 时间范围过滤（None/"24h"/"7d"/"30d"/"1y"）
        language: 搜索语言（"zh"/"en"/"ja"等）
        show_related: 是否显示相关搜索建议（默认 False）

    Returns:
        格式化的搜索结果字符串
    """
    max_results = min(max(max_results, 1), 20)
    market = _LANG_MARKETS.get(language, "zh-CN")

    cache_key = f"smart:{engine}:{query}:{max_results}:{time_range}:{language}"
    if use_cache:
        cached = _cache_get(cache_key)
        if cached:
            return cached + "\n\n（来自缓存）"

    try:
        time_filter = ""
        if time_range and time_range in _TIME_FILTERS:
            time_filter = _TIME_FILTERS[time_range]

        raw_results, source_name = _search_with_engine(
            query, engine, max_results, market, time_filter
        )

        if not raw_results:
            result_msg = f"🔍 搜索「{query}」未找到任何结果（引擎: {engine}）。"
            if use_cache:
                _cache_set(cache_key, result_msg)
            return result_msg

        time_info = _TIME_LABELS.get(time_range, "")

        # 提取相关搜索建议
        related = None
        if show_related:
            try:
                if engine == "google":
                    html = _fetch_google_search(query, 5, language)
                elif engine == "duckduckgo":
                    html = _fetch_duckduckgo_search(query, 5)
                else:
                    html = _fetch_bing_search(query, 5, market)
                related = _parse_related_searches(html, engine)
            except Exception:
                pass

        result_msg = _format_search_results(
            query=query,
            results=raw_results,
            source=source_name,
            total_count=len(raw_results),
            time_info=time_info,
            related_searches=related,
        )

        if use_cache:
            _cache_set(cache_key, result_msg)

        return result_msg

    except HTTPError as e:
        return f"❌ 搜索请求被拒绝 (HTTP {e.code}): 可能是访问过于频繁，请稍后再试。"
    except URLError as e:
        return f"❌ 网络连接失败: {e.reason}。请检查网络连接。"
    except Exception as e:
        return f"❌ 搜索出错: {e}"


# ═══════════════════════════════════════════════════════════════
#  📰 search_news — 新闻搜索
# ═══════════════════════════════════════════════════════════════

def search_news(
    query: str,
    max_results: int = 10,
    language: str = "zh",
    time_period: str = "7d",
    bilingual: bool = False,
) -> str:
    """📰 新闻搜索 — 专门针对时事政治新闻，支持中英文双语

    专为新闻资讯场景设计，自动从 Bing News 获取最新新闻。
    适合搜索时事政治、热点事件等时效性强的信息。

    支持：
    - 按时间范围筛选最新新闻
    - 多语言搜索（中文/英文/日文等）
    - 中英文双语模式（同时搜索中英文来源并合并去重）
    - 自动提取新闻日期和来源

    时间范围：
    - "24h"  — 过去24小时（最新）
    - "7d"   — 过去7天（默认）
    - "30d"  — 过去30天
    - "1y"   — 过去1年

    Args:
        query: 新闻搜索关键词（如"中美关系 最新"）
        max_results: 最大返回结果数量（1~30，默认10）
        language: 新闻语言（"zh"中文/"en"英文等）
        time_period: 时间范围（"24h"/"7d"/"30d"/"1y"）
        bilingual: 是否启用中英文双语搜索（默认 False）

    Returns:
        格式化的新闻搜索结果字符串
    """
    max_results = min(max(max_results, 1), 30)
    time_filter = _TIME_FILTERS.get(time_period, "-7")

    cache_key = f"news:{query}:{max_results}:{time_period}:{language}:{bilingual}"
    if cache_key in _search_cache:
        cached = _cache_get(cache_key)
        if cached:
            return cached + "\n\n（来自缓存）"

    try:
        all_results: list[dict] = []
        sources_used: list[str] = []

        if bilingual:
            zh_html = _fetch_bing_news(query, max_results, time_filter, "zh-CN")
            zh_results = _parse_bing_news_results(zh_html, max_results)
            for r in zh_results:
                r["_lang"] = "中文"
            all_results.extend(zh_results)
            sources_used.append("Bing News (中文)")

            en_html = _fetch_bing_news(query, max_results, time_filter, "en-US")
            en_results = _parse_bing_news_results(en_html, max_results)
            for r in en_results:
                r["_lang"] = "English"
            all_results.extend(en_results)
            sources_used.append("Bing News (English)")

            all_results = _deduplicate_results(all_results)
            all_results.sort(key=_extract_date_timestamp, reverse=True)
            all_results = all_results[:max_results]
            source_name = " + ".join(sources_used)
        else:
            market = _LANG_MARKETS.get(language, "zh-CN")
            html = _fetch_bing_news(query, max_results, time_filter, market)
            all_results = _parse_bing_news_results(html, max_results)
            source_name = f"Bing News ({language.upper()})"

        if not all_results:
            result_msg = f"📰 未找到「{query}」的相关新闻。"
            _cache_set(cache_key, result_msg)
            return result_msg

        time_info = _TIME_LABELS.get(time_period, time_period)
        if bilingual:
            time_info += " · 中英文双语"

        lines = [
            f"📰 新闻搜索「{query}」",
            f"   来源: {source_name} | 时间: {time_info}",
            f"   共找到 {len(all_results)} 条相关新闻\n",
        ]

        for i, r in enumerate(all_results, 1):
            title = (r.get("title") or "无标题").strip()
            link = r.get("href") or "无链接"
            snippet = (r.get("body") or "").strip()
            date_str = r.get("date") or ""
            source = r.get("source") or ""
            lang_tag = r.get("_lang", "")

            snippet = _truncate(snippet, 250)

            lines.append(f"{'─' * 60}")
            title_line = f"  📌 {title}"
            if lang_tag:
                title_line += f" 🌐{lang_tag}"
            lines.append(title_line)
            lines.append(f"     🔗 {link}")
            date_info = []
            if date_str:
                date_info.append(f"📅 {date_str}")
            if source:
                date_info.append(f"🏛️ {source}")
            if date_info:
                lines.append(f"     {' | '.join(date_info)}")
            if snippet:
                lines.append(f"     📝 {snippet}")
            lines.append("")

        if all_results:
            lines.append(f"{'═' * 60}")
            lines.append("💡 提示: 使用 bilingual=True 可同时搜索中英文新闻来源")

        result_msg = "\n".join(lines)
        _cache_set(cache_key, result_msg)

        return result_msg

    except HTTPError as e:
        return f"❌ 新闻搜索请求被拒绝 (HTTP {e.code}): 可能是访问过于频繁，请稍后再试。"
    except URLError as e:
        return f"❌ 网络连接失败: {e.reason}。请检查网络连接。"
    except Exception as e:
        return f"❌ 新闻搜索出错: {e}"


# ═══════════════════════════════════════════════════════════════
#  🔗 aggregate_search — 聚合搜索（多引擎同时搜索）
# ═══════════════════════════════════════════════════════════════

def aggregate_search(
    query: str,
    engines: Optional[list[str]] = None,
    max_results: int = 10,
    deduplicate: bool = True,
    sort_by: str = "relevance",
    language: str = "zh",
    time_range: Optional[str] = None,
) -> str:
    """🔗 聚合搜索 — 多引擎同时搜索，结果去重后按相关性/时间排序

    同时在多个搜索引擎中搜索相同关键词，合并结果后去重，
    并按指定方式排序，获取最全面的信息。

    默认同时搜索 Bing、Google 和 DuckDuckGo，适合需要全面覆盖的场景。

    Args:
        query: 搜索关键词
        engines: 搜索引擎列表，默认 ["bing", "google", "duckduckgo"]
                可选值: "bing", "google", "duckduckgo", "baidu", "bing_news"
        max_results: 最大返回结果数量（1~30，默认10）
        deduplicate: 是否对结果去重（默认 True）
        sort_by: 排序方式（"relevance" 按相关性 / "time" 按时间）
        language: 搜索语言（"zh"/"en"等）
        time_range: 时间范围过滤（None/"24h"/"7d"/"30d"/"1y"）

    Returns:
        格式化的聚合搜索结果字符串
    """
    if engines is None:
        engines = ["bing", "google", "duckduckgo"]

    max_results = min(max(max_results, 1), 30)
    market = _LANG_MARKETS.get(language, "zh-CN")
    time_filter = _TIME_FILTERS.get(time_range, "") if time_range else ""

    cache_key = f"aggregate:{query}:{'-'.join(engines)}:{max_results}:{sort_by}:{language}:{time_range}:{deduplicate}"
    if cache_key in _search_cache:
        cached = _cache_get(cache_key)
        if cached:
            return cached + "\n\n（来自缓存）"

    try:
        all_raw: list[list[dict]] = []
        engine_names: list[str] = []
        errors: list[str] = []

        for engine in engines:
            try:
                raw, name = _search_with_engine(query, engine, max_results, market, time_filter)
                if raw:
                    all_raw.append(raw)
                    engine_names.append(name)
            except Exception as e:
                errors.append(f"{engine}: {e}")

        if not all_raw:
            error_detail = "；".join(errors) if errors else "所有引擎均无结果"
            return f"❌ 聚合搜索「{query}」失败: {error_detail}"

        merged_results = _merge_and_sort_results(
            all_raw,
            sort_by=sort_by,
            max_results=max_results,
            deduplicate=deduplicate,
        )

        source_str = " + ".join(engine_names)
        time_info = _TIME_LABELS.get(time_range, "")

        lines = [
            f"🔗 聚合搜索「{query}」",
            f"   引擎: {source_str} | 排序: {'按时间' if sort_by == 'time' else '按相关性'}",
        ]
        if time_info:
            lines.append(f"   {time_info}")
        lines.append(f"   共找到 {len(merged_results)} 条结果（聚合去重后）\n")

        for i, r in enumerate(merged_results, 1):
            title = (r.get("title") or "无标题").strip()
            link = r.get("href") or r.get("url") or "无链接"
            snippet = (r.get("body") or r.get("snippet") or "").strip()
            date_str = r.get("date") or ""

            snippet = _truncate(snippet, 300)

            lines.append(f"{'─' * 60}")
            lines.append(f"  📌 {title}")
            lines.append(f"     🔗 {link}")
            if date_str:
                lines.append(f"     📅 {date_str}")
            if snippet:
                lines.append(f"     📝 {snippet}")
            lines.append("")

        if merged_results:
            lines.append(f"{'═' * 60}")

        if errors:
            lines.append(f"\n⚠️ 部分引擎出错: {'; '.join(errors)}")

        result_msg = "\n".join(lines)
        _cache_set(cache_key, result_msg)

        return result_msg

    except HTTPError as e:
        return f"❌ 聚合搜索请求被拒绝 (HTTP {e.code}): 可能是访问过于频繁，请稍后再试。"
    except URLError as e:
        return f"❌ 网络连接失败: {e.reason}。请检查网络连接。"
    except Exception as e:
        return f"❌ 聚合搜索出错: {e}"


# ═══════════════════════════════════════════════════════════════
#  🔍 web_search — 原始接口（保持向后兼容）
# ═══════════════════════════════════════════════════════════════

def web_search(
    query: str,
    max_results: int = 5,
    use_cache: bool = True,
) -> str:
    """🔍 通过 Bing 搜索互联网（原始接口，保持兼容）

    完全免费，无需 API Key。通过解析 Bing 搜索页面获取结果。
    这是原始的基础搜索函数，建议新项目使用更强大的 smart_search()。

    Args:
        query: 搜索关键词，支持中文
        max_results: 最大返回结果数量（1~20，默认5）
        use_cache: 是否使用缓存（默认 True，60秒内重复搜索相同关键词直接返回缓存）

    Returns:
        格式化的搜索结果字符串，包含标题、链接和摘要
    """
    cache_key = f"web:{query}:{max_results}"
    if use_cache:
        cached = _cache_get(cache_key)
        if cached:
            return cached + "\n\n（来自缓存）"

    try:
        max_results = min(max(max_results, 1), 20)
        html = _fetch_bing_search(query, num_results=max_results)
        raw_results = _parse_bing_results(html, max_results)

        if not raw_results:
            result_msg = f"🔍 搜索「{query}」未找到任何结果。"
            if use_cache:
                _cache_set(cache_key, result_msg)
            return result_msg

        output_lines = [f"🔍 搜索「{query}」的结果（共 {len(raw_results)} 条）：\n"]
        for i, r in enumerate(raw_results, 1):
            title = r.get("title", "无标题").strip()
            link = r.get("href", "无链接")
            snippet = r.get("body", "").strip()
            snippet = _truncate(snippet, 300)

            output_lines.append(f"{i}. {title}")
            output_lines.append(f"   链接: {link}")
            if snippet:
                output_lines.append(f"   摘要: {snippet}")
            output_lines.append("")

        result_msg = "\n".join(output_lines)

        if use_cache:
            _cache_set(cache_key, result_msg)

        return result_msg

    except HTTPError as e:
        return f"❌ 搜索请求被拒绝 (HTTP {e.code}): 可能是访问过于频繁，请稍后再试。"
    except URLError as e:
        return f"❌ 网络连接失败: {e.reason}。请检查网络连接。"
    except Exception as e:
        return f"❌ 搜索出错: {e}"


# ═══════════════════════════════════════════════════════════════
#  📄 web_search_and_open — 搜索并打开网页（增强版）
# ═══════════════════════════════════════════════════════════════

def web_search_and_open(
    query: str,
    max_results: int = 5,
    fetch_content: bool = True,
    max_content_length: int = 2000,
    result_index: int = 1,
) -> str:
    """📄 搜索并打开网页（增强版，原始接口保持兼容）

    搜索互联网，并可选地获取指定顺序结果的页面正文内容。

    增强功能：
    - 可选择打开第几条结果（不再是强制第一条）
    - 更好的 HTML 内容提取（去除脚本、样式等）
    - 可配置内容获取长度

    Args:
        query: 搜索关键词
        max_results: 最大返回结果数量（默认5）
        fetch_content: 是否获取页面内容（默认 True）
        max_content_length: 最大获取的页面内容长度（默认 2000）
        result_index: 打开第几条结果（从1开始，默认1）

    Returns:
        搜索结果及可选页面内容的字符串
    """
    search_result = web_search(query=query, max_results=max_results, use_cache=False)

    if not fetch_content:
        return search_result

    try:
        # 提取所有链接
        all_links = re.findall(r"链接:\s*(https?://[^\s\n]+)", search_result)
        if not all_links:
            return search_result + "\n\n（无法提取链接以获取页面内容）"

        # 选择要打开的链接
        idx = max(1, min(result_index, len(all_links)))
        first_url = all_links[idx - 1]
        parsed = urlparse(first_url)
        if not parsed.scheme or not parsed.netloc:
            return search_result + "\n\n（链接格式无效，无法获取页面内容）"

        # 获取页面内容（增强版：去除脚本、样式等干扰）
        # 现在 _make_request 已内置编码自动检测功能，可正确解码各种编码的网页
        text = _make_request(first_url, timeout=10)

        # 清理 HTML
        text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<nav[^>]*>.*?</nav>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<footer[^>]*>.*?</footer>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<header[^>]*>.*?</header>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) > max_content_length:
            text = text[:max_content_length] + "..."

        return search_result + f"\n\n📄 第{idx}条结果的页面内容（来自 {first_url}）：\n{text}"

    except HTTPError as e:
        return search_result + f"\n\n（获取页面内容时被拒绝: HTTP {e.code}）"
    except URLError as e:
        return search_result + f"\n\n（无法连接到目标网站: {e.reason}）"
    except Exception as e:
        return search_result + f"\n\n（获取页面内容时出错: {e}）"


# ═══════════════════════════════════════════════════════════════
#  🖼️ search_images — 图片搜索（新增！）
# ═══════════════════════════════════════════════════════════════

def search_images(
    query: str,
    max_results: int = 10,
    language: str = "zh",
    use_cache: bool = True,
) -> str:
    """🖼️ 图片搜索 — 搜索图片并返回结果

    通过 Bing Images 搜索图片，返回图片标题、链接和缩略图地址。

    Args:
        query: 搜索关键词
        max_results: 最大返回结果数量（1~20，默认10）
        language: 搜索语言（"zh"/"en"等）
        use_cache: 是否使用缓存（默认 True）

    Returns:
        格式化的图片搜索结果字符串
    """
    max_results = min(max(max_results, 1), 20)
    market = _LANG_MARKETS.get(language, "zh-CN")

    cache_key = f"images:{query}:{max_results}:{language}"
    if use_cache:
        cached = _cache_get(cache_key)
        if cached:
            return cached + "\n\n（来自缓存）"

    try:
        html = _fetch_bing_images(query, max_results, market)
        raw_results = _parse_bing_images_results(html, max_results)

        if not raw_results:
            result_msg = f"🖼️ 未找到「{query}」的图片结果。"
            if use_cache:
                _cache_set(cache_key, result_msg)
            return result_msg

        lines = [
            f"🖼️ 图片搜索「{query}」的结果",
            f"   来源: Bing Images ({language.upper()})",
            f"   共找到 {len(raw_results)} 张图片\n",
        ]

        for i, r in enumerate(raw_results, 1):
            title = (r.get("title") or "无标题").strip()
            img_url = r.get("img_url") or "无图片链接"
            page_url = r.get("href") or "无页面链接"
            dimensions = r.get("dimensions") or ""

            lines.append(f"{'─' * 60}")
            lines.append(f"  🖼️  [{i}] {title}")
            if dimensions:
                lines.append(f"     📐 {dimensions}")
            lines.append(f"     🔗 缩略图: {img_url}")
            lines.append(f"     🌐 原页面: {page_url}")
            lines.append("")

        if raw_results:
            lines.append(f"{'═' * 60}")

        result_msg = "\n".join(lines)

        if use_cache:
            _cache_set(cache_key, result_msg)

        return result_msg

    except HTTPError as e:
        return f"❌ 图片搜索请求被拒绝 (HTTP {e.code}): 可能是访问过于频繁，请稍后再试。"
    except URLError as e:
        return f"❌ 网络连接失败: {e.reason}。请检查网络连接。"
    except Exception as e:
        return f"❌ 图片搜索出错: {e}"


# ═══════════════════════════════════════════════════════════════
#  💡 search_suggestions — 相关搜索建议（新增！）
# ═══════════════════════════════════════════════════════════════

def search_suggestions(
    query: str,
    engine: str = "bing",
    language: str = "zh",
    use_cache: bool = True,
) -> str:
    """💡 相关搜索建议 — 从搜索结果中提取相关搜索词

    获取与当前搜索关键词相关的搜索建议，帮助用户发现更多相关内容。

    Args:
        query: 搜索关键词
        engine: 搜索引擎（"bing"/"google"/"duckduckgo"）
        language: 搜索语言（"zh"/"en"等）
        use_cache: 是否使用缓存（默认 True）

    Returns:
        格式化的相关搜索建议字符串
    """
    cache_key = f"suggestions:{engine}:{query}:{language}"
    if use_cache:
        cached = _cache_get(cache_key)
        if cached:
            return cached + "\n\n（来自缓存）"

    try:
        html = ""
        if engine == "google":
            html = _fetch_google_search(query, 5, language)
        elif engine == "duckduckgo":
            html = _fetch_duckduckgo_search(query, 5)
        else:
            market = _LANG_MARKETS.get(language, "zh-CN")
            html = _fetch_bing_search(query, 5, market)

        suggestions = _parse_related_searches(html, engine)

        if not suggestions:
            result_msg = f"💡 未找到「{query}」的相关搜索建议。"
            if use_cache:
                _cache_set(cache_key, result_msg)
            return result_msg

        lines = [
            f"💡 搜索「{query}」的相关建议",
            f"   来源: {engine.title()}\n",
        ]

        for i, s in enumerate(suggestions, 1):
            lines.append(f"  {i}. {s}")

        lines.append(f"\n{'═' * 60}")
        lines.append("💡 提示: 尝试用这些关键词搜索更多相关内容")

        result_msg = "\n".join(lines)

        if use_cache:
            _cache_set(cache_key, result_msg)

        return result_msg

    except HTTPError as e:
        return f"❌ 获取搜索建议被拒绝 (HTTP {e.code}): 可能是访问过于频繁，请稍后再试。"
    except URLError as e:
        return f"❌ 网络连接失败: {e.reason}。请检查网络连接。"
    except Exception as e:
        return f"❌ 获取搜索建议出错: {e}"


# ═══════════════════════════════════════════════════════════════
#  ⚡ search_engine_status — 搜索引擎健康检查（新增！）
# ═══════════════════════════════════════════════════════════════

def search_engine_status(
    test_query: str = "test",
    timeout: int = 5,
) -> str:
    """⚡ 搜索引擎健康检查 — 检测各搜索引擎可用性

    快速检测 Google、Bing、DuckDuckGo 等搜索引擎的可用状态，
    返回哪些引擎可以正常使用。

    Args:
        test_query: 用于测试的搜索词（默认 "test"）
        timeout: 每个引擎的超时时间（秒，默认5）

    Returns:
        格式化的引擎状态报告
    """
    engines_to_test = {
        "Google": {
            "fetch_fn": lambda: _fetch_google_search(test_query, 1, "zh"),
            "parse_fn": lambda h: len(_parse_google_results(h, 1)) > 0,
        },
        "Bing": {
            "fetch_fn": lambda: _fetch_bing_search(test_query, 1, "zh-CN"),
            "parse_fn": lambda h: len(_parse_bing_results(h, 1)) > 0,
        },
        "DuckDuckGo": {
            "fetch_fn": lambda: _fetch_duckduckgo_search(test_query, 1),
            "parse_fn": lambda h: len(_parse_duckduckgo_results(h, 1)) > 0,
        },
        "Bing News": {
            "fetch_fn": lambda: _fetch_bing_news(test_query, 1, "", "zh-CN"),
            "parse_fn": lambda h: len(_parse_bing_news_results(h, 1)) > 0,
        },
        "Baidu": {
            "fetch_fn": lambda: _fetch_baidu_search(test_query, 1),
            "parse_fn": lambda h: len(_parse_baidu_results(h, 1)) > 0,
        },
    }

    lines = [
        "⚡ 搜索引擎健康检查",
        f"   测试查询: 「{test_query}」\n",
    ]

    all_ok = True
    for name, engine in engines_to_test.items():
        try:
            start = time.time()
            html = engine["fetch_fn"]()
            elapsed = f"{time.time() - start:.1f}s"
            has_results = engine["parse_fn"](html)
            if has_results:
                lines.append(f"  ✅ {name:15s} | 正常 | 响应时间: {elapsed}")
            else:
                lines.append(f"  ⚠️  {name:15s} | 可访问但无结果 | 响应时间: {elapsed}")
                all_ok = False
        except HTTPError as e:
            lines.append(f"  ❌ {name:15s} | 请求被拒绝 (HTTP {e.code})")
            all_ok = False
        except URLError as e:
            lines.append(f"  ❌ {name:15s} | 网络连接失败: {e.reason}")
            all_ok = False
        except Exception as e:
            lines.append(f"  ❌ {name:15s} | 错误: {str(e)[:50]}")
            all_ok = False

    lines.append(f"\n{'═' * 60}")
    if all_ok:
        lines.append("✅ 所有搜索引擎均正常工作")
    else:
        lines.append("⚠️ 部分搜索引擎异常，建议稍后重试")

    return "\n".join(lines)
