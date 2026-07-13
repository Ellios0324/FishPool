"""
LLM 客户端封装模块

负责与 DeepSeek API（兼容 OpenAI 格式）的通信，
提供流式调用和工具调用累积功能。
"""

import json
import os
from typing import Optional

from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class LLMClient:
    """LLM 客户端封装类"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-flash",
        temperature: float = 0.3,
    ):
        """初始化 LLM 客户端

        Args:
            api_key: API 密钥，默认为环境变量 DEEPSEEK_API_KEY
            base_url: API 基础地址
            model: 模型名称
            temperature: 生成温度
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = base_url
        self.model = model
        self.temperature = temperature

        if not self.api_key:
            raise ValueError(
                "API key is required. Set DEEPSEEK_API_KEY in .env or pass api_key."
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def stream_chat_with_tools(self, messages: list, tools: list) -> dict:
        """流式调用 LLM API，实时打印文本内容并累积 tool_calls

        Args:
            messages: 对话消息列表
            tools: 工具定义列表（JSON Schema 格式）

        Returns:
            完整的 assistant message dict，格式：
            {
                "role": "assistant",
                "content": "..." or None,
                "tool_calls": [...]  # 如果有的话
            }
        """
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=self.temperature,
            stream=True,
        )

        content_parts: list[str] = []
        # 按 index 累积 tool_calls：{index: {id, function_name, arguments_str}}
        tool_calls_accum: dict[int, dict] = {}

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            # 流式打印文本内容
            if delta.content:
                content_parts.append(delta.content)
                print(delta.content, end="", flush=True)

            # 累积 tool_calls
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_accum:
                        tool_calls_accum[idx] = {
                            "id": "",
                            "function": {"name": "", "arguments": ""},
                        }

                    entry = tool_calls_accum[idx]

                    if tc_delta.id:
                        entry["id"] = tc_delta.id

                    if tc_delta.function:
                        if tc_delta.function.name:
                            entry["function"]["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            entry["function"]["arguments"] += tc_delta.function.arguments

        # 构建标准 assistant message dict
        content = "".join(content_parts).strip()

        # 按 index 排序构建 tool_calls 列表
        tool_calls_list = []
        for idx in sorted(tool_calls_accum.keys()):
            tc = tool_calls_accum[idx]
            tool_calls_list.append(
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    },
                }
            )

        assistant_msg: dict = {
            "role": "assistant",
            "content": content if content else None,
        }
        if tool_calls_list:
            assistant_msg["tool_calls"] = tool_calls_list

        return assistant_msg
