"""
FishPool 适配器抽象基类

定义所有消息平台适配器必须实现的接口规范。
遵循"依赖倒置"原则，高层模块（适配器管理器）依赖于抽象接口。
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, Optional

from .message import Message, MessageHandler, PlatformType

logger = logging.getLogger("fishpool.adapter")


class BaseAdapter(ABC):
    """
    适配器抽象基类

    所有消息平台适配器必须继承此类并实现所有抽象方法。
    子类应负责：
    - 与平台 API 的连接管理
    - 消息的接收和解析（转换为统一 Message 模型）
    - 消息的发送（从统一 Message 模型转换为平台格式）
    - 生命周期管理（启动/停止/重连）

    Attributes:
        name: 适配器名称标识
        platform: 所属平台类型
        config: 适配器配置字典
        _handler: 注册的消息处理回调
        _running: 运行状态标志
    """

    def __init__(self, name: str, platform: PlatformType, config: dict[str, Any]):
        self.name = name
        self.platform = platform
        self.config = config
        self._handler: Optional[MessageHandler] = None
        self._running = False
        self._logger = logging.getLogger(f"fishpool.adapter.{name}")

    # ───────────────────── 抽象方法-必须实现 ─────────────────────

    @abstractmethod
    async def start(self):
        """
        启动适配器

        建立与消息平台的连接（WebSocket / HTTP / RPC 等），
        开始监听消息。应处理连接异常和自动重连逻辑。
        """
        raise NotImplementedError

    @abstractmethod
    async def stop(self):
        """
        停止适配器

        关闭连接，释放资源。应确保优雅关闭，
        等待正在处理的消息完成。
        """
        raise NotImplementedError

    @abstractmethod
    async def send_message(
        self,
        target: str,
        content: str,
        is_group: bool = False,
        *,
        reply_to: Optional[str] = None,
        at_sender: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """
        发送消息到目标

        Args:
            target: 目标ID（群号或用户QQ/微信号）
            content: 消息文本内容
            is_group: 是否为群聊
            reply_to: 被回复的消息ID（可选）
            at_sender: 需要 @ 的发送者ID（群聊中可选）
            **kwargs: 平台特定参数

        Returns:
            发送成功返回 True，失败返回 False
        """
        raise NotImplementedError

    # ───────────────────── 消息处理 ─────────────────────

    async def on_message(self, handler: MessageHandler):
        """
        注册消息处理器

        当接收到平台消息时，适配器会调用此处理器。
        处理器接收 Message 对象，返回回复文本（可选）。

        Args:
            handler: 异步回调函数，接收 Message，返回 Optional[str]
        """
        self._handler = handler

    async def _dispatch_message(self, message: Message) -> Optional[str]:
        """
        分发消息到已注册的处理器

        子类在收到消息后调用此方法进行分发。

        Args:
            message: 标准化的消息对象

        Returns:
            处理器的回复文本（如果有）
        """
        if self._handler is None:
            self._logger.warning(f"未注册消息处理器，丢弃消息: {message.brief}")
            return None

        try:
            self._logger.info(f"分发消息: {message.brief}")
            reply = await self._handler(message)
            return reply
        except Exception as e:
            self._logger.error(f"消息处理异常: {e}", exc_info=True)
            return f"⚠️ 消息处理出错: {str(e)}"

    # ───────────────────── 生命周期 ─────────────────────

    @property
    def is_running(self) -> bool:
        """适配器是否正在运行"""
        return self._running

    async def health_check(self) -> bool:
        """
        健康检查

        返回适配器连接是否正常。
        子类可重写此方法添加具体的连接检测逻辑。
        """
        return self._running

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}[{self.name}]({self.platform.value})>"

    def __repr__(self) -> str:
        return self.__str__()
