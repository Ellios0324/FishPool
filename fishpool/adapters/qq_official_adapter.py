"""
QQ 官方机器人 API 适配器

使用 QQ 官方机器人 API（https://bot.q.qq.com/）接入，
通过 WebSocket 协议接收消息，通过 HTTP API 发送消息。

无需依赖任何第三方 QQ 机器人框架，直接在 QQ 开放平台注册机器人即可。

使用前准备：
1. 前往 https://q.qq.com/ 注册并创建机器人应用
2. 获取 APPID（应用ID）和应用密钥（APPSecret）
3. 在机器人管理后台设置「机器人令牌」（Token）
4. 配置 sandbox=true 在沙箱环境开发调试

支持的连接模式：
- websocket（默认）：通过 WebSocket 长连接接收消息事件
- webhook：通过 HTTP Webhook 接收消息事件（TODO）

协议文档：https://bot.q.qq.com/wiki/develop/api/

WebSocket 连接流程：
1. 客户端连接 Gateway → 服务器发送 HELLO (OpCode 10)
2. 客户端发送 IDENTIFY (OpCode 2) 进行鉴权（必须包含 intents）
3. 服务器回复 READY (OpCode 0, t="READY") → 获得 session_id
4. 开始监听消息事件
"""

from __future__ import annotations

import asyncio
import json
import logging
import platform
import time
from typing import Any, Optional

import aiohttp

from .base import BaseAdapter
from .message import Message, MessageHandler, PlatformType

logger = logging.getLogger("fishpool.adapter.qq_official")

# ── QQ 官方 WebSocket OpCode 定义 ──

OP_DISPATCH = 0            # 事件分发
OP_HEARTBEAT = 1           # 心跳
OP_IDENTIFY = 2            # 鉴权（标识身份）
OP_RESUME = 6              # 恢复连接
OP_RECONNECT = 7           # 重新连接（服务器要求）
OP_INVALID_SESSION = 9     # 无效会话
OP_HELLO = 10              # 连接成功（含心跳间隔）
OP_HEARTBEAT_ACK = 11      # 心跳回复

# ── 事件类型 ──

EVENT_READY = "READY"                              # 鉴权成功，获得 session_id
EVENT_RESUMED = "RESUMED"                          # 连接恢复成功
EVENT_AT_MESSAGE_CREATE = "AT_MESSAGE_CREATE"            # 群聊 @ 机器人
EVENT_GROUP_AT_MESSAGE_CREATE = "GROUP_AT_MESSAGE_CREATE"  # 群聊 @（新版）
EVENT_C2C_MESSAGE_CREATE = "C2C_MESSAGE_CREATE"          # 私聊消息
EVENT_GROUP_ADD_ROBOT = "GROUP_ADD_ROBOT"                # 机器人被邀请进群
EVENT_GROUP_DEL_ROBOT = "GROUP_DEL_ROBOT"                # 机器人被移出群

# ── Intent 定义 ──
# 按位标记，定义机器人监听的事件类型
# 文档：https://bot.q.qq.com/wiki/develop/api-v2/dev-prepare/interface-obj/event-enum.html

INTENT_GUILDS = 1 << 0                  # 1      — 频道事件
INTENT_GUILD_MEMBERS = 1 << 1           # 2      — 频道成员
INTENT_GUILD_MESSAGE_REACTIONS = 1 << 10  # 1024  — 消息表情
INTENT_DIRECT_MESSAGE = 1 << 12         # 4096   — 私信事件
INTENT_OPEN_FORUM_EVENT = 1 << 18       # 262144 — 开放论坛
INTENT_AUDIO_OR_LIVE = 1 << 19          # 524288 — 音频/直播
INTENT_GROUP_AND_C2C = 1 << 25          # 33554432 — 群聊和C2C事件（新版机器人核心）
INTENT_INTERACTION = 1 << 26            # 67108864 — 交互事件

# ── API 端点 ──

SANDBOX_WS_URL = "wss://sandbox.api.sgroup.qq.com/websocket/"
PRODUCTION_WS_URL = "wss://api.sgroup.qq.com/websocket/"
SANDBOX_API_BASE = "https://sandbox.api.sgroup.qq.com"
PRODUCTION_API_BASE = "https://api.sgroup.qq.com"

# ── 消息类型常量 ──

MSG_TYPE_TEXT = 0       # 文本
MSG_TYPE_MARKDOWN = 2   # Markdown
MSG_TYPE_ARK = 3        # Ark 卡片
MSG_TYPE_EMBED = 4      # Embed 卡片


class QQOfficialAdapter(BaseAdapter):
    """
    QQ 官方机器人 API 适配器

    使用 QQ 官方机器人 API（https://bot.q.qq.com/）接入，
    通过 WebSocket 协议接收消息，通过 HTTP API 发送消息。

    使用前需要在 https://q.qq.com/ 创建机器人应用，获取：
    - APPID: 应用ID
    - APPSecret: 应用密钥（用于获取 access_token）
    - Token: 机器人令牌（在机器人管理页面设置）

    配置项：
    - app_id: QQ机器人APPID（必填）
    - app_secret: 应用密钥（必填）
    - token: 机器人令牌（必填，管理后台设置的自定义Token）
    - sandbox: 是否使用沙箱环境（默认true）
    - intents: 监听的意图位掩码（默认监听群聊和C2C消息）
    - reconnect_interval: 重连间隔秒数（默认5）
    - max_reconnect_retries: 最大重连次数（默认-1无限）
    """

    def __init__(self, name: str = "qq_official", config: Optional[dict] = None):
        super().__init__(name, PlatformType.QQ, config or {})
        self._app_id: str = str(self.config.get("app_id", ""))
        self._app_secret: str = str(self.config.get("app_secret", ""))
        self._token: str = str(self.config.get("token", ""))
        self._sandbox: bool = bool(self.config.get("sandbox", True))
        self._intents: int = int(self.config.get("intents", INTENT_GROUP_AND_C2C))
        self._reconnect_interval: int = int(self.config.get("reconnect_interval", 5))
        self._max_retries: int = int(self.config.get("max_reconnect_retries", -1))

        # WebSocket 相关状态
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._retry_count: int = 0
        self._session_id: Optional[str] = None
        self._heartbeat_interval: float = 30.0  # 默认30秒，收到 HELLO 后会更新
        self._last_seq: Optional[int] = None     # 最后一次收到的消息序号（用于断线恢复）
        self._identified: bool = False           # 是否已完成鉴权
        self._access_token: Optional[str] = None  # 从 app_secret 换取的真实令牌

        # 构建 WebSocket 连接地址
        self._ws_url = SANDBOX_WS_URL if self._sandbox else PRODUCTION_WS_URL

        # 构建 Authorization Header
        # 格式: "Bot {app_id}.{token}"
        self._auth_header = f"QQBot {self._app_id}:{self._token}"

        self._logger.info(
            f"QQ官方适配器初始化完成, "
            f"app_id={self._app_id[:8]}..., "
            f"sandbox={self._sandbox}, "
            f"intents={self._intents}, "
            f"ws_url={self._ws_url}"
        )

    # ───────────────────── 属性 ─────────────────────

    @property
    def _api_base(self) -> str:
        """获取当前环境的 API 基础地址"""
        return SANDBOX_API_BASE if self._sandbox else PRODUCTION_API_BASE

    # ───────────────────── 生命周期 ─────────────────────

    async def start(self):
        """
        启动适配器，建立 WebSocket 连接到 QQ 官方 Gateway

        流程：
        1. 检查配置完整性（app_id / token 必填）
        2. 创建 HTTP 会话
        3. 先获取 access_token（如果配置了 app_secret）
        4. 启动 WebSocket 监听循环（含自动重连）
        """
        if not self._app_id:
            self._logger.error("QQ官方适配器启动失败: 缺少 app_id 配置")
            return

        if not self._token:
            self._logger.error("QQ官方适配器启动失败: 缺少 token 配置")
            return

        self._logger.info(
            f"🚀 QQ官方适配器启动中 (sandbox={self._sandbox})"
        )
        self._session = aiohttp.ClientSession()
        self._running = True
        self._retry_count = 0
        self._identified = False

        # 先获取 access_token
        # 如果配置了 app_secret，则用 app_secret 换取 access_token
        # 获取到的 access_token 将用于 IDENTIFY 鉴权
        if self._app_secret:
            await self._get_access_token()

        self._listen_task = asyncio.create_task(self._listen_loop())
        self._logger.info("✅ QQ官方适配器已启动")

    async def stop(self):
        """
        停止适配器，断开所有连接

        优雅关闭顺序：
        1. 取消心跳任务
        2. 取消监听任务
        3. 关闭 WebSocket
        4. 关闭 HTTP 会话
        """
        self._logger.info("🛑 QQ官方适配器停止中...")
        self._running = False

        # 1. 取消心跳任务
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # 2. 取消监听任务
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        # 3. 关闭 WebSocket
        if self._ws and not self._ws.closed:
            await self._ws.close()

        # 4. 关闭 HTTP 会话
        if self._session:
            await self._session.close()

        self._ws = None
        self._session = None
        self._heartbeat_task = None
        self._listen_task = None
        self._session_id = None
        self._identified = False
        self._logger.info("✅ QQ官方适配器已停止")

    # ───────────────────── WebSocket 监听循环 ─────────────────────

    async def _listen_loop(self):
        """
        WebSocket 监听循环（含自动重连）

        维持与 QQ 官方 Gateway 的长连接，处理以下情况：
        - 正常消息接收
        - 网络断开自动重连
        - 服务器要求重连（OpCode 7）
        - 无效会话（OpCode 9）
        """
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
                    f"正在连接 QQ 官方 WebSocket: {self._ws_url}"
                    + (f" (第 {self._retry_count + 1} 次重试)" if self._retry_count > 0 else "")
                )

                # 建立 WebSocket 连接
                # QQ 官方 API v2 的 WebSocket 连接不需要在 Header 中携带 Authorization
                # 鉴权信息在 IDENTIFY 消息体内发送
                headers = {}

                async with self._session.ws_connect(
                    self._ws_url,
                    headers=headers,
                    heartbeat=30.0,  # aiohttp 层面的心跳检测
                ) as ws:
                    self._ws = ws
                    self._retry_count = 0
                    self._logger.info("✅ QQ官方 WebSocket 连接成功")

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
                self._session_id = None
                self._identified = False

                # 取消旧的心跳任务
                if self._heartbeat_task and not self._heartbeat_task.done():
                    self._heartbeat_task.cancel()
                    try:
                        await self._heartbeat_task
                    except asyncio.CancelledError:
                        pass
                    self._heartbeat_task = None

                self._logger.info(
                    f"⏳ {self._reconnect_interval} 秒后重连..."
                )
                await asyncio.sleep(self._reconnect_interval)

    # ───────────────────── WebSocket 消息处理 ─────────────────────

    async def _handle_ws_message(self, data: str):
        """
        处理收到的 WebSocket 消息

        根据 QQ 官方 WebSocket 协议解析 OpCode 和数据载荷。

        Args:
            data: 收到的 JSON 字符串
        """
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            self._logger.warning(f"收到非 JSON 消息: {data[:200]}")
            return

        op = payload.get("op")
        d = payload.get("d", {})
        s = payload.get("s")  # 消息序号（sequence）
        t = payload.get("t")  # 事件类型（仅 OP_DISPATCH 时有值）

        # 更新消息序号
        if s is not None:
            self._last_seq = s

        # ── 按 OpCode 分发处理 ──

        if op == OP_HELLO:
            # 连接成功，服务器返回 HELLO 事件
            # 包含 heartbeat_interval（毫秒）
            # 注意：HELLO 不包含 session_id，session_id 在 READY 事件中
            await self._handle_hello(d)

        elif op == OP_DISPATCH:
            # 事件分发（包含 READY 事件和消息事件）
            self._logger.debug(f"📨 收到事件: {t}")
            await self._handle_event(t, d)

        elif op == OP_HEARTBEAT_ACK:
            # 心跳回复确认
            self._logger.debug("💓 心跳回复 ACK")

        elif op == OP_RECONNECT:
            # 服务器要求客户端重新连接
            self._logger.warning("🔄 收到 RECONNECT 指令，准备重连")
            if self._ws and not self._ws.closed:
                await self._ws.close()
            # 关闭连接后，监听循环会自动重连

        elif op == OP_INVALID_SESSION:
            # 会话无效，需要重新鉴权
            self._logger.error("❌ 无效会话 (INVALID_SESSION)，需要重新鉴权")
            self._identified = False
            self._session_id = None
            # 发送 IDENTIFY 重新鉴权（不关闭连接，直接重新鉴权）
            await self._send_identify()

        else:
            self._logger.debug(f"收到未处理的 OpCode: {op}")

    async def _handle_hello(self, data: dict):
        """
        处理 HELLO 事件（OpCode 10）

        连接成功后，服务器返回 HELLO 事件，包含：
        - heartbeat_interval: 心跳间隔（毫秒）

        收到 HELLO 后必须发送 IDENTIFY（OpCode 2）进行鉴权。

        Args:
            data: HELLO 事件的 d 字段
        """
        heartbeat_interval_ms = data.get("heartbeat_interval", 30000)
        self._heartbeat_interval = heartbeat_interval_ms / 1000.0

        self._logger.info(
            f"👋 收到 HELLO, "
            f"heartbeat_interval={self._heartbeat_interval:.1f}s"
        )

        # 启动心跳任务
        self._start_heartbeat()

        # 🐟 修复：发送 IDENTIFY 进行鉴权
        # 根据 QQ 官方协议，收到 HELLO 后必须发送 IDENTIFY 才能开始接收事件
        await self._send_identify()

    async def _get_access_token(self) -> Optional[str]:
        """
        通过 app_id 和 app_secret 换取 access_token

        QQ 官方 API v2 需要先通过此接口获取 access_token，
        然后用 access_token 作为 WebSocket 鉴权的凭证。

        POST https://sandbox.api.sgroup.qq.com/v2/app/access_token
        Body: { "app_id": "xxx", "app_secret": "xxx" }
        """
        if not self._app_secret:
            self._logger.warning("未配置 app_secret，无法获取 access_token")
            return None
            
        url = f"{self._api_base}/v2/app/access_token"
        body = {
            "app_id": self._app_id,
            "app_secret": self._app_secret,
        }
        headers = {
            "Content-Type": "application/json",
        }
    
        try:
            self._logger.info("🔑 正在获取 access_token...")
            async with self._session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    access_token = result.get("access_token")
                    if access_token:
                        self._access_token = access_token
                        self._logger.info(f"✅ access_token 获取成功: {access_token[:20]}...")
                        return access_token
                    else:
                        self._logger.error(f"❌ access_token 获取失败: 响应中无 access_token 字段: {result}")
                else:
                    error_text = await resp.text()
                    self._logger.error(f"❌ access_token 获取失败 [HTTP {resp.status}]: {error_text[:200]}")
        except Exception as e:
            self._logger.error(f"❌ access_token 获取异常: {e}")
    
        return None


    async def _send_identify(self):
        """
        发送 IDENTIFY 鉴权请求（OpCode 2）

        在收到 HELLO 后调用此方法进行鉴权，或 INVALID_SESSION 后重新鉴权。

        QQ 官方 API 的 IDENTIFY 载荷格式：
        {
            "op": 2,
            "d": {
                "token": "Bot {app_id}.{token} 或 QQBot {app_id}:{access_token}",
                "intents": <intents_bitmask>,
                "shard": [0, 1],  // 分片信息
                "properties": {
                    "$os": "linux|mac|windows",
                    "$device": "fishpool",
                    "$browser": "fishpool"
                }
            }
        }

        Intents 说明：
        - GROUP_AND_C2C_EVENT (1 << 25) = 33554432：监听群聊和C2C消息（新版机器人推荐）

        Token 格式说明：
        - 如果通过 app_secret 获取到了 access_token，则使用 "QQBot {app_id}:{access_token}"
        - 否则使用配置中的 token 字段 "QQBot {app_id}:{token}"
        """
        if not self._ws or self._ws.closed:
            self._logger.warning("WebSocket 未连接，无法发送 IDENTIFY")
            return

        # 优先使用 access_token（从 app_secret 换取），否则使用配置的 QQBot 格式 token
        identify_token = self._access_token if self._access_token else self._token
        identify_auth = f"QQBot {self._app_id}:{identify_token}"

        identify_payload = {
            "op": OP_IDENTIFY,
            "d": {
                "token": identify_auth,
                "intents": self._intents,
                "shard": [0, 1],
                "properties": {
                    "$os": platform.system().lower(),
                    "$device": "fishpool_bot",
                    "$browser": "fishpool_bot",
                },
            },
        }

        try:
            await self._ws.send_json(identify_payload)
            self._logger.info(
                f"🔐 已发送 IDENTIFY 鉴权请求 "
                f"(intents={self._intents}, "
                f"shard=[0,1], "
                f"token_type={'access_token' if self._access_token else 'config_token'})"
            )
        except Exception as e:
            self._logger.error(f"发送 IDENTIFY 失败: {e}")

    # ───────────────────── 事件处理 ─────────────────────

    async def _handle_event(self, event_type: str, data: dict):
        """
        处理 QQ 官方 API 的事件分发（OpCode 0）

        根据事件类型解析不同的消息事件。

        Args:
            event_type: 事件类型字符串（如 "READY", "AT_MESSAGE_CREATE"）
            data: 事件数据的 d 字段
        """
        # 🐟 修复：处理 READY 事件，获取 session_id
        if event_type == EVENT_READY:
            await self._handle_ready(data)

        # 连接恢复成功
        elif event_type == EVENT_RESUMED:
            self._logger.info("🔄 连接恢复成功")

        # 群聊 @ 机器人消息
        elif event_type in (EVENT_AT_MESSAGE_CREATE, EVENT_GROUP_AT_MESSAGE_CREATE):
            await self._handle_group_at_message(data)

        # 私聊消息
        elif event_type == EVENT_C2C_MESSAGE_CREATE:
            await self._handle_c2c_message(data)

        # 机器人被邀请进群
        elif event_type == EVENT_GROUP_ADD_ROBOT:
            group_id = data.get("group_openid", data.get("guild_id", ""))
            self._logger.info(f"📥 机器人被邀请进群: {group_id}")

        # 机器人被移出群
        elif event_type == EVENT_GROUP_DEL_ROBOT:
            group_id = data.get("group_openid", data.get("guild_id", ""))
            self._logger.info(f"📤 机器人被移出群: {group_id}")

        else:
            self._logger.debug(f"忽略未处理的事件类型: {event_type}")

    async def _handle_ready(self, data: dict):
        """
        处理 READY 事件（鉴权成功）

        IDENTIFY 鉴权成功后，服务器返回 READY 事件，包含：
        - version: 版本号
        - session_id: 当前会话ID（用于断线恢复和心跳）
        - user: 机器人自身信息
        - shard: 分片信息

        这是获取 session_id 的正确时机。

        Args:
            data: READY 事件的 d 字段
        """
        self._session_id = data.get("session_id", "")
        version = data.get("version", 0)
        user = data.get("user", {})
        user_id = user.get("id", "")

        self._identified = True
        self._logger.info(
            f"✅ IDENTIFY 鉴权成功！"
            f"session_id={self._session_id[:8] if self._session_id else 'N/A'}..., "
            f"version={version}, "
            f"bot_id={user_id}"
        )

    async def _handle_group_at_message(self, data: dict):
        """
        处理群聊 @ 机器人消息事件

        QQ 官方 API 的群聊 @ 消息事件格式：
        {
            "channel_type": "GROUP",
            "guild_id": "群ID",
            "content": "消息文本",
            "author": {
                "id": "用户ID",
                "username": "用户名",
                "member_openid": "群成员openid"
            },
            "msg_id": "消息ID",
            "timestamp": "ISO时间戳"
        }

        Args:
            data: 事件数据的 d 字段
        """
        try:
            group_id = data.get("guild_id", "")
            content = data.get("content", "")
            author = data.get("author", {})
            user_id = author.get("id", "") or author.get("member_openid", "")
            username = author.get("username", user_id)
            msg_id = data.get("msg_id", "")
            timestamp_str = data.get("timestamp", "")

            # 解析 ISO 8601 时间戳
            timestamp = time.time()
            if timestamp_str:
                try:
                    from datetime import datetime
                    # 兼容 "2024-01-01T00:00:00Z" 和带时区的格式
                    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    timestamp = dt.timestamp()
                except (ValueError, TypeError):
                    pass

            # 构建统一消息对象
            message = Message(
                platform=PlatformType.QQ,
                message_id=msg_id,
                sender_id=user_id,
                sender_name=username,
                content=content.strip(),
                raw_content=content,
                group_id=group_id,
                is_group=True,
                is_at=True,  # @ 机器人消息默认标记为 @
                timestamp=timestamp,
                extra={
                    "msg_id": msg_id,
                    "event_type": "AT_MESSAGE_CREATE",
                    "author": author,
                    "channel_type": data.get("channel_type", "GROUP"),
                },
            )

            self._logger.info(
                f"📩 收到群聊 @ 消息: "
                f"[群:{group_id}] {username}({user_id}): {content[:60]}"
            )

            # 分发给已注册的消息处理器
            reply = await self._dispatch_message(message)
            if reply:
                await self.send_message(
                    target=group_id,
                    content=reply,
                    is_group=True,
                    reply_to=msg_id,
                    at_sender=user_id,
                )

        except Exception as e:
            self._logger.error(f"处理群聊 @ 消息失败: {e}", exc_info=True)

    async def _handle_c2c_message(self, data: dict):
        """
        处理私聊消息事件

        QQ 官方 API 的私聊消息事件格式：
        {
            "channel_type": "DIRECT",
            "content": "消息文本",
            "author": {
                "id": "用户ID",
                "username": "用户名",
                "member_openid": "群成员openid"
            },
            "msg_id": "消息ID",
            "timestamp": "ISO时间戳"
        }

        Args:
            data: 事件数据的 d 字段
        """
        try:
            content = data.get("content", "")
            author = data.get("author", {})
            user_id = author.get("id", "") or author.get("member_openid", "")
            username = author.get("username", user_id)
            msg_id = data.get("msg_id", "")
            timestamp_str = data.get("timestamp", "")

            # 解析 ISO 8601 时间戳
            timestamp = time.time()
            if timestamp_str:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    timestamp = dt.timestamp()
                except (ValueError, TypeError):
                    pass

            # 构建统一消息对象
            message = Message(
                platform=PlatformType.QQ,
                message_id=msg_id,
                sender_id=user_id,
                sender_name=username,
                content=content.strip(),
                raw_content=content,
                is_group=False,
                is_at=True,  # 私聊消息天然是 @ 机器人
                timestamp=timestamp,
                extra={
                    "msg_id": msg_id,
                    "event_type": "C2C_MESSAGE_CREATE",
                    "author": author,
                    "channel_type": data.get("channel_type", "DIRECT"),
                },
            )

            self._logger.info(
                f"📩 收到私聊消息: "
                f"{username}({user_id}): {content[:60]}"
            )

            # 分发给已注册的消息处理器
            reply = await self._dispatch_message(message)
            if reply:
                await self.send_message(
                    target=user_id,
                    content=reply,
                    is_group=False,
                    reply_to=msg_id,
                )

        except Exception as e:
            self._logger.error(f"处理私聊消息失败: {e}", exc_info=True)

    # ───────────────────── 心跳机制 ─────────────────────

    def _start_heartbeat(self):
        """启动心跳任务（如果已有则先取消）"""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()

        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._logger.debug(f"💓 心跳任务已创建，间隔 {self._heartbeat_interval:.1f}s")

    async def _heartbeat_loop(self):
        """
        心跳循环

        根据 HELLO 事件中返回的 heartbeat_interval（毫秒），
        定时向服务器发送心跳包（OpCode 1）。
        """
        self._logger.info(f"💓 心跳任务启动，间隔 {self._heartbeat_interval:.1f}s")

        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_interval)

                if self._running and self._ws and not self._ws.closed:
                    await self._send_heartbeat()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"心跳任务异常: {e}")
                break

        self._logger.info("💓 心跳任务结束")

    async def _send_heartbeat(self):
        """
        发送心跳包

        心跳包格式：
        {
            "op": 1,          // OpCode 心跳
            "d": last_seq     // 最后一次收到的消息序号（用于断线恢复）
        }

        如果 last_seq 为 None，表示尚未收到任何事件。
        """
        if not self._ws or self._ws.closed:
            return

        payload = {
            "op": OP_HEARTBEAT,
            "d": self._last_seq,
        }

        try:
            await self._ws.send_json(payload)
            self._logger.debug("💓 发送心跳包")
        except Exception as e:
            self._logger.error(f"发送心跳包失败: {e}")

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
        发送消息到 QQ

        使用 QQ 官方 HTTP API 发送消息。
        - 群聊消息: POST /v2/groups/{group_guild_id}/messages
        - 私聊消息: POST /v2/users/{user_openid}/messages

        官方文档：
        https://bot.q.qq.com/wiki/develop/api-v2/server-inter/message/send-receive/send.html

        Args:
            target: 群 guild_id（群聊）或用户 openid（私聊）
            content: 消息文本内容
            is_group: 是否群聊
            reply_to: 被回复的消息 ID（可选）
            at_sender: 需要 @ 的用户 ID（群聊中可选）
            **kwargs: 其他参数

        Returns:
            发送成功返回 True
        """
        if not content:
            self._logger.warning("消息内容为空，跳过发送")
            return False

        if not self._session:
            self._logger.error("HTTP 会话未初始化，无法发送消息")
            return False

        # 构建请求体
        body = {
            "content": content,
            "msg_type": MSG_TYPE_TEXT,  # 0=文本消息
        }

        # 回复消息：设置 msg_id 表示回复指定消息
        if reply_to:
            body["msg_id"] = reply_to
            body["msg_seq"] = 1  # 回复序号

        # 群聊中 @ 指定用户
        # QQ 官方 API 支持在消息内容中使用 <@user_id> 格式 @ 用户
        if is_group and at_sender:
            body["content"] = f"<@{at_sender}> {content}"

        # 选择 API 端点
        if is_group:
            api_path = f"/v2/groups/{target}/messages"
        else:
            api_path = f"/v2/users/{target}/messages"

        self._logger.info(
            f"📤 发送{'群聊' if is_group else '私聊'}消息 "
            f"到 {target}: {content[:60]}..."
        )

        result = await self._call_official_api("POST", api_path, body)

        if result:
            self._logger.debug(f"✅ 消息发送成功: {result}")
        else:
            self._logger.error(f"❌ 消息发送失败: target={target}")

        return bool(result)

    # ───────────────────── HTTP API 调用 ─────────────────────

    async def _call_official_api(
        self,
        method: str,
        path: str,
        body: Optional[dict] = None,
    ) -> Any:
        """
        调用 QQ 官方 HTTP API

        通用 API 调用方法，自动处理鉴权 Header 和错误处理。

        Args:
            method: HTTP 方法 (GET / POST / PUT / DELETE)
            path: API 路径，如 "/v2/groups/{guild_id}/messages"
            body: 请求体（可选，仅 POST/PUT 需要）

        Returns:
            成功返回 API 响应数据（dict），失败返回 False

        Raises:
            不会主动抛出异常，异常会被捕获并记录日志
        """
        if not self._session:
            self._logger.error("HTTP 会话未初始化")
            return False

        url = f"{self._api_base}{path}"
        headers = {
            "Authorization": self._auth_header,
            "Content-Type": "application/json",
        }

        try:
            self._logger.debug(f"🌐 调用 QQ API: {method} {path}")

            async with self._session.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                # 成功状态码
                if resp.status in (200, 201, 204):
                    if resp.status == 204:
                        return True
                    result = await resp.json()
                    self._logger.debug(f"📥 API 响应: {result}")
                    return result
                else:
                    error_text = await resp.text()
                    self._logger.error(
                        f"API 请求失败 [HTTP {resp.status}]: {error_text[:200]}"
                    )
                    return False

        except asyncio.TimeoutError:
            self._logger.error(f"API 请求超时: {method} {path}")
            return False
        except aiohttp.ClientError as e:
            self._logger.error(f"API 请求异常: {type(e).__name__}: {e}")
            return False
        except Exception as e:
            self._logger.error(f"API 请求未知错误: {e}", exc_info=True)
            return False

    # ───────────────────── 健康检查 ─────────────────────

    async def health_check(self) -> bool:
        """
        健康检查

        检查适配器是否处于正常运行状态：
        - 运行标志位为 True
        - WebSocket 连接正常
        - 已完成 IDENTIFY 鉴权（_identified=True）
        - 已建立有效 session（_session_id 不为空）

        Returns:
            正常运行返回 True
        """
        return (
            self._running
            and self._ws is not None
            and not self._ws.closed
            and self._identified
            and self._session_id is not None
        )
