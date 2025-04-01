import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import openai
from typing import TypedDict, Optional, List, Dict, Any
from openai.types.chat import ChatCompletion

from zapmyco.config import settings
from zapmyco.mcp_servers.home_assistant import MCPHomeAssistant


class LLMService:
    def __init__(self):
        # Use settings from the config module
        self.config = {
            "base_url": settings.LLM_BASE_URL,
            "api_key": settings.LLM_API_KEY,
        }
        # Validate that necessary configs are present
        if not self.config["api_key"]:
            raise ValueError(
                "DASHSCOPE_API_KEY must be set in the environment or .env file."
            )
        if not self.config["base_url"]:
            # Should have a default, but good to check
            raise ValueError("LLM_BASE_URL must be set (although it has a default).")

        self.system_prompt = """
        你是一个家庭助理，你需要根据用户的语音输入，调节对应的家庭设备
        """.strip()

    async def get_response(self, user_input: str, context: dict) -> ChatCompletion:
        """
        根据用户输入和上下文获取 LLM 的响应。

        Args:
            user_input: 用户输入的字符串。
            context: Home Assistant 环境上下文。
        """
        prompt = self._build_prompt(user_input, context)
        llm_raw_response = await self._call_llm_api(prompt)
        parsed_response = self._parse_llm_response(llm_raw_response)
        return parsed_response

    def _build_prompt(self, user_input: str, context: dict) -> str:
        prompt = f"""
        当前上下文：{context}
        用户输入：{user_input}
        """
        return prompt

    async def _call_llm_api(self, prompt: str) -> openai.types.chat.ChatCompletion:
        client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        list_tools = await MCPHomeAssistant.list_tools()
        tools = []
        for tool in list_tools:
            # 解析inputSchema，可能是JSON字符串或已经是字典
            input_schema = tool.inputSchema
            if isinstance(input_schema, str):
                try:
                    input_schema = json.loads(input_schema)
                except json.JSONDecodeError:
                    print(f"无法解析工具 {tool.name} 的inputSchema: {input_schema}")
                    continue

            # 处理schema中的$defs和$ref
            properties = input_schema.get("properties", {})
            defs = input_schema.get("$defs", {})

            # 展开properties中的$ref引用
            expanded_properties = {}
            for prop_name, prop_value in properties.items():
                if (
                    prop_value.get("type") == "array"
                    and "items" in prop_value
                    and "$ref" in prop_value["items"]
                ):
                    # 获取引用的定义名称
                    ref_path = prop_value["items"]["$ref"]
                    if ref_path.startswith("#/$defs/"):
                        ref_name = ref_path.split("/")[-1]
                        if ref_name in defs:
                            # 创建新的展开后的property
                            expanded_properties[prop_name] = {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": defs[ref_name].get("properties", {}),
                                    "required": defs[ref_name].get("required", []),
                                },
                            }
                        else:
                            # 如果找不到引用，保留原始属性
                            expanded_properties[prop_name] = prop_value
                else:
                    # 对于没有$ref的属性，直接保留
                    expanded_properties[prop_name] = prop_value

            # 构建OpenAI格式的工具定义
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            "type": input_schema.get("type", "object"),
                            "properties": expanded_properties,
                            "required": input_schema.get("required", []),
                        },
                    },
                }
            )
        completion = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": self.system_prompt,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            tools=tools,
            stream=False,
        )
        return completion

    def _parse_llm_response(
        self, llm_raw_response: openai.types.chat.ChatCompletion
    ) -> dict:
        """将 LLM 响应转换为 JSON 格式

        Args:
            llm_raw_response: ChatCompletion 对象

        Returns:
            JSON 格式的响应
        """
        return llm_raw_response.to_dict()


if __name__ == "__main__":
    import asyncio

    async def main():
        llm_service = LLMService()
        res = await llm_service.get_response("你好", {})
        print(res)

    asyncio.run(main())
