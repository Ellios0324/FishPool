"""
Skill 类 - AgentSkills 的统一对外接口

提供简便的方式创建和使用 Coding Agent。
"""

import os
from typing import Optional

from dotenv import load_dotenv

from .core.llm_client import LLMClient
from .core.agent import Agent

load_dotenv()


class Skill:
    """Coding Agent Skill 类

    封装了 LLM 客户端和 Agent 核心逻辑，
    提供简洁的 API 供外部调用。

    用法:
        skill = Skill()
        reply = skill.process("读取当前目录下的所有文件")
        print(reply)

        # 或以交互模式运行
        skill.run()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-flash",
        temperature: float = 0.3,
    ):
        """初始化 Skill

        Args:
            api_key: API 密钥，默认从环境变量 DEEPSEEK_API_KEY 读取
            base_url: API 基础地址
            model: 模型名称
            temperature: 生成温度
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = base_url
        self.model = model
        self.temperature = temperature

        # 创建 LLM 客户端
        self.llm_client = LLMClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            temperature=self.temperature,
        )

        # 创建 Agent
        self.agent = Agent(llm_client=self.llm_client)

    def process(self, user_input: str) -> str:
        """处理用户输入并返回回复

        Args:
            user_input: 用户输入的文本

        Returns:
            Agent 的文本回复
        """
        return self.agent.process_message(user_input)

    def run(self):
        """以交互式对话模式运行 Agent"""
        self.agent.run_interactive()

    def reset(self):
        """重置对话历史"""
        self.agent.reset_conversation()
