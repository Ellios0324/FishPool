"""
modify_tool.py - 内容优化工具（ModifyAgent）

提供将技术内容针对不同受众进行改写、翻译、格式转换的功能。
基于规则实现文本转换，支持受众适配、格式转换、术语管理等。
"""

import re
from typing import Optional, Callable


# ── 受众类型定义 ──
AUDIENCES = {
    "developer": "面向开发者：保持技术深度，使用专业术语",
    "manager": "面向管理者：关注进度、成本和收益，避免过多技术细节",
    "executive": "面向高管：突出商业价值和战略意义，一句话总结核心",
    "beginner": "面向初学者：用通俗语言，增加示例和类比",
    "customer": "面向客户：聚焦功能收益和使用场景，避免技术细节",
    "non_technical": "面向非技术人员：完全避免术语，用生活化类比",
}

# ── 技术术语库（技术术语 -> 通俗解释）──
_TECH_TERMS = {
    # 编程概念
    "API": "应用程序编程接口（不同程序之间的通信桥梁）",
    "RESTful API": "REST风格接口（一种规范化的网络通信方式）",
    "SDK": "软件开发工具包（让开发者快速集成功能的工具集合）",
    "ORM": "对象关系映射（用编程语言操作数据库的桥梁）",
    "SDLC": "软件开发生命周期（从需求到上线的完整流程）",
    "CI/CD": "持续集成/持续部署（自动构建和发布的流程）",
    "IDE": "集成开发环境（编写代码的软件工具）",
    "CLI": "命令行界面（通过输入命令操作的工具）",
    "GUI": "图形用户界面（有按钮和菜单的交互方式）",
    "JSON": "一种轻量级数据交换格式（类似字典的结构化数据）",
    "XML": "可扩展标记语言（另一种数据格式，类似HTML）",
    "YAML": "一种人类可读的数据序列化格式（常用于配置文件）",
    "SQL": "结构化查询语言（和数据库对话的标准语言）",
    "NoSQL": "非关系型数据库（灵活存储非结构化数据的数据库）",
    "HTTP": "超文本传输协议（浏览器和服务器通信的规则）",
    "HTTPS": "安全的超文本传输协议（加密版的HTTP）",
    "TCP": "传输控制协议（确保数据可靠传输的协议）",
    "IP": "互联网协议地址（网络设备的唯一标识）",
    "DNS": "域名系统（把网址翻译成IP地址的服务）",
    "SSH": "安全外壳协议（远程安全登录服务器的工具）",
    "TLS": "传输层安全协议（为网络传输加密）",
    "SSL": "安全套接层（TLS的前身，负责数据加密）",

    # 架构概念
    "微服务": "将大型应用拆分成多个小型独立服务的架构风格",
    "单体架构": "将所有功能打包成一个整体应用的架构方式",
    "分布式系统": "多台计算机协同工作的系统",
    "容器化": "将应用及其依赖打包成可移植容器的技术",
    "云原生": "专门为云计算环境设计应用的理念和方法",
    "负载均衡": "将流量合理分配到多台服务器的技术",
    "缓存": "将数据临时存储以加速后续访问的技术",
    "数据库索引": "为加快数据检索速度而建立的特殊数据结构",
    "消息队列": "用于不同服务之间异步通信的中间件",
    "反向代理": "位于用户和服务器之间的中间服务器",
    "CDN": "内容分发网络（把内容缓存到离用户最近的节点）",
    "Docker": "一种容器化平台（把应用打包成标准化的盒子）",
    "Kubernetes": "容器编排平台（自动管理容器部署和伸缩的系统）",
    "Serverless": "无服务器架构（只需关注代码，无需管理服务器）",

    # 数据概念
    "大数据": "规模庞大到传统工具难以处理的数据集合",
    "机器学习": "让计算机从数据中自动学习规律的技术",
    "深度学习": "使用多层神经网络的机器学习方法",
    "神经网络": "模拟人脑神经元结构的计算模型",
    "人工智能": "让计算机模拟人类智能行为的技术",
    "GPT": "生成式预训练语言模型（能理解和生成人类语言）",
    "LLM": "大型语言模型（处理和理解自然语言的大规模AI模型）",
    "算法": "解决问题的一系列清晰步骤和方法",
    "数据结构": "组织和存储数据的方式",
    "区块链": "去中心化的分布式账本技术",
    "加密": "把信息变成只有特定人才能理解的编码形式",
    "哈希": "将任意长度数据转换成固定长度指纹的算法",
}

# ── 配置选项 ──
_CHINESE_PUNCTUATION = {
    ".": "。",
    ",": "，",
    "?": "？",
    "!": "！",
    ":": "：",
    ";": "；",
    "(": "（",
    ")": "）",
    "[": "【",
    "]": "】",
    '"': "“",
    '"': "”",
    "'": "‘",
    "'": "’",
}


def _detect_audience(task: str) -> str:
    """从任务描述中检测目标受众

    通过关键词匹配判断目标受众类型。

    Args:
        task: 任务描述

    Returns:
        受众类型标识（如 'developer', 'beginner' 等）
    """
    task_lower = task.lower()

    # 受众关键词映射
    audience_keywords = {
        "developer": [
            "开发", "程序员", "工程师", "技术", "developer", "programmer",
            "engineer", "technical", "代码", "code", "编程", "coding",
        ],
        "manager": [
            "经理", "管理", "项目", "进度", "成本", "预算", "资源",
            "manager", "management", "timeline", "budget", "resource",
        ],
        "executive": [
            "高管", "CEO", "CTO", "总裁", "总监", "VP", "执行", "决策",
            "战略", "商业", "价值", "收益", "ROI", "executive", "strategy",
        ],
        "beginner": [
            "初学者", "新手", "入门", "小白", "零基础", "菜鸟", "初级",
            "beginner", "starter", "newbie", "novice", "basic",
        ],
        "customer": [
            "客户", "用户", "消费者", "顾客", "买家", "甲方",
            "customer", "client", "user", "consumer",
        ],
        "non_technical": [
            "非技术", "非技术人员", "普通", "大众", "通俗", "小白",
            "外行", "non-technical", "nontechnical", "layman",
        ],
    }

    scores = {}
    for audience, keywords in audience_keywords.items():
        score = 0
        for kw in keywords:
            if kw in task_lower:
                score += 1
        if score > 0:
            scores[audience] = score

    if scores:
        return max(scores, key=scores.get)

    # 默认：如果没有明确指定，根据内容特征判断
    return "beginner"


def _detect_content_type(task: str) -> str:
    """检测内容类型

    Args:
        task: 任务描述

    Returns:
        内容类型：'technical', 'general', 'news', 'tutorial', 'report'
    """
    task_lower = task.lower()

    if any(kw in task_lower for kw in ["教程", "教学", "guide", "tutorial", "how to", "入门"]):
        return "tutorial"
    if any(kw in task_lower for kw in ["报告", "分析", "report", "analysis", "总结"]):
        return "report"
    if any(kw in task_lower for kw in ["新闻", "news", "报道", "资讯"]):
        return "news"
    if any(kw in task_lower for kw in ["技术", "代码", "编程", "框架", "library", "sdk", "api"]):
        return "technical"

    return "general"


def _extract_content(task: str) -> str:
    """从任务描述中提取需要优化的内容

    尝试从任务描述中识别引用的内容块。

    Args:
        task: 任务描述

    Returns:
        提取到的内容
    """
    # 尝试匹配引号中的内容
    quote_patterns = [
        r'["""]((?:[^"]|\\")+)["""]',      # 双引号
        r"['']((?:[^']|\\')+)['']",         # 单引号
        r'```(.+?)```',                     # 代码块
        r'「(.+?)」',                        # 中文引号
        r'《(.+?)》',                        # 书名号
    ]

    for pattern in quote_patterns:
        matches = re.findall(pattern, task, re.DOTALL)
        if matches:
            return max(matches, key=len).strip()

    # 尝试分隔符后的内容：--- 或 *** 之后的内容
    separator_match = re.split(r'[-*]{3,}\s*\n', task, maxsplit=1)
    if len(separator_match) > 1 and separator_match[1].strip():
        return separator_match[1].strip()

    return task


def _simplify_sentences(text: str, max_words: int = 25) -> str:
    """简化长句子 — 将过长的句子拆分为短句

    Args:
        text: 输入文本
        max_words: 每个句子的最大单词数

    Returns:
        简化后的文本
    """
    # 按中文句号和英文句点分割句子
    sentences = re.split(r'(?<=[。！？.!?])\s*', text)
    simplified = []

    for sentence in sentences:
        if not sentence.strip():
            continue

        # 计算句子的"词"数（中文字符 + 英文单词）
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', sentence))
        english_words = len(re.findall(r'[a-zA-Z]+', sentence))
        total_words = chinese_chars // 2 + english_words  # 近似估算

        if total_words <= max_words:
            simplified.append(sentence)
            continue

        # 长句子拆分：在逗号、分号、连接词处断开
        split_points = list(re.finditer(r'(?:，|,|；|;|、|并且|而且|但是|然而|因此|所以)', sentence))

        if len(split_points) < 2:
            # 没有足够的分割点，直接保留原句
            simplified.append(sentence)
            continue

        # 从中间附近的位置拆分
        mid = len(split_points) // 2
        split_pos = split_points[mid].end()

        part1 = sentence[:split_pos].strip()
        part2 = sentence[split_pos:].strip()

        if part1:
            simplified.append(part1 + ("。" if not part1.endswith(("。", "！", "？")) else ""))
        if part2:
            simplified.append(part2)

    return "\n".join(simplified)


def _markdown_to_plain_text(text: str) -> str:
    """将 Markdown 格式文本转换为纯文本

    Args:
        text: Markdown 文本

    Returns:
        纯文本字符串
    """
    # 移除代码块
    text = re.sub(r'```[\s\S]*?```', '', text)

    # 移除行内代码标记
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # 处理标题：移除 # 号
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # 处理加粗和斜体
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)

    # 处理链接 [text](url) -> text (url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1（\2）', text)

    # 处理图片 ![alt](url) -> [图片: alt]
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'[图片: \1]', text)

    # 处理列表标记
    text = re.sub(r'^[-*+]\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+[.、]\s+', '', text, flags=re.MULTILINE)

    # 处理表格：移除分隔线，单元格内容用空格分隔
    text = re.sub(r'\|[ -:\|]+\|', '', text, flags=re.MULTILINE)
    text = re.sub(r'\|', ' ', text)

    # 处理引用
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

    # 处理分隔线
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)

    # 合并多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def _add_technical_markers(text: str) -> str:
    """为技术术语添加标记（加粗标记），便于生成强调格式

    Args:
        text: 输入文本

    Returns:
        添加了标记的文本
    """
    result = text

    # 按术语长度降序排序（优先匹配长术语）
    sorted_terms = sorted(_TECH_TERMS.keys(), key=len, reverse=True)

    for term in sorted_terms:
        # 只标记尚未被标记的术语
        pattern = r'(?<!\*\*)(?<!\*\*\*)\b' + re.escape(term) + r'\b(?!\*\*)'
        result = re.sub(pattern, f'**{term}**', result)

    return result


def _remove_technical_terms(text: str, replacement: str = "通俗化解释") -> str:
    """将技术术语替换为通俗解释

    Args:
        text: 输入文本
        replacement: 替换方式：'通俗化解释' 替换为解释、'删除' 替换为通用词、保持原样加括号说明

    Returns:
        处理后的文本
    """
    result = text

    # 按术语长度降序排序
    sorted_terms = sorted(_TECH_TERMS.keys(), key=len, reverse=True)

    for term in sorted_terms:
        if term in result:
            explanation = _TECH_TERMS[term]
            if replacement == "通俗化解释":
                result = result.replace(term, f"{term}（{explanation}）")
            elif replacement == "替换":
                result = result.replace(term, explanation)
            # "标记"模式下保持原样

    return result


def _convert_to_beginner_style(text: str) -> str:
    """将技术内容转换为适合初学者的风格

    - 简化长句
    - 技术术语添加解释
    - 增加类比描述

    Args:
        text: 输入文本

    Returns:
        转换后的文本
    """
    # 1. 简化长句
    text = _simplify_sentences(text, max_words=20)

    # 2. 技术术语加通俗解释
    text = _remove_technical_terms(text, replacement="通俗化解释")

    # 3. 英文术语添加中文翻译
    def _add_chinese_translation(match):
        word = match.group(0)
        if word in _TECH_TERMS:
            explanation = _TECH_TERMS[word]
            # 如果还没有被解释过
            if "（" not in word:
                return f"{word}（{explanation}）"
        return word

    # 为常见的英文技术术语添加翻译
    common_terms = ['API', 'SDK', 'HTTP', 'JSON', 'SQL', 'IDE', 'CLI', 'GUI', 'ORM', 'DNS']
    for term in common_terms:
        if term in text and f"{term}（" not in text:
            explanation = _TECH_TERMS.get(term, "")
            if explanation:
                text = text.replace(term, f"{term}（{explanation}）")

    # 4. 添加鼓励性或引导性语句
    text = text.strip()
    if text and not text.endswith(("。", "！", "？", ".")):
        text += "。"

    return text


def _convert_to_executive_style(text: str) -> str:
    """将内容转换为面向高管的风格

    - 提炼核心要点
    - 突出商业价值和战略意义
    - 使用简洁有力的语言

    Args:
        text: 输入文本

    Returns:
        转换后的文本
    """
    # 1. 提取关键语句（包含"价值"、"收益"、"成本"、"效率"等关键词的句子）
    sentences = re.split(r'(?<=[。！？.!?])\s*', text)
    key_sentences = []
    value_keywords = [
        "价值", "收益", "成本", "效率", "提升", "降低", "增长", "ROI",
        "战略", "竞争", "优势", "利润", "收入", "节约", "节省",
        "value", "revenue", "cost", "efficiency", "growth", "profit",
    ]

    for sentence in sentences:
        for kw in value_keywords:
            if kw in sentence:
                key_sentences.append(sentence.strip())
                break

    # 2. 如果找到了关键句子，用它们重构内容
    if key_sentences:
        text = "。".join(key_sentences[:5])
        if not text.endswith("。"):
            text += "。"

    # 3. 简化句子，突出结论
    text = _simplify_sentences(text, max_words=15)

    return text


def _convert_to_non_technical_style(text: str) -> str:
    """将技术内容转换为非技术人员可理解的风格

    - 完全消除技术术语或用类比替代
    - 使用日常语言
    - 增加生活化类比

    Args:
        text: 输入文本

    Returns:
        转换后的文本
    """
    # 1. 替换技术术语为通俗解释（替换模式）
    for term, explanation in sorted(_TECH_TERMS.items(), key=lambda x: -len(x[0])):
        if term in text:
            text = text.replace(term, explanation)

    # 2. 简化长句
    text = _simplify_sentences(text, max_words=15)

    # 3. 清理技术代码片段
    text = re.sub(r'[{}()\[\]<>]', '', text)
    text = re.sub(r'[\w.]+\([\w\s,]*\)', '', text)  # 移除函数调用

    return text


def _detect_format_requirements(task: str) -> list[str]:
    """检测格式转换需求

    Args:
        task: 任务描述

    Returns:
        格式需求列表
    """
    formats = []
    task_lower = task.lower()

    format_keywords = {
        "markdown_to_plain": ["转纯文本", "去格式", "remove format", "plain text", "纯文本"],
        "plain_to_markdown": ["转markdown", "加格式", "to markdown"],
        "simplify": ["简化", "缩短", "精简", "提炼", "摘要", "summarize", "shorten", "simplify"],
        "expand": ["展开", "扩写", "详细", "expand", "detail", "elaborate"],
        "bullet_points": ["要点", "列表", "条列", "bullet", "list", "提纲"],
        "translate_to_chinese": ["翻译成中文", "译为中文", "to chinese", "中文翻译"],
        "translate_to_english": ["翻译成英文", "译为英文", "to english", "英文翻译"],
    }

    for fmt, keywords in format_keywords.items():
        for kw in keywords:
            if kw in task_lower:
                formats.append(fmt)
                break

    return formats


def run_modify_agent(task: str) -> str:
    """
    ModifyAgent - 内容优化入口函数

    接收任务描述，分析受众和格式要求，返回优化后的内容。

    支持的功能：
    - 受众适配：developer / manager / executive / beginner / customer / non_technical
    - 格式转换：Markdown ↔ 纯文本
    - 文本简化/扩写
    - 技术术语管理：添加/移除术语标记

    Args:
        task: 任务描述，包含原始内容和目标受众/格式要求，例如：
              - "把这段内容改写成面向初学者的版本：...内容..."
              - "面向高管总结：...报告内容..."
              - "把这篇技术文档转成纯文本"
              - "为这段内容添加技术术语标记"

    Returns:
        优化后的内容字符串
    """
    try:
        # 1. 检测目标受众
        audience = _detect_audience(task)
        audience_desc = AUDIENCES.get(audience, "通用")

        # 2. 检测格式需求
        formats = _detect_format_requirements(task)

        # 3. 提取内容
        content = _extract_content(task)
        if not content or len(content) < 3:
            return (
                "❌ 无法从任务描述中提取需要优化的内容。\n\n"
                "请将要优化的内容放在引号中，或用 --- 分隔符隔开，例如：\n"
                '  - 面向初学者改写："我们的API支持RESTful风格调用..."\n'
                "  - 转纯文本：---\n    原来的Markdown内容...\n    ---"
            )

        original_content = content

        # 4. 执行格式转换
        if "markdown_to_plain" in formats:
            content = _markdown_to_plain_text(content)

        # 5. 根据受众执行内容转换
        if audience == "beginner":
            content = _convert_to_beginner_style(content)
        elif audience == "executive":
            content = _convert_to_executive_style(content)
        elif audience == "non_technical":
            content = _convert_to_non_technical_style(content)
        elif audience == "developer":
            # 为开发者：添加技术术语标记
            content = _add_technical_markers(content)
        elif audience == "manager":
            # 为管理者：简化句子 + 突出进度/成本相关
            content = _simplify_sentences(content, max_words=25)
        elif audience == "customer":
            # 为客户：去掉技术细节，聚焦功能收益
            content = _remove_technical_terms(content, replacement="通俗化解释")
            content = _simplify_sentences(content, max_words=20)

        # 6. 如果指定了简化
        if "simplify" in formats:
            content = _simplify_sentences(content, max_words=15)

        # 7. 组装输出
        lines = []
        lines.append(f"✏️  内容优化结果")
        lines.append(f"{'═' * 50}")
        lines.append(f"🎯 目标受众: {audience} ({audience_desc})")

        if formats:
            fmt_names = {
                "markdown_to_plain": "Markdown → 纯文本",
                "simplify": "文本简化",
                "expand": "内容扩写",
                "bullet_points": "要点提取",
            }
            applied = [fmt_names.get(f, f) for f in formats if f in fmt_names]
            if applied:
                lines.append(f"🛠️  应用转换: {' + '.join(applied)}")

        lines.append("")
        lines.append(f"{'─' * 50}")
        lines.append(content)
        lines.append("")
        lines.append(f"{'═' * 50}")

        # 添加转换说明
        changes = []
        if audience in ("beginner", "non_technical"):
            changes.append("✅ 技术术语已添加通俗解释")
        if "markdown_to_plain" in formats:
            changes.append("✅ Markdown 格式已转换为纯文本")
        if "simplify" in formats or audience in ("executive", "manager"):
            changes.append("✅ 长句已简化")
        if audience == "developer":
            changes.append("✅ 技术术语已添加加粗标记")
        if audience == "customer":
            changes.append("✅ 技术细节已替换为功能描述")

        if changes:
            lines.append("\n".join(changes))

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 内容优化失败: {e}"
