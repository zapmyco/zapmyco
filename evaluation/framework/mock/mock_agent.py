"""
Mock Zapmyco Agent for evaluation purposes
"""

import logging
from typing import Dict, Any, Optional

from zapmyco.llm import LLMService


class MockZapmycoAgent:
    """
    Mock version of ZapmycoAgent that doesn't connect to Home Assistant
    Used for evaluation to test LLM responses only
    """

    def __init__(self, llm_service: LLMService):
        """
        Initialize the mock agent
        
        Args:
            llm_service: LLM service for generating responses
        """
        self.llm_service = llm_service
        self.logger = logging.getLogger("MockZapmycoAgent")
        
        # 不创建真实的 Home Assistant 客户端和 MCP
        self.ha_client = None
        self.ha_mcp = None

    async def initialize(self):
        """初始化 Agent - 不需要连接到 Home Assistant"""
        self.logger.info("Mock Zapmyco Agent initialized successfully")
        return True

    async def process_request(self, user_input: str):
        """
        处理用户请求 - 直接调用 LLM 服务，不需要 Home Assistant 上下文
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            LLM 响应
        """
        try:
            # 创建一个模拟的上下文
            mock_context = self._create_mock_context(user_input)
            
            # 调用 LLM 获取响应
            return await self.llm_service.get_response(user_input, mock_context)
            
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_mock_context(self, query: str) -> Dict[str, Any]:
        """
        创建模拟的上下文数据
        
        Args:
            query: 用户查询
            
        Returns:
            模拟的上下文数据
        """
        # 创建基本的模拟设备状态
        mock_states = [
            {
                "entity_id": "light.living_room",
                "state": "off",
                "attributes": {"friendly_name": "客厅灯", "brightness": 0},
            },
            {
                "entity_id": "climate.living_room",
                "state": "off",
                "attributes": {
                    "friendly_name": "客厅空调",
                    "temperature": 24,
                    "hvac_modes": ["heat", "cool", "off"],
                },
            },
            {
                "entity_id": "switch.kitchen",
                "state": "off",
                "attributes": {"friendly_name": "厨房开关"},
            },
        ]
        
        # 创建模拟的设备能力
        mock_capabilities = {
            "light.living_room": {
                "actions": ["turn_on", "turn_off", "toggle"],
                "attributes": ["brightness", "color_temp", "rgb_color"],
            },
            "climate.living_room": {
                "actions": ["set_temperature", "set_hvac_mode", "turn_on", "turn_off"],
                "attributes": ["temperature", "hvac_mode", "fan_mode"],
            },
            "switch.kitchen": {
                "actions": ["turn_on", "turn_off", "toggle"],
                "attributes": [],
            },
        }
        
        # 创建模拟的区域信息
        mock_areas = {
            "living_room": {"name": "客厅", "entities": ["light.living_room", "climate.living_room"]},
            "kitchen": {"name": "厨房", "entities": ["switch.kitchen"]},
        }
        
        # 构建上下文
        context = {
            "device_states": mock_states,
            "device_capabilities": mock_capabilities,
            "areas": mock_areas,
        }
        
        return context
