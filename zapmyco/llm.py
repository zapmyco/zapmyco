import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import openai
from typing import TypedDict, Optional
from openai.types.chat import ChatCompletion

from zapmyco.config import settings


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
        self.tools = [
            # {
            #     "type": "function",
            #     "function": {
            #         "name": "handle_light",
            #         "description": "控制灯泡的开关",
            #         "parameters": {
            #             "type": "object",
            #             "properties": {
            #                 "state": {"type": "string", "enum": ["on", "off"]}
            #             },
            #         },
            #     },
            # },
            # {
            #     "type": "function",
            #     "function": {
            #         "name": "handle_air_conditioner",
            #         "description": "控制空调的开关",
            #         "parameters": {
            #             "type": "object",
            #             "properties": {
            #                 "state": {"type": "string", "enum": ["on", "off"]}
            #             },
            #         },
            #     },
            # },
            {
                "type": "function",
                "function": {
                    "name": "call_service",
                    "description": "调用家庭设备服务",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "domain": {
                                "type": "string",
                                "enum": ["light", "switch", "camera", "climate"],
                                "description": "服务域名，只能是 light、switch 或 camera",
                            },
                            "service": {
                                "type": "string",
                                "enum": [
                                    "turn_on",
                                    "turn_off",
                                    "set_color",
                                    "set_brightness",
                                    "set_temperature",
                                ],
                                "description": "设备服务",
                            },
                            "service_data": {
                                "type": "object",
                                "description": "设备服务数据",
                                "properties": {
                                    "entity_id": {
                                        "type": "string",
                                        "description": "设备ID",
                                    },
                                    "color": {
                                        "type": "string",
                                        "description": "颜色，只能是 red、green 或 blue",
                                    },
                                    "brightness": {
                                        "type": "integer",
                                        "description": "亮度，只能是 0-100",
                                    },
                                    "temperature": {
                                        "type": "integer",
                                        "description": "温度，只能是 16-30",
                                    },
                                    "hvac_mode": {
                                        "type": "string",
                                        "description": "HVAC 模式，只能是 heat、cool 或 auto",
                                    },
                                },
                            },
                        },
                    },
                },
            },
        ]

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
            tools=self.tools,
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
