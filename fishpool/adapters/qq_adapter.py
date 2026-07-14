"""
QQ 适配器 —— 基于 OneBot v11 协议（反向 WebSocket）

连接到支持 OneBot v11 协议的 QQ 机器人框架（如 NapCatQQ、Lagrange.Core、
LLOneBot 等），通过反向 WebSocket 接收和发送消息。

支持的框架：
- NapCatQQ (推荐) — 基于 Electron，支持 OneBot v11，维护活跃
- Lagrange.Core — 基于 .NET，纯协议实现，跨平台
- LLOneBot — 基于 Lolicon 框架
- go-cqhttp — 已停止维护，但部分社区分叉仍在运行

使用方式：
1. 在 QQ 机器人框架中开启「反向 WebSocket」服务
2. 配置 ws_url 指向框架的 WebSocket 地址
3. 启动 FishPool 系统即可自动连接
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Coroutine, Optional

import aiohttp

from .base import BaseAdapter
from .message import Message, MessageHandler, PlatformType

logger = logging.getLogger("fishpool.adapter.qq")


class QQAdapter(BaseAdapter):
    """
    QQ 适配器

    通过反向 WebSocket 连接 OneBot v11 兼容的 QQ 机器人框架。

    Args:
        config: 配置字典，支持以下字段：
            - ws_url: WebSocket 服务器地址，如 "ws://localhost:8080/ws"
            - bot_qq: 机器人 QQ 号（用于识别 @ 消息）
            - reconnect_interval: 重连间隔（秒，默认 5）
            - max_reconnect_retries: 最大重连次数（默认 -1 无限）
            - access_token: 鉴权 Token（可选）
    """

    def __init__(self, name: str = "qq", config: Optional[dict] = None):
        super().__init__(name, PlatformType.QQ, config or {})
        self._ws_url: str = self.config.get("ws_url", "ws://localhost:8080/ws")
        self._bot_qq: str = str(self.config.get("bot_qq", ""))
        self._reconnect_interval: int = int(self.config.get("reconnect_interval", 5))
        self._max_retries: int = int(self.config.get("max_reconnect_retries", -1))
        self._access_token: str = self.config.get("access_token", "")
        self._retry_count: int = 0
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._listen_task: Optional[asyncio.Task] = None

        # OneBot v11 的 action 调用递增 ID
        self._echo_id: int = 0

    # ───────────────────── 生命周期 ─────────────────────

    async def start(self):
        """启动适配器，连接到 QQ 框架的 WebSocket 服务"""
        self._logger.info(f"🚀 QQ适配器启动中，连接地址: {self._ws_url}")
        self._session = aiohttp.ClientSession()
        self._running = True
        self._retry_count = 0
        self._listen_task = asyncio.create_task(self._listen_loop())
        self._logger.info("✅ QQ适配器已启动")

    async def stop(self):
        """停止适配器，断开 WebSocket 连接"""
        self._logger.info("🛑 QQ适配器停止中...")
        self._running = False

        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        if self._ws and not self._ws.closed:
            await self._ws.close()

        if self._session:
            await self._session.close()

        self._ws = None
        self._session = None
        self._logger.info("✅ QQ适配器已停止")

    # ───────────────────── 消息发送 ─────────────────────

    async def send_message(
        self,
        target: str,
        content: str,
        is_group: bool = False,
        *,
        reply_to: Optional[str] = None,
        at_sender: Optional[str] = None,
        auto_escape: bool = False,
        **kwargs,
    ) -> bool:
        """
        发送 QQ 消息

        使用 OneBot v11 的 send_msg API。
        群聊中支持 @ 指定用户。

        Args:
            target: 群号或 QQ 号
            content: 消息内容（支持 CQ 码）
            is_group: 是否群聊
            reply_to: 回复的消息 ID
            at_sender: 需要 @ 的 QQ 号（群聊）
            auto_escape: 是否转义 CQ 码

        Returns:
            发送成功返回 True
        """
        if not self._ws or self._ws.closed:
            self._logger.error("WebSocket 未连接，无法发送消息")
            return False

        # 构建消息内容
        message_content = content

        # 如果在群聊中需要 @ 某人
        if is_group and at_sender:
            message_content = f"[CQ:at,qq={at_sender}] {message_content}"

        # 构建 action 请求
        action = "send_group_msg" if is_group else "send_private_msg"
        params = {
            "message": message_content,
            "auto_escape": auto_escape,
        }

        if is_group:
            params["group_id"] = int(target)
        else:
            params["user_id"] = int(target)

        return await self._call_action(action, params)

    async def _call_action(self, action: str, params: dict) -> bool:
        """
        调用 OneBot v11 Action API

        Args:
            action: 动作名称（如 send_group_msg）
            params: 参数字典

        Returns:
            调用成功返回 True
        """
        if not self._ws or self._ws.closed:
            return False

        self._echo_id += 1
        payload = {
            "action": action,
            "params": params,
            "echo": str(self._echo_id),
        }

        try:
            await self._ws.send_json(payload)
            self._logger.debug(f"📤 发送 OneBot action: {action}, params={params}")
            return True
        except Exception as e:
            self._logger.error(f"发送 action 失败: {e}")
            return False

    # ───────────────────── 消息接收 ─────────────────────

    async def _listen_loop(self):
        """WebSocket 监听循环（含自动重连）"""
        while self._running:
            try:
                # 检查重连次数
                if (
                    self._max_retries >= 0
                    and self._retry_count >= self._max_retries
                ):
                    self._logger.error(
                        f"达到最大重连次数 ({self._max_retries})，停止重连"
                    )
                    break

                self._logger.info(
                    f"正在连接 WebSocket: {self._ws_url}"
                    + (f" (第 {self._retry_count + 1} 次重试)" if self._retry_count > 0 else "")
                )

                # 建立 WebSocket 连接
                headers = {}
                if self._access_token:
                    headers["Authorization"] = f"Bearer {self._access_token}"

                async with self._session.ws_connect(
                    self._ws_url,
                    headers=headers,
                    heartbeat=30.0,  # 30秒心跳
                ) as ws:
                    self._ws = ws
                    self._retry_count = 0
                    self._logger.info("✅ WebSocket 连接成功")

                    # 消息接收循环
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_ws_message(msg.data)
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            self._logger.error(
                                f"WebSocket 错误: {ws.exception()}"
                            )
                            break
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            self._logger.warning("WebSocket 连接关闭")
                            break

            except asyncio.CancelledError:
                self._logger.info("WebSocket 监听任务取消")
                break
            except aiohttp.ClientError as e:
                self._logger.warning(f"WebSocket 连接失败: {e}")
            except Exception as e:
                self._logger.error(f"WebSocket 异常: {e}", exc_info=True)

            # 重连逻辑
            if self._running:
                self._retry_count += 1
                self._ws = None
                self._logger.info(
                    f"⏳ {self._reconnect_interval} 秒后重连..."
                )
                await asyncio.sleep(self._reconnect_interval)

    async def _handle_ws_message(self, data: str):
        """
        处理收到的 WebSocket 消息

        根据 OneBot v11 协议解析消息事件，
        转换为统一的 Message 模型后分发给处理器。
        """
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            self._logger.warning(f"收到非 JSON 消息: {data[:100]}")
            return

        # Only handle message events, not API responses
        post_type = payload.get("post_type")
        if post_type != "message":
            return

        # 解析消息详情
        message_type = payload.get("message_type", "")
        user_id = str(payload.get("user_id", ""))
        sender = payload.get("sender", {})
        nickname = sender.get("nickname", user_id)
        card = sender.get("card", "")  # 群名片
        sender_name = card or nickname

        raw_message = str(payload.get("raw_message", ""))
        message_id = str(payload.get("message_id", ""))

        # 判断是否 @ 机器人
        is_at_bot = False
        if self._bot_qq and f"[CQ:at,qq={self._bot_qq}]" in raw_message:
            is_at_bot = True

        # 判断群聊
        is_group = message_type == "group"
        group_id = str(payload.get("group_id", "")) if is_group else None

        # 构建统一消息对象
        message = Message(
            platform=PlatformType.QQ,
            message_id=message_id,
            sender_id=user_id,
            sender_name=sender_name,
            content=self._clean_cq_code(raw_message),
            raw_content=raw_message,
            group_id=group_id,
            is_group=is_group,
            is_at=is_at_bot,
            extra={
                "user_id": user_id,
                "message_type": message_type,
                "font": payload.get("font"),
            },
        )

        self._logger.info(f"📩 收到QQ消息: {message.brief}")

        # 分发给处理器
        reply = await self._dispatch_message(message)
        if reply:
            await self.send_message(
                target=message.chat_id,
                content=reply,
                is_group=is_group,
                at_sender=user_id if is_group else None,
            )

    @staticmethod
    def _clean_cq_code(text: str) -> str:
        """
        清理 CQ 码，提取纯文本

        例如: "[CQ:at,qq=123] 你好" -> "你好"
        """
        import re

        # 移除所有 CQ 码
        text = re.sub(r"\[CQ:[^\]]*\]", "", text).strip()
        # 移除多余空格
        text = re.sub(r"\s+", " ", text)
        return text

    # ───────────────────── 健康检查 ─────────────────────

    async def health_check(self) -> bool:
        """检查 WebSocket 连接状态"""
        return self._running and self._ws is not None and not self._ws.closed
