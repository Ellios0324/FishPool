"""
FishPool 消息适配器模块

提供统一的跨平台消息接入能力，支持 QQ、微信等多种消息平台。
"""

from .message import Message, PlatformType
from .base import BaseAdapter
from .manager import AdapterManager
from .qq_official_adapter import QQOfficialAdapter

__all__ = [
    "Message",
    "PlatformType",
    "BaseAdapter",
    "AdapterManager",
    "QQOfficialAdapter",
]
