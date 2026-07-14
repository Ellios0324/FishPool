"""
FishPool 统一消息数据模型

定义跨平台消息的标准数据结构，所有适配器均使用此模型
进行消息的接收与发送。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Optional


class PlatformType(Enum):
    """支持的平台类型枚举"""

    QQ = "qq"
    WECHAT = "wechat"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    DINGTALK = "dingtalk"
    SLACK = "slack"
    TERMINAL = "terminal"  # 本地终端/CLI

    @classmethod
    def from_string(cls, name: str) -> "PlatformType":
        """从字符串解析平台类型，不区分大小写"""
        name_lower = name.lower().strip()
        for member in cls:
            if member.value == name_lower or member.name.lower() == name_lower:
                return member
        raise ValueError(f"未知的平台类型: {name}，可选: {[m.value for m in cls]}")


class MessageType(Enum):
    """消息类型枚举"""

    TEXT = "text"             # 纯文本
    IMAGE = "image"           # 图片
    VOICE = "voice"           # 语音
    VIDEO = "video"           # 视频
    FILE = "file"             # 文件
    AT = "at"                 # @消息
    REPLY = "reply"           # 回复消息
    RICH = "rich"             # 富文本/卡片
    SYSTEM = "system"         # 系统消息


@dataclass
class Message:
    """
    统一消息数据模型

    所有平台的消息在进入 FishPool 系统前，都会被转换为此标准格式。
    发送消息时，适配器将此模型转换为各平台的特定格式。

    Attributes:
        platform: 来源平台类型
        message_id: 平台消息唯一ID
        sender_id: 发送者ID
        sender_name: 发送者昵称/显示名
        group_id: 群聊ID（私聊为 None）
        group_name: 群聊名称（可选）
        content: 消息文本内容
        raw_content: 原始消息内容（含格式标记等）
        message_type: 消息类型（文本/图片/等）
        is_group: 是否为群聊消息
        is_at: 是否 @ 了机器人
        reply_to_id: 被回复的消息ID（可选）
        timestamp: 消息时间戳
        extra: 扩展字段，存储平台特定信息
    """

    platform: PlatformType
    message_id: str
    sender_id: str
    sender_name: str
    content: str
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    raw_content: Optional[str] = None
    message_type: MessageType = MessageType.TEXT
    is_group: bool = False
    is_at: bool = False
    reply_to_id: Optional[str] = None
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.raw_content is None:
            self.raw_content = self.content

    @property
    def is_private(self) -> bool:
        """是否为私聊消息"""
        return not self.is_group

    @property
    def chat_id(self) -> str:
        """获取会话ID（用于发送回复）"""
        return self.group_id if self.is_group else self.sender_id

    @property
    def brief(self) -> str:
        """消息摘要，用于日志"""
        chat_type = "群聊" if self.is_group else "私聊"
        chat_name = f"[{self.group_name}]" if self.group_name else ""
        return (
            f"[{self.platform.value}]"
            f"{chat_type}{chat_name}"
            f"{self.sender_name}({self.sender_id}): "
            f"{self.content[:50]}..."
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "platform": self.platform.value,
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "group_id": self.group_id,
            "group_name": self.group_name,
            "content": self.content,
            "message_type": self.message_type.value,
            "is_group": self.is_group,
            "is_at": self.is_at,
            "timestamp": self.timestamp,
        }

    @classmethod
    def create_text(
        cls,
        platform: PlatformType,
        sender_id: str,
        sender_name: str,
        content: str,
        *,
        group_id: Optional[str] = None,
        group_name: Optional[str] = None,
        is_at: bool = False,
        **kwargs,
    ) -> "Message":
        """便捷方法：创建文本消息"""
        return cls(
            platform=platform,
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            group_id=group_id,
            group_name=group_name,
            is_group=group_id is not None,
            is_at=is_at,
            **kwargs,
        )


# 消息处理器类型签名
MessageHandler = Callable[[Message], Coroutine[Any, Any, Optional[str]]]
