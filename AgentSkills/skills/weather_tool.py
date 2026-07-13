"""
weather_tool.py - 天气查询工具（WeatherAgent）

提供查询任意城市未来天气信息的功能。
通过联网搜索获取天气数据，解析并返回格式化的天气报告。
支持：天气预报、穿衣建议、生活小提示。
"""

import re
import json
import urllib.request
import urllib.parse
from typing import Optional


# ── 默认请求头 ──
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _extract_city(task: str) -> Optional[str]:
    """从任务描述中提取城市名称

    支持的匹配模式：
    - "查询/搜索/查一下/看看 北京 的天气"
    - "北京 天气预报/天气"
    - "天气/气温 上海"
    - "Tokyo/London/New York 天气"

    Args:
        task: 任务描述字符串

    Returns:
        提取到的城市名称，未找到返回 None
    """
    # 去除多余空白
    task = task.strip()

    # 模式1: "查询/搜索/查一下/看看/告诉我 X 的天气/气温/温度"
    patterns = [
        r'(?:查询|搜索|查一下|看看|告诉我|请问|帮我看下|帮我查下|帮我查查)\s*(.+?)\s*(?:的?\s*(?:天气|气温|温度|预报|气候))',
        r'(?:天气|气温|温度|预报|气候)\s*(?:查询|搜索|情况)?\s*(.+?)(?:的|$)',
        r'(.+?)\s*(?:的)?\s*(?:天气|气温|温度|预报|气候)',
        r'(?:查询|搜索|查)\s*(.+?)\s*(?:天气|气温|温度)',
    ]

    for pattern in patterns:
        match = re.search(pattern, task)
        if match:
            city = match.group(1).strip()
            # 过滤掉常见的非城市词
            if city and len(city) <= 20 and city not in ("什么", "如何", "怎么", "哪里"):
                return city

    # 模式2: 如果以上都没匹配到，直接用整个字符串作为城市名（去掉常见前缀后缀）
    city = task.strip()
    for prefix in ["查询", "搜索", "查一下", "看看", "告诉我", "请问", "帮我看下", "帮我查下", "帮我查查"]:
        if city.startswith(prefix):
            city = city[len(prefix):].strip()
    for suffix in ["的天气", "天气", "气温", "温度", "预报", "气候", "怎么样", "怎样", "如何"]:
        if city.endswith(suffix):
            city = city[:-len(suffix)].strip()
    if city and len(city) <= 20:
        return city

    return None


def _fetch_weather_data(city: str) -> str:
    """通过联网搜索获取城市天气数据

    使用 urllib.request 搜索 "{city} 天气预报"，解析返回的 HTML 片段。

    Args:
        city: 城市名称

    Returns:
        HTML 文本内容
    """
    query = f"{city} 天气预报 未来7天"
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.bing.com/search?q={encoded_query}&count=5"

    req = urllib.request.Request(url, headers=_DEFAULT_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as response:
        raw_data = response.read()
        # 自动检测编码
        content_type = response.headers.get("Content-Type", "")
        try:
            text = raw_data.decode("utf-8", errors="replace")
        except Exception:
            text = raw_data.decode("gbk", errors="replace")
        return text


def _parse_weather_info(html: str, city: str) -> dict:
    """从搜索结果 HTML 中提取天气信息

    Args:
        html: 搜索结果的 HTML 文本
        city: 城市名称

    Returns:
        包含天气信息的字典
    """
    weather_info = {
        "city": city,
        "temperature": "",
        "condition": "",
        "humidity": "",
        "wind": "",
        "summary": "",
        "forecast": [],
        "tips": [],
        "source": "Bing 搜索",
    }

    # 从搜索结果片段中提取天气关键词
    # 移除脚本和样式内容
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)

    # 提取所有可见文本
    text = re.sub(r'<[^>]+>', ' ', cleaned)
    text = re.sub(r'\s+', ' ', text).strip()

    # 提取温度信息 (如 25°C, 25℃, 25°F, -5°C 等)
    temp_pattern = r'(-?\d{1,2}[°度]?[CFcf℃℉]?)'
    temps = re.findall(temp_pattern, text)
    if temps:
        # 取最常见的温度值
        temp_list = [t for t in temps if any(c in t for c in '°℃℉CFcf') or t.strip('-').isdigit()]
        if temp_list:
            weather_info["temperature"] = " / ".join(temp_list[:4])

    # 提取天气状况关键词
    conditions = []
    condition_keywords = [
        '晴', '多云', '阴', '小雨', '中雨', '大雨', '暴雨', '雷阵雨', '阵雨',
        '小雪', '中雪', '大雪', '暴雪', '雨夹雪', '雾', '霾', '霜', '冰雹',
        '晴转多云', '多云转晴', '阴转晴', '晴转阴',
        'sunny', 'cloudy', 'rain', 'rainy', 'snow', 'snowy', 'fog', 'foggy',
        'clear', 'overcast', 'drizzle', 'thunderstorm', 'windy',
        'partly cloudy', 'mostly cloudy',
    ]
    for keyword in condition_keywords:
        if keyword in text:
            conditions.append(keyword)
    weather_info["condition"] = "、".join(conditions[:3]) if conditions else "未知"

    # 提取湿度
    humidity_match = re.search(r'湿度[：:为约]?\s*(\d{1,3})\s*%', text)
    if humidity_match:
        weather_info["humidity"] = f"{humidity_match.group(1)}%"

    # 提取风力
    wind_patterns = [
        r'(风力|风速|风级)[：:为约]?\s*(\d{1,2})\s*[级级]',
        r'(\d{1,2})\s*[级级]\s*(?:风力|风速|风)',
        r'(东北风|东南风|西北风|西南风|东风|南风|西风|北风|微风|无风)',
    ]
    for pattern in wind_patterns:
        wind_match = re.search(pattern, text)
        if wind_match:
            weather_info["wind"] = wind_match.group(0).strip()
            break

    # 提取搜索结果摘要作为概要
    snippets = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
    for snippet in snippets:
        clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
        if city in clean_snippet and len(clean_snippet) < 500:
            weather_info["summary"] = clean_snippet
            break

    # 如果没有找到摘要，提取所有相关文本片段
    if not weather_info["summary"]:
        sentences = re.split(r'[。！？\n]', text)
        relevant = [s.strip() for s in sentences if city in s and len(s.strip()) > 5]
        if relevant:
            weather_info["summary"] = "。".join(relevant[:3]) + "。"

    # 生活小提示 (基于天气状况生成)
    tips = _generate_life_tips(weather_info["condition"], weather_info["temperature"])
    weather_info["tips"] = tips

    return weather_info


def _generate_life_tips(condition: str, temperature: str) -> list[str]:
    """根据天气状况生成生活小提示

    Args:
        condition: 天气状况描述
        temperature: 温度信息

    Returns:
        生活提示列表
    """
    tips = []

    # 提取温度数值
    temps = re.findall(r'-?\d{1,2}', temperature)
    max_temp = None
    min_temp = None
    if len(temps) >= 2:
        nums = [int(t) for t in temps]
        max_temp = max(nums)
        min_temp = min(nums)
    elif len(temps) == 1:
        max_temp = int(temps[0])

    # 高温提示
    if max_temp is not None and max_temp >= 35:
        tips.append("🌡️ 高温预警：注意防暑降温，尽量避免午后外出")
        tips.append("☀️ 出门请做好防晒，多补充水分")
    elif max_temp is not None and max_temp >= 30:
        tips.append("🌡️ 气温较高，注意防晒和补水")
        tips.append("👕 建议穿着轻薄透气的衣物")

    # 低温提示
    if min_temp is not None and min_temp <= 0:
        tips.append("🥶 低温冰冻：注意保暖防寒，路面可能结冰")
        tips.append("🧣 建议穿着羽绒服、围巾和手套")
    elif min_temp is not None and min_temp <= 5:
        tips.append("🥶 气温较低，注意添衣保暖")

    # 雨天提示
    if any(kw in condition for kw in ['雨', 'rain', 'drizzle', 'thunderstorm']):
        tips.append("☔ 有降雨可能，出门请携带雨具")
        tips.append("🚗 雨天路滑，驾车请注意安全")

    # 雪天提示
    if any(kw in condition for kw in ['雪', 'snow']):
        tips.append("❄️ 有降雪，注意保暖和出行安全")
        tips.append("🚶 雪天地面湿滑，行走时注意防滑")

    # 雾霾提示
    if any(kw in condition for kw in ['雾', '霾', 'fog']):
        tips.append("🌫️ 能见度较低，出行请注意安全")
        tips.append("😷 建议佩戴口罩，减少户外活动")

    # 大风提示
    if any(kw in condition for kw in ['风', 'wind']):
        tips.append("🌬️ 风力较大，注意防风，谨防高空坠物")

    # 晴好天气
    if any(kw in condition for kw in ['晴', 'sunny', 'clear']):
        tips.append("☀️ 天气晴好，适合户外活动和晾晒衣物")

    if not tips:
        tips.append("📌 天气状况较为平稳，适合日常出行和户外活动")

    return tips


def _format_weather_report(weather_info: dict) -> str:
    """将天气信息格式化为可读的天气报告

    Args:
        weather_info: 天气信息字典

    Returns:
        格式化的天气报告字符串
    """
    lines = []
    city = weather_info["city"]

    # 标题
    lines.append(f"🌤️  {city} 天气预报")
    lines.append(f"{'═' * 50}")
    lines.append("")

    # 当前天气概览
    lines.append("📊 当前天气概览")
    lines.append(f"{'─' * 30}")
    if weather_info["temperature"]:
        lines.append(f"   🌡️  温度: {weather_info['temperature']}")
    if weather_info["condition"] and weather_info["condition"] != "未知":
        lines.append(f"   🌤️  状况: {weather_info['condition']}")
    if weather_info["humidity"]:
        lines.append(f"   💧  湿度: {weather_info['humidity']}")
    if weather_info["wind"]:
        lines.append(f"   🌬️  风力: {weather_info['wind']}")
    lines.append("")

    # 详细描述
    if weather_info["summary"]:
        lines.append("📝 天气详情")
        lines.append(f"{'─' * 30}")
        lines.append(f"   {weather_info['summary']}")
        lines.append("")

    # 生活小提示
    if weather_info["tips"]:
        lines.append("💡 生活小提示")
        lines.append(f"{'─' * 30}")
        for tip in weather_info["tips"]:
            lines.append(f"   {tip}")
        lines.append("")

    # 底部
    lines.append(f"{'═' * 50}")
    lines.append(f"📡 数据来源: {weather_info['source']}")
    lines.append("💬 提示: 天气信息仅供参考，请以官方天气预报为准")

    return "\n".join(lines)


def run_weather_agent(task: str) -> str:
    """
    WeatherAgent - 天气查询入口函数

    接收包含城市名称的任务描述，通过联网搜索获取天气信息，
    返回格式化的天气报告。

    Args:
        task: 任务描述，例如：
              - "查询北京的天气"
              - "上海天气预报"
              - "Tokyo 天气怎么样"
              - "帮我查查纽约未来几天的气温"

    Returns:
        格式化的天气报告字符串
    """
    try:
        # 1. 提取城市名称
        city = _extract_city(task)
        if not city:
            return (
                "❌ 无法从任务描述中提取城市名称。\n\n"
                "请提供城市名称，例如：\n"
                "  - \"查询北京的天气\"\n"
                "  - \"上海天气预报\"\n"
                "  - \"Tokyo 天气怎么样\"\n"
                "  - \"帮我查查纽约未来几天的气温\""
            )

        print(f"   🌍 正在查询 {city} 的天气信息...")

        # 2. 搜索天气数据
        html = _fetch_weather_data(city)

        # 3. 解析天气信息
        weather_info = _parse_weather_info(html, city)

        # 4. 格式化输出
        report = _format_weather_report(weather_info)

        return report

    except Exception as e:
        return f"❌ 天气查询失败: {e}\n\n请检查网络连接或稍后重试。"
