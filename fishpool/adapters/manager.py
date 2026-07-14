"""
适配器管理器

负责所有消息平台适配器的注册、生命周期管理、消息路由。
是 FishPool 系统与外部消息通道之间的核心调度层。

架构：
┌─────────────────────────────────────────────────────┐
│                    AdapterManager                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ QQAdapter│  │WxAdapter │  │Telegram..│  (插件式) │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       │             │             │                 │
│       └──────┬──────┘─────────────┘                 │
│              ▼                                       │
│     Message Router → message_handler                 │
│              │                                       │
│              ▼                                       │
│     FishPool Agent Dispatcher                        │
└─────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Any, Callable, Coroutine, Optional

from .base import BaseAdapter
from .message import Message, MessageHandler, PlatformType

logger = logging.getLogger("fishpool.adapter.manager")


class AdapterManager:
    """
    适配器管理器

    管理所有消息平台适配器的注册、启动、停止和消息路由。
    采用插件式架构，新增平台只需实现 BaseAdapter 子类并注册即可。

    Usage:
        manager = AdapterManager(config)

        # 注册适配器
        manager.register(QQAdapter(config["qq"]))
        manager.register(WeChatAdapter(config["wechat"]))

        # 设置消息处理器（连接到 FishPool 核心）
        await manager.set_message_handler(my_handler)

        # 启动所有
        await manager.start_all()

        # 等待
        await manager.wait_for_shutdown()
    """

    def __init__(self, config: Optional[dict] = None):
        self._config: dict = config or {}
        self._adapters: dict[str, BaseAdapter] = {}
        self._message_handler: Optional[MessageHandler] = None
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()

    # ───────────────────── 适配器注册 ─────────────────────

    def register(self, adapter: BaseAdapter) -> "AdapterManager":
        """
        注册适配器

        Args:
            adapter: 适配器实例

        Returns:
            self（支持链式调用）
        """
        if adapter.name in self._adapters:
            raise ValueError(f"适配器 '{adapter.name}' 已存在，请先注销")

        self._adapters[adapter.name] = adapter
        logger.info(f"📋 注册适配器: {adapter}")
        return self

    def unregister(self, name: str) -> Optional[BaseAdapter]:
        """
        注销适配器

        Args:
            name: 适配器名称

        Returns:
            被注销的适配器实例（如存在）
        """
        adapter = self._adapters.pop(name, None)
        if adapter:
            logger.info(f"🗑️ 注销适配器: {adapter}")
        return adapter

    def get_adapter(self, name: str) -> Optional[BaseAdapter]:
        """根据名称获取适配器实例"""
        return self._adapters.get(name)

    def get_adapters_by_platform(self, platform: PlatformType) -> list[BaseAdapter]:
        """按平台类型获取适配器列表"""
        return [a for a in self._adapters.values() if a.platform == platform]

    @property
    def all_adapters(self) -> dict[str, BaseAdapter]:
        """获取所有适配器的只读副本"""
        return dict(self._adapters)

    @property
    def adapter_count(self) -> int:
        """已注册的适配器数量"""
        return len(self._adapters)

    # ───────────────────── 消息处理器 ─────────────────────

    async def set_message_handler(self, handler: MessageHandler):
        """
        设置全局消息处理器

        当任意适配器收到消息时，会调用此处理器。
        处理器接收 Message 对象，返回回复文本（可选）。

        这是适配器层与 FishPool Agent 调度层的连接点。

        Args:
            handler: 异步回调函数 (Message) -> Optional[str]
        """
        self._message_handler = handler
        logger.info("🔗 设置全局消息处理器")

        # 为所有已注册适配器设置处理器
        for adapter in self._adapters.values():
            await adapter.on_message(handler)

    # ───────────────────── 生命周期管理 ─────────────────────

    async def start_all(self):
        """
        启动所有已注册的适配器

        同时设置消息处理器（如果已配置）。
        """
        if self._running:
            logger.warning("适配器管理器已在运行中")
            return

        self._running = True
        logger.info(f"🚀 启动所有适配器 (共 {len(self._adapters)} 个)...")

        # 为所有适配器设置消息处理器
        if self._message_handler:
            for adapter in self._adapters.values():
                await adapter.on_message(self._message_handler)

        # 并行启动所有适配器
        start_tasks = []
        for name, adapter in self._adapters.items():
            task = asyncio.create_task(self._start_adapter_safe(adapter))
            start_tasks.append(task)

        if start_tasks:
            await asyncio.gather(*start_tasks, return_exceptions=True)

        logger.info(f"✅ 适配器管理器启动完成 (成功: {self._count_running()}/{len(self._adapters)})")

    async def stop_all(self):
        """
        停止所有适配器

        发送停止信号，等待所有适配器优雅关闭。
        """
        logger.info("🛑 停止所有适配器...")

        self._running = False

        stop_tasks = []
        for name, adapter in self._adapters.items():
            task = asyncio.create_task(self._stop_adapter_safe(adapter))
            stop_tasks.append(task)

        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        # 取消所有后台任务
        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()
        self._shutdown_event.set()
        logger.info("✅ 所有适配器已停止")

    async def _start_adapter_safe(self, adapter: BaseAdapter):
        """安全启动单个适配器"""
        try:
            await adapter.start()
            logger.info(f"✅ 适配器 {adapter.name} 启动成功")
        except Exception as e:
            logger.error(f"❌ 适配器 {adapter.name} 启动失败: {e}", exc_info=True)

    async def _stop_adapter_safe(self, adapter: BaseAdapter):
        """安全停止单个适配器"""
        try:
            await adapter.stop()
            logger.info(f"✅ 适配器 {adapter.name} 已停止")
        except Exception as e:
            logger.error(f"❌ 适配器 {adapter.name} 停止异常: {e}", exc_info=True)

    def _count_running(self) -> int:
        """统计运行中的适配器数量"""
        return sum(1 for a in self._adapters.values() if a.is_running)

    # ───────────────────── 生命周期钩子 ─────────────────────

    def on_shutdown(self, handler: Callable[[], Coroutine[Any, Any, None]]):
        """
        注册关闭回调
        """
        self._shutdown_handler = handler

    async def wait_for_shutdown(self, signal_handlers: bool = True):
        """
        等待关闭信号

        设置 SIGINT/SIGTERM 信号处理，阻塞直到收到信号。
        适合在主程序入口使用。

        Args:
            signal_handlers: 是否自动注册系统信号处理
        """
        if signal_handlers:
            loop = asyncio.get_event_loop()

            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(
                        sig,
                        lambda: asyncio.create_task(self._handle_signal(sig)),
                    )
                except NotImplementedError:
                    # Windows 不支持 add_signal_handler
                    pass

        logger.info("等待关闭信号 (Ctrl+C)...")
        await self._shutdown_event.wait()

    async def _handle_signal(self, sig):
        """处理系统信号"""
        logger.warning(f"收到信号 {sig.name}，准备关闭...")
        await self.stop_all()

    # ───────────────────── 统计信息 ─────────────────────

    def get_stats(self) -> dict:
        """获取管理器状态统计"""
        return {
            "running": self._running,
            "adapter_count": self.adapter_count,
            "adapters": {
                name: {
                    "platform": adapter.platform.value,
                    "running": adapter.is_running,
                    "type": adapter.__class__.__name__,
                }
                for name, adapter in self._adapters.items()
            },
        }

    def __str__(self) -> str:
        status = "运行中" if self._running else "已停止"
        return (
            f"<AdapterManager [{status}] "
            f"适配器: {self.adapter_count}个 "
            f"({', '.join(self._adapters.keys()) or '无'})>"
        )

    def __repr__(self) -> str:
        return self.__str__()
