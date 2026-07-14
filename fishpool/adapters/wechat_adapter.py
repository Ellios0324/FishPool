"""
微信适配器 —— 基于 WeChatFerry (wcf) / WeChatHook

WeChatFerry 是一个基于 Windows 微信 PC 客户端的 Hook 框架，
通过注入 DLL 到微信进程实现消息的收发。

支持的方案：
1. WeChatFerry (wcf) — 推荐，支持 Python SDK，维护活跃
   GitHub: https://github.com/lich0821/WeChatFerry
2. ComWeChatRobot — 基于 COM 接口的微信机器人
3. WechatBot/WechatAPI — 其他 Hook 方案

使用前提：
- Windows 操作系统
- 安装特定版本的微信 PC 客户端
- 运行 wcf 服务端（wcf.exe 或 wcf-service.exe）

WeChatFerry 架构：
┌─────────────┐     gRPC      ┌──────────────┐
│  wcf.exe    │ ◄──────────►  │ FishPool     │
│ (注入微信)   │   port:10086  │ (Python gRPC)│
└─────────────┘               └──────────────┘

如果无法安装 wcf，本适配器也提供 HTTP API 模式，
可对接其他类似微信机器人服务。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

import aiohttp

from .base import BaseAdapter
from .message import Message, MessageHandler, PlatformType

logger = logging.getLogger("fishpool.adapter.wechat")


class WeChatAdapter(BaseAdapter):
    """
    微信适配器

    支持两种模式：
    1. wcf 模式：通过 gRPC 连接 WeChatFerry（需要 wcf_python 库）
    2. http 模式：通过 HTTP API 连接微信机器人服务（通用）

    Args:
        config: 配置字典
            - protocol: "wcf" (默认) 或 "http"
            - host: 服务地址（默认 "127.0.0.1"）
            - port: 服务端口（wcf 默认 10086，http 默认 8080）
            - poll_interval: 轮询间隔秒数（http 模式，默认 1.0）
            - admin_users: 管理员微信号列表（可选）
    """

    def __init__(self, name: str = "wechat", config: Optional[dict] = None):
        super().__init__(name, PlatformType.WECHAT, config or {})
        self._protocol: str = self.config.get("protocol", "wcf")
        self._host: str = self.config.get("host", "127.0.0.1")
        self._port: int = int(self.config.get("port", 10086))
        self._poll_interval: float = float(self.config.get("poll_interval", 1.0))
        self._admin_users: list[str] = self.config.get("admin_users", [])

        # 内部状态
        self._session: Optional[aiohttp.ClientSession] = None
        self._poll_task: Optional[asyncio.Task] = None
        self._wcf_grpc_stub = None  # wcf gRPC stub (延迟导入)
        self._last_msg_id: int = 0
        self._self_wxid: str = ""

        # 缓存：wxid -> 昵称
        self._contact_cache: dict[str, str] = {}

        # 是否已初始化 wcf
        self._wcf_available: bool = False

    # ───────────────────── 生命周期 ─────────────────────

    async def start(self):
        """启动微信适配器"""
        self._logger.info(
            f"🚀 微信适配器启动中，模式: {self._protocol}, "
            f"地址: {self._host}:{self._port}"
        )

        if self._protocol == "wcf":
            await self._start_wcf_mode()
        elif self._protocol == "http":
            await self._start_http_mode()
        else:
            raise ValueError(f"不支持的协议模式: {self._protocol}")

        self._running = True
        self._logger.info("✅ 微信适配器已启动")

    async def stop(self):
        """停止微信适配器"""
        self._logger.info("🛑 微信适配器停止中...")
        self._running = False

        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        if self._session:
            await self._session.close()
            self._session = None

        self._logger.info("✅ 微信适配器已停止")

    # ───────────────────── wcf 模式启动 ─────────────────────

    async def _start_wcf_mode(self):
        """启动 wcf gRPC 模式"""
        try:
            # 延迟导入 wcf，避免未安装时影响其他模块
            import grpc
            from wcf_pb2 import Request, Response
            from wcf_pb2_grpc import WcfStub

            # 建立 gRPC 连接
            channel = grpc.aio.insecure_channel(f"{self._host}:{self._port}")
            self._wcf_grpc_stub = WcfStub(channel)

            # 检查连接
            try:
                # 获取自身微信ID，验证连接
                result = await self._wcf_grpc_stub.get_self_wxid(Request())
                self._self_wxid = result.wxid
                self._wcf_available = True
                self._logger.info(f"✅ wcf 连接成功，自身微信ID: {self._self_wxid}")
            except Exception as e:
                self._logger.warning(f"wcf 连接测试失败: {e}")
                self._wcf_available = False

            # 启动轮询监听
            self._poll_task = asyncio.create_task(self._wcf_poll_loop())

        except ImportError:
            self._logger.warning(
                "未安装 wcf_python 库，尝试 HTTP 模式回退\n"
                "请安装: pip install wcf-python\n"
                "或设置 protocol: http 使用 HTTP API"
            )
            # 回退到 HTTP 模式
            self._protocol = "http"
            await self._start_http_mode()

    async def _wcf_poll_loop(self):
        """wcf 模式的消息轮询循环"""
        if not self._wcf_grpc_stub:
            return

        from wcf_pb2 import Request

        self._logger.info("开始轮询微信消息...")

        while self._running:
            try:
                # 获取新消息
                request = Request(last_id=self._last_msg_id)
                response = await self._wcf_grpc_stub.get_msg(request)

                for msg_data in response.messages:
                    msg_id = msg_data.id
                    if msg_id <= self._last_msg_id:
                        continue

                    self._last_msg_id = msg_id
                    await self._process_wcf_message(msg_data)

            except Exception as e:
                if self._running:
                    self._logger.error(f"轮询消息失败: {e}")

            await asyncio.sleep(self._poll_interval)

    async def _process_wcf_message(self, msg_data):
        """处理 wcf 消息"""
        msg_type = msg_data.type
        # 1=文本, 3=图片, 34=语音, 37=好友确认, 47=动画表情, ...

        # 只处理文本消息
        if msg_type != 1:
            return

        wxid = msg_data.sender
        room_id = msg_data.roomid  # 群聊ID，私聊为空
        content = msg_data.content
        msg_id = str(msg_data.id)

        # 判断是否为群聊
        is_group = bool(room_id)

        # 获取发送者昵称
        if is_group:
            # 群聊中 sender 格式: "群ID:成员ID<,成员ID,...>"
            actual_sender = msg_data.sender
            if ":" in actual_sender:
                parts = actual_sender.split(":", 1)
                room_id = parts[0]
                actual_sender = parts[1].split(",")[0]

            sender_name = await self._get_contact_name(actual_sender)
            group_name = await self._get_contact_name(room_id)

            # 检查是否 @ 机器人
            is_at = f"@{self._get_self_name()}" in content if self._self_wxid else False
        else:
            sender_name = await self._get_contact_name(wxid)
            group_name = None
            is_at = False

        # 去掉群聊中的 @ 标记文本
        if is_group and is_at:
            # 移除 "@昵称" 前缀
            import re
            content = re.sub(rf"^@{self._get_self_name()}\s*", "", content).strip()

        # 构建统一消息
        message = Message(
            platform=PlatformType.WECHAT,
            message_id=msg_id,
            sender_id=wxid,
            sender_name=sender_name or wxid,
            content=content,
            raw_content=msg_data.content,
            group_id=room_id if is_group else None,
            group_name=group_name,
            is_group=is_group,
            is_at=is_at,
            extra={
                "msg_type": msg_type,
                "xml": msg_data.xml,
            },
        )

        self._logger.info(f"📩 收到微信消息: {message.brief}")

        # 分发给处理器
        reply = await self._dispatch_message(message)
        if reply:
            target = room_id if is_group else wxid
            await self.send_message(target, reply, is_group=is_group)

    # ───────────────────── HTTP 模式 ─────────────────────

    async def _start_http_mode(self):
        """启动 HTTP API 模式（通用方案）"""
        self._session = aiohttp.ClientSession()
        base_url = f"http://{self._host}:{self._port}"

        # 检查 API 是否可用
        try:
            async with self._session.get(f"{base_url}/health", timeout=5) as resp:
                if resp.status == 200:
                    self._logger.info("✅ HTTP API 服务可用")
                else:
                    self._logger.warning(f"HTTP API 返回异常状态: {resp.status}")
        except Exception as e:
            self._logger.warning(f"HTTP API 不可用: {e}")

        self._poll_task = asyncio.create_task(self._http_poll_loop(base_url))

    async def _http_poll_loop(self, base_url: str):
        """HTTP 模式的消息轮询"""
        self._logger.info("开始 HTTP 轮询微信消息...")

        while self._running:
            try:
                async with self._session.get(
                    f"{base_url}/get_messages",
                    params={"last_id": self._last_msg_id},
                    timeout=10,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        messages = data.get("messages", [])
                        for msg in messages:
                            msg_id = msg.get("id", 0)
                            if msg_id <= self._last_msg_id:
                                continue
                            self._last_msg_id = msg_id
                            await self._process_http_message(msg)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._running:
                    self._logger.warning(f"HTTP 轮询异常: {e}")

            await asyncio.sleep(self._poll_interval)

    async def _process_http_message(self, msg: dict):
        """处理 HTTP 模式收到的消息"""
        msg_type = msg.get("type", 0)
        if msg_type != 1:  # 非文本消息
            return

        wxid = msg.get("sender", "")
        room_id = msg.get("roomid", "")
        content = msg.get("content", "")
        msg_id = str(msg.get("id", 0))

        is_group = bool(room_id)

        message = Message(
            platform=PlatformType.WECHAT,
            message_id=msg_id,
            sender_id=wxid,
            sender_name=wxid,
            content=content,
            group_id=room_id if is_group else None,
            is_group=is_group,
            is_at=False,
            extra={"msg_type": msg_type},
        )

        self._logger.info(f"📩 收到微信消息(HTTP): {message.brief}")

        reply = await self._dispatch_message(message)
        if reply:
            target = room_id if is_group else wxid
            await self.send_message(target, reply, is_group=is_group)

    # ───────────────────── 消息发送 ─────────────────────

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
        发送微信消息

        Args:
            target: 微信号(wxid) 或群ID(roomid)
            content: 消息内容
            is_group: 是否发送到群聊
            reply_to: (暂不支持)
            at_sender: 群聊中 @ 指定用户（wcf 支持）

        Returns:
            发送成功返回 True
        """
        try:
            if self._protocol == "wcf" and self._wcf_available:
                return await self._send_wcf(target, content, is_group, at_sender)
            elif self._protocol == "http":
                return await self._send_http(target, content, is_group)
            else:
                self._logger.error("未连接任何微信服务")
                return False
        except Exception as e:
            self._logger.error(f"发送消息失败: {e}")
            return False

    async def _send_wcf(
        self,
        target: str,
        content: str,
        is_group: bool,
        at_sender: Optional[str] = None,
    ) -> bool:
        """通过 wcf gRPC 发送消息"""
        try:
            from wcf_pb2 import Request

            if is_group:
                # 群聊消息
                if at_sender:
                    # 带 @ 的消息
                    content = f"@{await self._get_contact_name(at_sender)} {content}"
                    # 使用 send_at_msg API
                    request = Request(
                        roomid=target,
                        wxid=at_sender,
                        msg=content,
                    )
                    await self._wcf_grpc_stub.send_at_msg(request)
                else:
                    request = Request(roomid=target, msg=content)
                    await self._wcf_grpc_stub.send_room_msg(request)
            else:
                request = Request(wxid=target, msg=content)
                await self._wcf_grpc_stub.send_txt_msg(request)

            self._logger.info(f"📤 发送微信消息到 {'群' if is_group else '私聊'}{target}")
            return True

        except Exception as e:
            self._logger.error(f"wcf 发送失败: {e}")
            return False

    async def _send_http(self, target: str, content: str, is_group: bool) -> bool:
        """通过 HTTP API 发送消息"""
        if not self._session:
            return False

        base_url = f"http://{self._host}:{self._port}"
        endpoint = "/send_room_msg" if is_group else "/send_txt_msg"
        params = {
            "msg": content,
        }
        if is_group:
            params["roomid"] = target
        else:
            params["wxid"] = target

        try:
            async with self._session.post(
                f"{base_url}{endpoint}",
                json=params,
                timeout=10,
            ) as resp:
                result = await resp.json()
                success = result.get("success", False) or resp.status == 200
                if success:
                    self._logger.info(f"📤 发送微信消息(HTTP)到 {target}")
                return success
        except Exception as e:
            self._logger.error(f"HTTP 发送失败: {e}")
            return False

    # ───────────────────── 辅助方法 ─────────────────────

    async def _get_contact_name(self, wxid: str) -> str:
        """
        获取联系人昵称（带缓存）
        """
        if not wxid:
            return ""

        if wxid in self._contact_cache:
            return self._contact_cache[wxid]

        try:
            if self._protocol == "wcf" and self._wcf_available:
                from wcf_pb2 import Request

                request = Request(wxid=wxid)
                response = await self._wcf_grpc_stub.get_info(request)
                name = response.name or wxid
            else:
                name = wxid
        except Exception:
            name = wxid

        self._contact_cache[wxid] = name
        return name

    def _get_self_name(self) -> str:
        """获取机器人自身昵称"""
        return self._contact_cache.get(self._self_wxid, f"wxid_{self._self_wxid[:8]}")

    async def get_self_info(self) -> dict:
        """获取机器人自身信息"""
        if self._protocol == "wcf" and self._wcf_available:
            try:
                from wcf_pb2 import Request

                request = Request()
                response = await self._wcf_grpc_stub.get_self_info(request)
                return {
                    "wxid": response.wxid,
                    "name": response.name,
                    "mobile": response.mobile,
                }
            except Exception as e:
                self._logger.error(f"获取自身信息失败: {e}")
        return {}

    async def health_check(self) -> bool:
        """健康检查"""
        if self._protocol == "wcf":
            return self._running and self._wcf_available
        else:
            return self._running and self._session is not None
