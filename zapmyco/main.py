import logging
import json
from typing import Optional

from integrations.home_assistant.main import HomeAssistantClient
from zapmyco.llm import LLMService
from zapmyco.voice import AsyncVoiceService


class ZapmycoAgent:
    """Zapmyco Home Agent with Home Assistant MCP"""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.logger = logging.getLogger("ZapmycoAgent")

        # 初始化 Home Assistant 客户端
        self.ha_client = HomeAssistantClient()

        # 初始化语音服务
        self.voice_service = AsyncVoiceService()

        # 语音监听状态
        self.is_voice_listening = False
        self.voice_task = None

    async def initialize(self):
        """初始化 Agent"""
        # 连接到 Home Assistant
        connected = await self.ha_client.connect()
        if not connected:
            self.logger.error("Failed to connect to Home Assistant")
            return False

        self.logger.info("Zapmyco Agent initialized successfully")
        return True

    async def start_voice_listening(self, wake_word: Optional[str] = None):
        """
        开始语音监听。

        Args:
            wake_word: 唤醒词，如果设置，则只有在检测到唤醒词后才会开始处理
        """
        if self.is_voice_listening:
            self.logger.warning("语音监听已经启动")
            return

        # 启动语音服务
        await self.voice_service.start(wake_word=wake_word)
        self.is_voice_listening = True
        self.logger.info("语音监听已启动")

    async def stop_voice_listening(self):
        """停止语音监听。"""
        if not self.is_voice_listening:
            return

        # 停止语音服务
        await self.voice_service.stop()
        self.is_voice_listening = False
        self.logger.info("语音监听已停止")

    async def listen_and_process(self):
        """监听语音并处理请求。"""
        if not self.is_voice_listening:
            await self.start_voice_listening()

        try:
            # 等待语音识别结果
            self.logger.info("等待语音输入...")
            text = await self.voice_service.get_text()
            self.logger.info(f"识别到语音: {text}")

            # 处理请求
            if text:
                response = await self.process_request(text)
                self.logger.info(f"处理结果: {response}")
                return response

        except Exception as e:
            self.logger.error(f"语音处理错误: {str(e)}")
            return {"success": False, "error": str(e)}

    async def process_request(self, user_input: str):
        """处理用户请求"""
        try:
            # 获取 MCP 上下文
            states = await self.ha_client.get_states()
            entity_registry = await self.ha_client.get_entity_registry()
            area_registry = await self.ha_client.get_area_registry()

            context = {
                "states": states,
                "entity_registry": entity_registry,
                "area_registry": area_registry,
            }

            # 调用 LLM 获取控制指令
            response = await self.llm_service.get_response(user_input, context)

            if None is response["response"]["choices"]:
                return response

            # 检查是否有工具调用
            choices = response["response"]["choices"]
            if not choices or not choices[0].get("message", {}).get("tool_calls"):
                return response

            # 获取工具调用
            tool_calls = choices[0]["message"]["tool_calls"]

            # 处理每个工具调用
            results = []
            for tool_call in tool_calls:
                # 获取工具名称和参数
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])

                # 根据工具名称调用对应的 MCP 工具
                from zapmyco.mcp_servers.home_assistant import MCPHomeAssistant

                try:
                    # 调用 MCP 工具
                    result = await MCPHomeAssistant.call_tool(tool_name, tool_args)
                    results.append(
                        {
                            "success": True,
                            "tool": tool_name,
                            "args": tool_args,
                            "result": result,
                        }
                    )
                except Exception as e:
                    self.logger.error(f"调用工具 {tool_name} 失败: {str(e)}")
                    results.append(
                        {
                            "success": False,
                            "tool": tool_name,
                            "args": tool_args,
                            "error": str(e),
                        }
                    )

            # 构建响应
            final_response = {
                "success": (
                    any(result["success"] for result in results) if results else False
                ),
                "message": "已处理工具调用",
                "llm_response": response,
                "tool_results": results,
            }

            return final_response

        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            return {"success": False, "error": str(e)}


if __name__ == "__main__":

    import asyncio
    from dotenv import load_dotenv

    load_dotenv()

    async def main():
        # 创建服务
        llm_service = LLMService()
        agent = ZapmycoAgent(llm_service)

        # 初始化 Agent
        if not await agent.initialize():
            print("初始化失败")
            return

        # 示例1: 直接处理文本请求
        print("\n=== 示例1: 直接处理文本请求 ===")
        res = await agent.process_request("关掉小灯")

        # 打印处理结果
        print(f"处理结果: {res}")

        # # 示例2: 使用语音输入（需要麦克风）
        # print("\n=== 示例2: 使用语音输入 ===")
        # print("请对着麦克风说话，例如'打开客厅灯'...")

        # try:
        #     # 启动语音监听
        #     await agent.start_voice_listening()

        #     # 监听并处理一次请求
        #     voice_res = await agent.listen_and_process()
        #     print(f"语音处理结果: {voice_res}")

        # finally:
        #     # 停止语音监听
        #     await agent.stop_voice_listening()

        # print("\n处理完成")

    # 运行主函数
    asyncio.run(main())
