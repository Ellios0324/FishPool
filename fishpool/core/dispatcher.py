"""
FishPool Agent 调度器

负责将消息路由到对应的 Agent 进行处理。
支持意图识别、Agent 调用、结果整合。
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from fishpool.adapters.message import Message, PlatformType

logger = logging.getLogger("fishpool.dispatcher")


class AgentDispatcher:
    """
    Agent 调度器

    接收来自适配器层的统一消息，解析意图，路由到对应 Agent，
    收集结果并返回回复文本。
    """

    def __init__(self):
        self._logger = logging.getLogger("fishpool.dispatcher")
        self._agents: dict[str, object] = {}

    def register_agent(self, name: str, agent: object):
        """注册 Agent"""
        self._agents[name] = agent
        self._logger.info(f"📋 注册 Agent: {name}")

    async def dispatch(self, message: Message) -> Optional[str]:
        """
        调度消息到对应的 Agent

        流程：
        1. 提取消息内容
        2. 判断消息类型和意图
        3. 路由到合适的 Agent
        4. 返回处理结果

        Args:
            message: 标准化的消息对象

        Returns:
            Agent 处理后的回复文本，None 表示无回复
        """
        content = message.content.strip()

        if not content:
            return None

        # 记录消息来源
        platform_name = message.platform.value
        source = f"[{platform_name}]"
        if message.is_group:
            source += f"[群:{message.group_name or message.group_id}]"
        source += f"[{message.sender_name}]"

        self._logger.info(f"📨 调度消息 {source}: {content[:80]}")

        # ── 意图识别与路由 ──

        # 1. 帮助指令
        if content in ("/help", "帮助", "菜单", "功能"):
            return self._handle_help()

        # 2. 天气查询 → Dolphin Agent
        if any(kw in content for kw in ("天气", "气温", "下雨", "台风", "温度")):
            return await self._call_agent("dolphin", content)

        # 3. 编程相关 → KillerWhale Agent
        if any(
            kw in content
            for kw in ("代码", "编程", "写一个", "实现", "debug", "bug", "算法")
        ):
            return await self._call_agent("killerwhale", content)

        # 4. 技能管理 → FishFarmer Agent
        if any(kw in content for kw in ("技能", "学习", "教程", "课程", "训练")):
            return await self._call_agent("fishfarmer", content)

        # 5. 内容优化 → ModifyAgent
        if any(kw in content for kw in ("优化", "润色", "改写", "修改", "翻译")):
            return await self._call_agent("modify", content)

        # 6. 系统信息
        if content in ("/status", "状态", "ping"):
            return self._handle_status()

        # 7. 默认回复
        return self._handle_default(message)

    def _handle_help(self) -> str:
        """帮助菜单"""
        return (
            "🐟 FishPool 智能助手\n"
            "─────────────────\n"
            "📌 可用功能：\n"
            "  🌤 天气查询 — 例：\"北京天气\"\n"
            "  💻 编程助手 — 例：\"用Python写一个排序算法\"\n"
            "  📚 技能学习 — 例：\"Go语言入门教程\"\n"
            "  ✏️ 内容优化 — 例：\"润色这段文字\"\n"
            "  ℹ️ 状态查看 — 输入 \"状态\"\n\n"
            "💡 @我 + 问题 或 私聊发送即可使用"
        )

    def _handle_status(self) -> str:
        """系统状态"""
        agent_list = ", ".join(self._agents.keys()) or "无"
        return (
            "🐟 FishPool 运行状态\n"
            "─────────────────\n"
            f"✅ 系统正常运行\n"
            f"🤖 已注册 Agent: {agent_list}\n"
            f"⏰ 当前时间: 在线\n"
        )

    def _handle_default(self, message: Message) -> str:
        """默认回复"""
        return (
            f"你好 {message.sender_name}！👋\n"
            f"我是 FishPool 智能助手，你可以：\n"
            f"• 输入「帮助」查看所有功能\n"
            f"• 直接提问，我会为你路由到最合适的 AI Agent\n"
        )

    async def _call_agent(self, agent_name: str, content: str) -> str:
        """
        调用指定 Agent 处理消息

        实际项目中，这里会调用 LLM 或专门的 Agent 服务。
        当前返回模拟结果。
        """
        agent = self._agents.get(agent_name)
        if agent and hasattr(agent, "process"):
            try:
                return await agent.process(content)
            except Exception as e:
                self._logger.error(f"Agent {agent_name} 处理失败: {e}")
                return f"⚠️ {agent_name} 处理出错: {str(e)}"
        else:
            self._logger.info(f"Agent {agent_name} 未注册，返回模拟响应")
            return self._mock_agent_response(agent_name, content)

    def _mock_agent_response(self, agent_name: str, content: str) -> str:
        """模拟 Agent 响应（开发阶段使用）"""
        responses = {
            "dolphin": (
                f"🌤 Dolphin 天气查询结果：\n"
                f"📍 查询内容: {content}\n"
                f"☀️ 今日天气: 晴，20~25°C\n"
                f"💨 风力: 3-4级\n"
                f"⚠️ 提示: 当前为模拟数据，请集成真实天气 API"
            ),
            "killerwhale": (
                f"🐋 KillerWhale 编程助手：\n"
                f"📝 收到问题: {content}\n"
                f"💡 建议方案: ...\n"
                f"🔧 (当前为模拟响应，请集成真实 LLM 服务)"
            ),
            "fishfarmer": (
                f"🌾 FishFarmer 技能管理：\n"
                f"📚 关于「{content}」\n"
                f"📖 推荐学习路径: ...\n"
                f"🎯 (当前为模拟响应，请集成真实知识库)"
            ),
            "modify": (
                f"✏️ ModifyAgent 内容优化：\n"
                f"📝 原文: {content}\n"
                f"✅ 优化结果: ...\n"
                f"✨ (当前为模拟响应，请集成真实 LLM 服务)"
            ),
        }
        return responses.get(
            agent_name,
            f"🤖 {agent_name} 正在处理你的请求: {content[:50]}...\n⏳ 处理中，请稍候",
        )
