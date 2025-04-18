"""
Agent Connector - Handles communication with the Zapmyco Home Agent
"""

import logging
from typing import Dict, Any, Optional

# 导入模拟 Agent 而不是真实的 Agent
from evaluation.framework.mock.mock_agent import MockZapmycoAgent
from zapmyco.llm import LLMService

logger = logging.getLogger(__name__)


class AgentConnector:
    """
    Connector class for interacting with the Zapmyco Home Agent
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the connector with configuration

        Args:
            config: Configuration for connecting to the agent
        """
        self.config = config
        self.llm_service = LLMService()
        # 使用模拟 Agent 而不是真实的 ZapmycoAgent
        self.agent = MockZapmycoAgent(self.llm_service)
        self._initialized = False
        logger.info("Agent connector created with MockZapmycoAgent")

    async def initialize(self):
        """
        Asynchronously initialize the agent
        """
        if not self._initialized:
            await self.agent.initialize()
            self._initialized = True
            logger.info("Agent connector initialized successfully")

    async def send_request(
        self, data: Dict[str, Any], timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a request to the agent and get the response

        Args:
            data: The request data to send
            timeout: Request timeout in seconds (not used in direct calls)

        Returns:
            The agent's response
        """
        try:
            if not self._initialized:
                await self.initialize()
            return await self.agent.process_request(data.get("text"))
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            raise ValueError(f"Failed to process request: {str(e)}")

    def check_health(self) -> bool:
        """
        Check if the agent is healthy and responding

        Returns:
            True if agent is healthy, False otherwise
        """
        try:
            return self._initialized and self.agent is not None
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    async def close(self):
        """
        关闭连接并清理资源
        """
        logger.info("关闭 Agent Connector...")

        # 如果有其他需要清理的资源，可以在这里添加

        # 标记为未初始化
        self._initialized = False
