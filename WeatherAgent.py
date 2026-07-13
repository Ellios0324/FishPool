#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeatherAgent.py - 智能天气助手

支持两种运行模式：
  1. 命令行模式： python3 WeatherAgent.py --task "查询北京的天气"
  2. 交互式模式： python3 WeatherAgent.py （直接运行进入交互界面）

数据来源：
  主方案：wttr.in (https://wttr.in)
  备用方案：Open-Meteo (https://open-meteo.com)
"""

import argparse
import json
import re
import sys
import textwrap
from datetime import datetime

import requests

# ============================================================
# 天气状况编码 -> 中文描述 + 表情符号
# 参考：https://www.worldweatheronline.com/developer/api/docs/weather-icons.aspx
# ============================================================
WEATHER_CODE_MAP = {
    113: ("晴天", "☀️"),
    116: ("多云", "⛅"),
    119: ("阴天", "☁️"),
    122: ("阴天", "☁️"),
    143: ("雾", "🌫️"),
    149: ("烟霾", "🌫️"),       # Smoky haze
    176: ("零星小雨", "🌦️"),
    179: ("零星小雪", "🌨️"),
    182: ("零星雨夹雪", "🌧️"),
    185: ("冻雨", "🌧️"),
    200: ("雷阵雨", "⛈️"),
    227: ("吹雪", "🌨️"),
    230: ("暴风雪", "❄️"),
    248: ("雾", "🌫️"),
    260: ("冻雾", "🌫️"),
    263: ("毛毛雨", "🌦️"),
    266: ("毛毛雨", "🌦️"),
    281: ("冻毛毛雨", "🌧️"),
    284: ("强冻毛毛雨", "🌧️"),
    293: ("小雨", "🌦️"),
    296: ("小雨", "🌦️"),
    299: ("中雨", "🌧️"),
    302: ("中雨", "🌧️"),
    305: ("大雨", "🌧️"),
    308: ("暴雨", "🌧️"),
    311: ("冻雨", "🌧️"),
    314: ("中到大冻雨", "🌧️"),
    317: ("小冰雹", "🌨️"),
    320: ("中到大冰雹", "🌨️"),
    323: ("小雪", "🌨️"),
    326: ("小雪", "🌨️"),
    329: ("中雪", "🌨️"),
    332: ("中雪", "🌨️"),
    335: ("大雪", "❄️"),
    338: ("暴雪", "❄️"),
    350: ("冰粒", "🌨️"),
    353: ("阵雨", "🌦️"),
    356: ("中到大阵雨", "🌧️"),
    359: ("大暴雨", "🌧️"),
    362: ("阵雨夹雪", "🌧️"),
    365: ("中到大阵雨夹雪", "🌧️"),
    368: ("阵雪", "🌨️"),
    371: ("中到大阵雪", "❄️"),
    374: ("冰粒阵", "🌨️"),
    377: ("中到大冰粒", "🌨️"),
    392: ("雷阵雨", "⛈️"),
    395: ("雷阵雪", "⛈️"),
}

# 默认天气描述（备用）
DEFAULT_WEATHER_DESC = ("未知天气", "❓")

# ============================================================
# 穿衣建议规则
# ============================================================
CLOTHING_ADVICE = [
    (30, float("inf"), "短袖、短裤、防晒衣、帽子、墨镜 🧢🕶️"),
    (20, 30, "短袖/薄长袖、薄外套、牛仔裤 👕"),
    (10, 20, "长袖、外套、卫衣、休闲裤 🧥"),
    (0, 10, "毛衣、厚外套、围巾 🧣"),
    (float("-inf"), 0, "羽绒服、棉服、帽子、手套 🧤"),
]


def get_clothing_advice(temp_c):
    """根据温度给出穿衣建议"""
    for low, high, advice in CLOTHING_ADVICE:
        if low <= temp_c < high or (high == float("inf") and temp_c >= low):
            return advice
    return "请根据实际体感适当增减衣物"


# ============================================================
# 生活 tips 规则
# ============================================================
def get_life_tips(weather_code, max_temp, min_temp, hourly_data, humidity):
    """根据天气状况生成每日生活小提示"""
    tips = []

    # 从 hourly 数据中汇总判断
    has_rain = False
    has_wind = False
    has_fog = False
    max_wind_speed = 0
    max_uv = 0

    for h in hourly_data:
        if h.get("chanceofrain") and int(h.get("chanceofrain", 0)) > 50:
            has_rain = True
        if h.get("chanceofwindy") and int(h.get("chanceofwindy", 0)) > 50:
            has_wind = True
        if h.get("chanceoffog") and int(h.get("chanceoffog", 0)) > 50:
            has_fog = True
        ws = int(h.get("windspeedKmph", 0))
        if ws > max_wind_speed:
            max_wind_speed = ws
        uv = int(h.get("uvIndex", 0))
        if uv > max_uv:
            max_uv = uv

    # 根据 weatherCode 判断
    code = int(weather_code) if weather_code else 0

    # 降雨相关
    rain_codes = {
        176, 179, 182, 185, 200, 263, 266, 281, 284,
        293, 296, 299, 302, 305, 308, 311, 314, 317,
        320, 353, 356, 359, 362, 365, 374, 377, 392, 395,
    }
    if code in rain_codes or has_rain:
        tips.append("🌂 今日有雨，记得带伞")

    # 雪天
    snow_codes = {
        179, 182, 227, 230, 317, 320, 323, 326, 329,
        332, 335, 338, 350, 362, 365, 368, 371, 374,
        377, 395,
    }
    if code in snow_codes:
        tips.append("❄️ 今日有雪，注意防滑保暖")

    # 雾/霾天
    fog_codes = {143, 149, 248, 260}
    if code in fog_codes or has_fog:
        tips.append("😷 有雾/霾，建议佩戴口罩")

    # 晴天（注意防晒）
    sunny_codes = {113}
    if code in sunny_codes and max_uv >= 5:
        tips.append("🧴 紫外线较强，注意防晒")
    elif code in sunny_codes:
        tips.append("☀️ 天气晴好，适合户外活动")

    # 大风
    if has_wind or max_wind_speed > 30:
        tips.append("💨 风力较大，注意防风")
    elif max_wind_speed > 20:
        tips.append("🍃 风稍大，注意保暖")

    # 温差大
    temp_diff = max_temp - min_temp
    if temp_diff >= 12:
        tips.append("🌡️ 昼夜温差大，注意适时增减衣物")
    elif temp_diff >= 8:
        tips.append("🌡️ 早晚较凉，出门带件外套")

    # 湿度
    if humidity is not None:
        try:
            h_val = int(humidity)
            if h_val < 30:
                tips.append("💧 空气干燥，注意多喝水保湿")
            elif h_val > 80:
                tips.append("💦 湿度较高，注意除湿防潮")
        except ValueError:
            pass

    # 高温低温
    if max_temp >= 35:
        tips.append("🥵 高温天气，注意防暑降温")
    elif max_temp <= 0:
        tips.append("🧊 严寒天气，注意保暖防冻")

    if not tips:
        tips.append("✅ 天气不错，祝您心情愉快！")

    return "；".join(tips)


def get_weekday(date_str):
    """根据日期字符串获取星期几"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return weekdays[dt.weekday()]
    except (ValueError, IndexError):
        return ""


def get_weather_info(weather_code):
    """根据天气编码获取中文描述和表情符号"""
    try:
        code = int(weather_code)
        return WEATHER_CODE_MAP.get(code, DEFAULT_WEATHER_DESC)
    except (ValueError, TypeError):
        return DEFAULT_WEATHER_DESC


def parse_weather_from_wttr(city_name, data):
    """解析 wttr.in API 返回的 JSON 数据"""
    weather_days = data.get("weather", [])
    if not weather_days:
        raise ValueError("未找到天气数据")

    results = []
    for day in weather_days[:7]:  # 最多7天
        date = day.get("date", "")
        max_temp = int(day.get("maxtempC", 0))
        min_temp = int(day.get("mintempC", 0))
        avg_temp = int(day.get("avgtempC", 0))

        # 从 hourly 中获取主要时段的天气描述（取 12:00 或 15:00 为代表）
        hourly = day.get("hourly", [])
        desc_value = ""
        weather_code = ""
        humidity_val = None

        # 优先获取午间（12:00）的天气描述
        target_times = ["1200", "1500", "900", "600", "1800"]
        for h in hourly:
            if h.get("time") in target_times:
                weather_code = h.get("weatherCode", "")
                humidity_val = h.get("humidity")
                break

        # 如果目标时段没找到 weatherCode，取第一个有数据的时间段
        if not weather_code:
            for h in hourly:
                weather_code = h.get("weatherCode", "")
                humidity_val = h.get("humidity")
                if weather_code:
                    break

        # 使用 weatherCode 映射为中文描述，确保所有情况都有中文输出
        if weather_code:
            info = get_weather_info(weather_code)
            desc_value = info[0]
            emoji = info[1]
        else:
            desc_value = "未知"
            emoji = "❓"

        # 穿衣建议（取平均温度）
        clothing = get_clothing_advice(avg_temp)

        # 生活提示
        tips = get_life_tips(weather_code, max_temp, min_temp, hourly, humidity_val)

        # 星期几
        weekday = get_weekday(date)

        results.append({
            "date": date,
            "weekday": weekday,
            "description": desc_value,
            "emoji": emoji,
            "max_temp": max_temp,
            "min_temp": min_temp,
            "avg_temp": avg_temp,
            "clothing": clothing,
            "tips": tips,
            "weather_code": weather_code,
        })

    return results


def fetch_weather_wttr(city_name):
    """通过 wttr.in API 获取天气数据"""
    url = f"https://wttr.in/{city_name}?format=j1&lang=zh"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; WeatherAgent/1.0)",
        "Accept": "application/json",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # 检查是否有错误信息
        if "error" in data:
            raise ValueError(f"API 返回错误: {data['error']}")

        if not data.get("weather"):
            raise ValueError(f"未找到城市「{city_name}」的天气数据")

        return parse_weather_from_wttr(city_name, data)

    except requests.exceptions.ConnectionError:
        raise ConnectionError("网络连接失败，请检查网络设置")
    except requests.exceptions.Timeout:
        raise TimeoutError("请求超时，请稍后重试")
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 404:
            raise ValueError(f"未找到城市「{city_name}」的信息")
        raise RuntimeError(f"HTTP 错误: {resp.status_code}")
    except json.JSONDecodeError:
        raise RuntimeError("API 返回数据格式异常")


def display_weather(city_name, weather_list):
    """以美观的格式展示天气数据"""
    if not weather_list:
        print("❌ 没有天气数据可以显示")
        return

    # 标题
    print()
    print("=" * 55)
    print(f"    🌤  {city_name} 未来7天天气预报")
    print("=" * 55)
    print()

    for i, day in enumerate(weather_list, 1):
        date_str = day["date"]
        weekday = day["weekday"]
        desc = day["description"]
        emoji = day["emoji"]
        max_t = day["max_temp"]
        min_t = day["min_temp"]
        clothing = day["clothing"]
        tips = day["tips"]

        # 日期行
        weekday_str = f" ({weekday})" if weekday else ""
        print(f"📅 第{i}天：{date_str}{weekday_str}")

        # 天气
        print(f"   🌡  天气：{desc} {emoji}")
        print(f"   🌡  温度：{min_t}°C ~ {max_t}°C")

        # 穿衣建议（自动换行）
        clothing_wrapped = textwrap.fill(
            f"👗 穿衣建议：{clothing}", width=50,
            subsequent_indent="          "
        )
        print(f"   {clothing_wrapped}")

        # 生活tips（自动换行）
        tips_wrapped = textwrap.fill(
            f"💡 生活tip：{tips}", width=50,
            subsequent_indent="          "
        )
        print(f"   {tips_wrapped}")

        print()  # 空行间隔

    print("=" * 55)
    print()


def fetch_weather_fallback(city_name):
    """备用方案：当 wttr.in 不可用时，使用 Open-Meteo API"""
    # 先通过 Open-Meteo Geocoding API 获取城市坐标
    geo_url = (
        f"https://geocoding-api.open-meteo.com/v1/search?"
        f"name={city_name}&count=5&language=zh&format=json"
    )
    headers = {"User-Agent": "WeatherAgent/1.0"}

    try:
        geo_resp = requests.get(geo_url, headers=headers, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        results = geo_data.get("results", [])
        if not results:
            raise ValueError(f"未找到城市「{city_name}」")

        city_info = results[0]
        lat = city_info["latitude"]
        lon = city_info["longitude"]
        display_name = city_info.get("name", city_name)
        country = city_info.get("country", "")

        print(f"📍 定位到：{display_name}, {country}")

        # 通过 Open-Meteo API 获取7天天气预报
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,weathercode,uv_index_max"
            f"&current_weather=true&timezone=auto&forecast_days=7"
        )

        weather_resp = requests.get(weather_url, headers=headers, timeout=10)
        weather_resp.raise_for_status()
        weather_data = weather_resp.json()

        daily = weather_data.get("daily", {})
        dates = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        weather_codes = daily.get("weathercode", [])
        uv_max = daily.get("uv_index_max", [])

        # Open-Meteo 天气编码与描述的映射
        open_meteo_codes = {
            0: ("晴天", "☀️"),
            1: ("晴间多云", "🌤️"),
            2: ("多云", "⛅"),
            3: ("阴天", "☁️"),
            45: ("雾", "🌫️"),
            48: ("雾凇", "🌫️"),
            51: ("小毛毛雨", "🌦️"),
            53: ("中毛毛雨", "🌦️"),
            55: ("大毛毛雨", "🌦️"),
            56: ("冻毛毛雨", "🌧️"),
            57: ("冻毛毛雨", "🌧️"),
            61: ("小雨", "🌦️"),
            63: ("中雨", "🌧️"),
            65: ("大雨", "🌧️"),
            66: ("冻雨", "🌧️"),
            67: ("冻雨", "🌧️"),
            71: ("小雪", "🌨️"),
            73: ("中雪", "🌨️"),
            75: ("大雪", "❄️"),
            77: ("雪粒", "🌨️"),
            80: ("阵雨", "🌦️"),
            81: ("中阵雨", "🌧️"),
            82: ("大阵雨", "🌧️"),
            85: ("小阵雪", "🌨️"),
            86: ("大阵雪", "❄️"),
            95: ("雷暴", "⛈️"),
            96: ("雷暴+冰雹", "⛈️"),
            99: ("强雷暴+冰雹", "⛈️"),
        }

        result_list = []
        for i in range(min(len(dates), 7)):
            date = dates[i]
            max_t = int(max_temps[i]) if max_temps else 0
            min_t = int(min_temps[i]) if min_temps else 0
            avg_t = (max_t + min_t) // 2
            w_code = int(weather_codes[i]) if i < len(weather_codes) else 0
            uv = uv_max[i] if i < len(uv_max) else 0

            w_info = open_meteo_codes.get(w_code, ("未知", "❓"))
            desc = w_info[0]
            emoji = w_info[1]

            clothing = get_clothing_advice(avg_t)

            # 为 Open-Meteo 生成生活 tips
            tips_parts = []
            rain_codes = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
            if w_code in rain_codes:
                tips_parts.append("🌂 今日有雨，记得带伞")
            snow_codes = {71, 73, 75, 77, 85, 86}
            if w_code in snow_codes:
                tips_parts.append("❄️ 今日有雪，注意防滑保暖")
            if w_code in (45, 48):
                tips_parts.append("😷 有雾/霾，建议佩戴口罩")
            if w_code in (0, 1) and uv >= 5:
                tips_parts.append("🧴 紫外线较强，注意防晒")
            elif w_code in (0, 1):
                tips_parts.append("☀️ 天气晴好，适合户外活动")
            temp_diff = max_t - min_t
            if temp_diff >= 12:
                tips_parts.append("🌡️ 昼夜温差大，注意增减衣物")
            elif temp_diff >= 8:
                tips_parts.append("🌡️ 早晚较凉，出门带件外套")
            if max_t >= 35:
                tips_parts.append("🥵 注意防暑降温")
            if max_t <= 0:
                tips_parts.append("🧊 注意防寒保暖")
            if not tips_parts:
                tips_parts.append("✅ 天气不错，祝您心情愉快！")

            weekday = get_weekday(date)

            result_list.append({
                "date": date,
                "weekday": weekday,
                "description": desc,
                "emoji": emoji,
                "max_temp": max_t,
                "min_temp": min_t,
                "avg_temp": avg_t,
                "clothing": clothing,
                "tips": "；".join(tips_parts),
                "weather_code": str(w_code),
            })

        return result_list

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"备用 API 请求失败: {e}")
    except (KeyError, IndexError, ValueError) as e:
        raise RuntimeError(f"数据解析失败: {e}")


def get_weather(city_name):
    """获取天气数据的主函数，自动切换主/备用方案"""
    city_name = city_name.strip()
    if not city_name:
        print("❌ 城市名不能为空！")
        return None

    # 方案一：wttr.in
    try:
        print(f"🔍 正在查询「{city_name}」的天气...")
        return fetch_weather_wttr(city_name)
    except (ConnectionError, TimeoutError) as e:
        print(f"⚠️ 主API连接失败: {e}")
        print("🔄 正在切换到备用方案...")
    except (ValueError, RuntimeError) as e:
        print(f"⚠️ 主API错误: {e}")
        print("🔄 正在尝试备用方案...")

    # 方案二：Open-Meteo
    try:
        return fetch_weather_fallback(city_name)
    except Exception as e:
        print(f"❌ 备用方案也失败了: {e}")
        print("💡 请检查城市名是否正确，或稍后重试。")
        return None


def print_banner():
    """打印欢迎横幅"""
    banner = r"""
    ╔══════════════════════════════════╗
    ║        🌤  WeatherAgent          ║
    ║      智能天气助手 v1.0            ║
    ╚══════════════════════════════════╝
    """
    print(banner)


def extract_city_from_task(task_text):
    """
    从自然语言任务描述中智能提取城市名。

    支持多种输入格式：
      - "查询北京的天气"          -> 北京
      - "北京的天气"              -> 北京
      - "上海天气"                -> 上海
      - "帮我查一下广州的天气"     -> 广州
      - "东京"                    -> 东京（直接作为城市名）
      - "London weather"          -> London
      - "深圳今天天气怎么样"       -> 深圳
    """
    if not task_text:
        return None

    text = task_text.strip()
    if not text:
        return None

    # ===== 第一步：递归清除常见动词前缀 =====
    # 按长度从长到短排序，优先匹配更长的前缀
    prefixes = [
        '帮我查一下', '帮我查查', '帮我查', '帮我',
        '给我查一下', '给我查查', '给我查', '给我',
        '请查一下', '请查查', '请查', '请',
        '麻烦你查一下', '麻烦你查查', '麻烦你',
        '我想要查一下', '我想要查查', '我想要查', '我想要',
        '我想查一下', '我想查查', '我想查', '我想',
        '我要查一下', '我要查查', '我要查', '我要',
        '能不能查一下', '能不能查查', '能不能查', '能不能',
        '可以查一下', '可以查查', '可以查', '可以',
        '查一下', '查查', '查询', '查',
        '搜索', '搜一下', '搜搜', '搜',
        '看看', '告诉我', '找一下', '找找', '找',
        '有没有', '有',
    ]
    # 去重并排序（按长度降序），确保长前缀优先匹配
    prefixes = sorted(set(prefixes), key=len, reverse=True)

    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                changed = True
                break  # 每轮只移除一个最长匹配前缀

    if not text:
        return task_text

    # ===== 第二步：匹配 "X的天气" 或 "X天气" 模式 =====
    # [^的]+ 匹配不含"的"的字符序列，遇到"的"或结尾停止
    # 后面跟可选的"的" + "天气"
    match = re.search(r'([^的]+?)(?:的)?天气', text)
    if match:
        city = match.group(1).strip()
        if city:
            # 清除城市名中残留在末尾的时间词（如 "深圳今天天气" -> "深圳"）
            city = re.sub(
                r'(今天|明天|后天|昨日|昨晚|这周|下周|现在|目前|'
                r'today|tomorrow|yesterday)$',
                '', city
            ).strip()
            if city:
                return city

    # ===== 第三步：匹配 "今天/明天 X 天气" 等时间+城市组合模式 =====
    match = re.search(
        r'(?:今天|明天|后天|昨日|昨晚|这周|下周|这个星期|下个星期|这周末|下周末|'
        r'today|tomorrow)\s*([\u4e00-\u9fff_a-zA-Z]{2,})',
        text, re.IGNORECASE
    )
    if match:
        city = match.group(1).strip()
        # 确保提取的不是"天气"这类非城市词
        if city and city not in ('天气', 'weather', '温度', '气温'):
            # 清除末尾残留的天气相关后缀
            city = re.sub(r'(天气|怎么样|如何|怎样|情况)$', '', city).strip()
            if city:
                return city

    # ===== 第四步：匹配 "weather in X" / "X weather" 英文模式 =====
    match = re.search(
        r'(?:weather\s+(?:in|for|at|of)\s+)?([a-zA-Z\s]+?)(?:\s+weather)?$',
        text, re.IGNORECASE
    )
    if match:
        city = match.group(1).strip()
        if city and len(city) >= 2:
            return city

    # ===== 第五步：清理常见后缀后直接返回 =====
    text = re.sub(
        r'(?:的天气|天气情况|天气预报|天气怎么样|天气如何|天气|气温|温度|'
        r'情况|怎么样|如何|怎样|情况如何|情况怎么样|'
        r'今天|明天|后天|昨日|昨晚|现在|目前|'
        r'怎么样啊|如何啊|怎样啊)$',
        '', text
    ).strip()

    return text if text else task_text


def run_task(task_text):
    """
    执行单次天气查询任务（--task 模式）。

    返回：True 表示成功，False 表示失败
    """
    try:
        city_name = extract_city_from_task(task_text)
        if not city_name:
            print("❌ 无法从任务描述中提取城市名")
            print(f"   任务内容: {task_text}")
            print("💡 请使用类似格式：--task \"查询北京的天气\"")
            return False

        print(f"📋 任务：{task_text}")
        print(f"🏙️  识别城市：{city_name}")
        print()

        weather_data = get_weather(city_name)

        if weather_data:
            display_weather(city_name, weather_data)
            return True
        else:
            print(f"❌ 无法获取「{city_name}」的天气数据")
            return False

    except Exception as e:
        print(f"❌ 执行任务时发生错误: {e}")
        return False


def main():
    """主函数：支持 --task 命令行模式和交互式模式"""
    parser = argparse.ArgumentParser(
        description="🌤  WeatherAgent - 智能天气助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python3 WeatherAgent.py --task \"查询北京的天气\"\n"
            "  python3 WeatherAgent.py --task \"上海天气\"\n"
            "  python3 WeatherAgent.py                      # 进入交互模式\n"
        )
    )
    parser.add_argument(
        "--task", "-t",
        type=str,
        default=None,
        help="指定天气查询任务，例如：--task \"查询北京的天气\""
    )
    args = parser.parse_args()

    # ========== 模式一：--task 命令行模式 ==========
    if args.task:
        success = run_task(args.task)
        sys.exit(0 if success else 1)

    # ========== 模式二：交互式模式 ==========
    print_banner()
    print("📖 使用说明：输入城市名称查询未来7天天气预报")
    print("   - 支持中文城市名（如：北京、上海、东京、London）")
    print("   - 输入 'exit' 或 'quit' 或 'q' 退出程序")
    print("   - 输入 'clear' 清屏")
    print("   - 支持自然语言输入，如「查询北京的天气」")
    print()

    while True:
        try:
            # 获取用户输入
            user_input = input("🏙️  请输入城市名称 > ").strip()

            if not user_input:
                continue

            # 退出命令
            if user_input.lower() in ("exit", "quit", "q"):
                print("👋 感谢使用 WeatherAgent，再见！")
                break

            # 清屏命令
            if user_input.lower() == "clear":
                print("\033c", end="")
                continue

            # 对于交互式输入，也支持自然语言解析
            city = extract_city_from_task(user_input)

            # 获取天气
            weather_data = get_weather(city)

            if weather_data:
                display_weather(city, weather_data)
            else:
                print()

        except KeyboardInterrupt:
            print("\n\n👋 检测到中断，再见！")
            break
        except Exception as e:
            print(f"❌ 发生未知错误: {e}")
            print("💡 请重试或联系开发者。")
            print()


if __name__ == "__main__":
    main()
