import logging

from zapmyco.integrations.home_assistant.mcp import HomeAssistantMCP
from zapmyco.integrations.home_assistant.client import HomeAssistantClient
from zapmyco.llm import LLMService


class ZapmycoAgent:
    """Zapmyco Home Agent with Home Assistant MCP"""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.logger = logging.getLogger("ZapmycoAgent")

        # 初始化 Home Assistant 客户端
        self.ha_client = HomeAssistantClient()

        # 初始化 Home Assistant MCP
        self.ha_mcp = HomeAssistantMCP(self.ha_client)

    async def initialize(self):
        """初始化 Agent"""
        # 连接到 Home Assistant
        connected = await self.ha_client.connect()
        if not connected:
            self.logger.error("Failed to connect to Home Assistant")
            return False

        self.logger.info("Zapmyco Agent initialized successfully")
        return True

    async def process_request(self, user_input: str):
        """处理用户请求"""
        try:
            # 获取 MCP 上下文
            context = await self.ha_mcp.get_context(query=user_input)

            # 调用 LLM 获取控制指令
            return await self.llm_service.get_response(user_input, context)
            # if not llm_response["success"]:
            #     return {"success": False, "error": llm_response["error"]}

            # 如果没有执行指令，直接返回响应
            # if None is llm_response["response"]["choices"]:
            #     return {
            #         "success": True,
            #         "message": "No execution required",
            #         "response": llm_response,
            #     }

            # return {
            #     "success": True,
            #     "response": llm_response,
            # }
            # result = await self.ha_mcp.execute_intent(
            #     llm_response["response"]["choices"][0]["message"]["tool_calls"][0]
            # )

            # # 构建响应
            # response = {
            #     "success": result["success"],
            #     "message": result.get("message", ""),
            #     "execution": {
            #         "device": result.get("device"),
            #         "action": result.get("action"),
            #         "service_called": result.get("service_called"),
            #     },
            #     "device_state": result.get("new_state"),
            # }

            # if not result["success"]:
            #     response["error"] = result.get("error", "Unknown error")

            # return response

        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            return {"success": False, "error": str(e)}


if __name__ == "__main__":

    import os
    import asyncio
    from dotenv import load_dotenv

    load_dotenv()

    async def main():
        llm_service = LLMService()
        agent = ZapmycoAgent(llm_service)
        await agent.initialize()
        res = await agent.process_request("关掉小灯")
        print(res)

    asyncio.run(main())
