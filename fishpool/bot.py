"""
FishPool Bot 主入口

整合适配器管理器与 Agent 调度器，实现：
- QQ 消息 → 意图解析 → Agent 处理 → 回复
- 微信消息 → 意图解析 → Agent 处理 → 回复

启动方式：
    python -m fishpool.bot                    # 默认配置
    python -m fishpool.bot --config config.yaml  # 指定配置
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import yaml

from fishpool.adapters import AdapterManager, BaseAdapter, Message, PlatformType
from fishpool.adapters.qq_adapter import QQAdapter
from fishpool.adapters.qq_official_adapter import QQOfficialAdapter
from fishpool.adapters.wechat_adapter import WeChatAdapter
from fishpool.core.dispatcher import AgentDispatcher

# ── 日志配置 ──

LOG_FORMAT = (
    "[%(asctime)s] [%(levelname)s] "
    "[%(name)s] %(message)s"
)
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO"):
    """配置日志系统"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("fishpool.log", encoding="utf-8"),
        ],
    )


# ── 配置加载 ──

DEFAULT_CONFIG = {
    "bot": {
        "name": "FishPool",
        "version": "0.2.0",
        "log_level": "INFO",
    },
    "adapters": {
        "qq": {
            "enabled": True,
            "protocol": "onebot_v11",
            "ws_url": "ws://localhost:8080/ws",
            "bot_qq": "",
            "reconnect_interval": 5,
            "max_reconnect_retries": -1,
        },
        # ── QQ 官方机器人 API（推荐，无需第三方框架）──
        "qq_official": {
            "enabled": False,
            "mode": "websocket",
            "app_id": "",
            "app_secret": "",
            "token": "",
            "sandbox": True,
            "reconnect_interval": 5,
            "max_reconnect_retries": -1,
        },
        "wechat": {
            "enabled": False,
            "protocol": "wcf",
            "host": "127.0.0.1",
            "port": 10086,
            "poll_interval": 1.0,
        },
    },
}


def load_config(config_path: Optional[str] = None) -> dict:
    """
    加载配置文件

    优先级：环境变量 > 配置文件 > 默认配置
    """
    config = DEFAULT_CONFIG.copy()

    # 1. 从指定路径加载
    if config_path:
        path = Path(config_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    _deep_merge(config, file_config)
            print(f"📂 加载配置文件: {config_path}")
        else:
            print(f"⚠️ 配置文件不存在: {config_path}，使用默认配置")
    else:
        # 尝试从常见路径加载
        for candidate in ["config.yaml", "config.yml", "configs/config.yaml"]:
            path = Path(candidate)
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        _deep_merge(config, file_config)
                print(f"📂 加载配置文件: {candidate}")
                break

    # 2. 环境变量覆盖（ADAPTERS_QQ_WS_URL 等）
    _apply_env_overrides(config)

    return config


def _deep_merge(base: dict, overlay: dict):
    """深度合并字典"""
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _apply_env_overrides(config: dict, prefix: str = ""):
    """
    从环境变量覆盖配置

    例如：ADAPTERS_QQ_WS_URL → config["adapters"]["qq"]["ws_url"]

    支持的环境变量前缀：
    - FISHPOOL_ (默认)
    - 完整路径匹配，如 FISHPOOL_ADAPTERS_QQ_OFFICIAL_APP_ID
    """
    if not prefix:
        prefix = "FISHPOOL_"

    for key, value in config.items():
        env_key = f"{prefix}{key.upper()}"
        if isinstance(value, dict):
            _apply_env_overrides(value, f"{env_key}_")
            continue

        env_val = os.environ.get(env_key)
        if env_val is not None:
            # 类型转换
            if isinstance(value, bool):
                config[key] = env_val.lower() in ("true", "1", "yes")
            elif isinstance(value, int):
                config[key] = int(env_val)
            elif isinstance(value, float):
                config[key] = float(env_val)
            else:
                config[key] = env_val
            print(f"🔧 环境变量覆盖: {env_key}={config[key]}")


# ── Bot 主类 ──


class FishPoolBot:
    """
    FishPool 机器人主类

    整合消息适配器与 Agent 调度逻辑。
    """

    def __init__(self, config: dict):
        self.config = config
        self.name = config.get("bot", {}).get("name", "FishPool")
        self.logger = logging.getLogger("fishpool.bot")

        # 核心组件
        self.dispatcher = AgentDispatcher()
        self.adapter_manager = AdapterManager(config.get("adapters", {}))

        # 运行状态
        self._running = False

    def setup(self):
        """
        初始化系统组件

        1. 创建并注册适配器
        2. 设置消息处理器（路由到调度器）
        3. 注册内置 Agent
        """
        self.logger.info(f"🐟 {self.name} v{self.config.get('bot', {}).get('version', '?')} 初始化中...")

        # ── 1. 注册适配器 ──
        self._setup_adapters()

        # ── 2. 设置消息处理器 ──
        self.adapter_manager.set_message_handler(self._on_message)

        # ── 3. 注册 Agent ──
        self._setup_agents()

        self.logger.info("✅ FishPool Bot 初始化完成")

    def _setup_adapters(self):
        """根据配置创建并注册消息适配器"""
        adapters_config = self.config.get("adapters", {})

        # ── QQ 适配器（基于 OneBot v11 协议，旧方案）──
        # 需要 NapCatQQ / Lagrange 等第三方框架配合
        qq_config = adapters_config.get("qq", {})
        if qq_config.get("enabled", True):
            qq_adapter = QQAdapter("qq", qq_config)
            self.adapter_manager.register(qq_adapter)
            self.logger.info(f"  📱 QQ适配器 (OneBot) 已注册 -> {qq_config.get('ws_url', 'N/A')}")

        # ── QQ 官方机器人 API 适配器（推荐方案）──
        # 直接使用 QQ 开放平台官方 API，无需第三方框架
        # 配置方式：在 https://q.qq.com/ 创建机器人应用
        qq_official_config = adapters_config.get("qq_official", {})
        if qq_official_config.get("enabled", False):
            # 检查必填配置
            app_id = qq_official_config.get("app_id", "")
            token = qq_official_config.get("token", "")
            if not app_id or not token:
                self.logger.warning(
                    "  ⚠️ QQ官方适配器已启用但配置不完整（缺少 app_id 或 token），跳过注册"
                )
            else:
                qq_official_adapter = QQOfficialAdapter("qq_official", qq_official_config)
                self.adapter_manager.register(qq_official_adapter)
                sandbox = qq_official_config.get("sandbox", True)
                env_name = "沙箱" if sandbox else "正式"
                self.logger.info(
                    f"  🤖 QQ官方适配器 (API) 已注册 -> "
                    f"APPID={app_id[:8]}..., {env_name}环境"
                )

        # 微信适配器
        wx_config = adapters_config.get("wechat", {})
        if wx_config.get("enabled", False):
            wx_adapter = WeChatAdapter("wechat", wx_config)
            self.adapter_manager.register(wx_adapter)
            protocol = wx_config.get("protocol", "wcf")
            host = wx_config.get("host", "127.0.0.1")
            port = wx_config.get("port", 10086)
            self.logger.info(f"  💬 微信适配器已注册 -> {protocol}://{host}:{port}")

    def _setup_agents(self):
        """注册内置 Agent"""
        # 这里注册实际的 Agent 实现
        # 当前为空，由 dispatcher 的 _mock_agent_response 提供模拟响应
        self.logger.info("  🤖 Agent 调度器已就绪 (模拟模式)")

    async def _on_message(self, message: Message) -> Optional[str]:
        """
        消息处理器（适配器层 → Agent 调度层）

        所有平台的消息都会经过此方法处理。
        """
        self.logger.info(f"📨 收到消息: [{message.platform.value}] {message.sender_name}: {message.content[:60]}")

        # 只响应 @ 机器人的群消息 或 私聊消息
        if message.is_group and not message.is_at:
            self.logger.debug("群聊消息未 @ 机器人，忽略")
            return None

        # 调用调度器处理
        try:
            reply = await self.dispatcher.dispatch(message)
            if reply:
                self.logger.info(f"📤 回复: {reply[:60]}...")
            return reply
        except Exception as e:
            self.logger.error(f"消息处理失败: {e}", exc_info=True)
            return f"😅 抱歉，处理消息时出错了: {str(e)}"

    async def run(self):
        """
        启动 Bot

        1. 初始化组件
        2. 启动所有适配器
        3. 等待关闭信号
        """
        self.setup()
        self._running = True

        self.logger.info("=" * 50)
        self.logger.info(f"🐟 {self.name} is now running!")
        self.logger.info(f"📱 适配器: {self.adapter_manager.adapter_count} 个已注册")
        self.logger.info("=" * 50)
        print()
        print(f"  🐟 {self.name} 已启动！")
        print(f"  📱 适配器数量: {self.adapter_manager.adapter_count}")
        print(f"  💡 按 Ctrl+C 停止")
        print()

        # 启动适配器
        await self.adapter_manager.start_all()

        # 等待关闭
        try:
            await self.adapter_manager.wait_for_shutdown()
        except KeyboardInterrupt:
            self.logger.info("收到 KeyboardInterrupt")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """关闭 Bot"""
        self.logger.info("🛑 正在关闭 FishPool Bot...")
        self._running = False
        await self.adapter_manager.stop_all()
        self.logger.info("👋 FishPool Bot 已关闭")


# ── 命令行入口 ──


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="🐟 FishPool - 多 Agent 智能系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m fishpool.bot                     # 使用默认配置启动
  python -m fishpool.bot --config prod.yaml  # 使用生产配置
  python -m fishpool.bot --log DEBUG         # 调试模式
        """,
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="配置文件路径 (YAML格式)",
    )
    parser.add_argument(
        "--log", "-l",
        type=str,
        default=None,
        help="日志级别 (DEBUG/INFO/WARNING/ERROR)",
    )
    parser.add_argument(
        "--qq-only",
        action="store_true",
        help="仅启动 QQ 适配器",
    )
    parser.add_argument(
        "--wechat-only",
        action="store_true",
        help="仅启动微信适配器",
    )
    parser.add_argument(
        "--generate-config",
        action="store_true",
        help="生成示例配置文件",
    )
    return parser.parse_args()


def generate_example_config():
    """生成示例配置文件"""
    import yaml

    config = {
        "bot": {
            "name": "FishPool",
            "version": "0.2.0",
            "log_level": "INFO",
        },
        "adapters": {
            "qq": {
                "enabled": True,
                "protocol": "onebot_v11",
                "ws_url": "ws://localhost:8080/ws",
                "bot_qq": "123456789",
                "reconnect_interval": 5,
                "max_reconnect_retries": -1,
            },
            "qq_official": {
                "enabled": False,
                "mode": "websocket",
                "app_id": "",
                "app_secret": "",
                "token": "",
                "sandbox": True,
                "reconnect_interval": 5,
                "max_reconnect_retries": -1,
            },
            "wechat": {
                "enabled": False,
                "protocol": "wcf",
                "host": "127.0.0.1",
                "port": 10086,
                "poll_interval": 1.0,
                "admin_users": [],
            },
        },
    }

    path = Path("config.example.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"✅ 示例配置文件已生成: {path}")


def main():
    """主入口"""
    args = parse_args()

    # 生成示例配置
    if args.generate_config:
        generate_example_config()
        return

    # 加载配置
    config = load_config(args.config)

    # 设置日志级别
    log_level = args.log or config.get("bot", {}).get("log_level", "INFO")
    setup_logging(log_level)

    # 处理 --qq-only / --wechat-only
    if args.qq_only:
        config["adapters"]["qq"]["enabled"] = True
        config["adapters"]["wechat"]["enabled"] = False
    elif args.wechat_only:
        config["adapters"]["qq"]["enabled"] = False
        config["adapters"]["wechat"]["enabled"] = True

    # 启动 Bot
    bot = FishPoolBot(config)

    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
