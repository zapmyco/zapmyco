from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any


class ContextProvider(ABC):
    """Home Assistant 上下文提供者接口"""

    @abstractmethod
    async def get_states(
        self, query: Optional[str] = None, entities: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """获取设备状态"""
        pass

    @abstractmethod
    async def get_entity_registry(self) -> Dict[str, Any]:
        """获取实体注册表"""
        pass

    @abstractmethod
    async def get_area_registry(self) -> Dict[str, Any]:
        """获取区域注册表"""
        pass


class DefaultContextProvider(ContextProvider):
    """默认的上下文提供者实现，使用实际的 Home Assistant 客户端"""

    def __init__(self, ha_client):
        self.ha_client = ha_client

    async def get_states(
        self, query: Optional[str] = None, entities: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        return await self.ha_client.get_states(entities)

    async def get_entity_registry(self) -> Dict[str, Any]:
        return await self.ha_client.get_entity_registry()

    async def get_area_registry(self) -> Dict[str, Any]:
        return await self.ha_client.get_area_registry()


class MockContextProvider(ContextProvider):
    """模拟的上下文提供者实现，用于测试"""

    def __init__(self, mock_data: Dict[str, Any]):
        self.mock_data = mock_data

    async def get_states(
        self, query: Optional[str] = None, entities: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        states = self.mock_data.get("states", [])
        if entities:
            return [state for state in states if state["entity_id"] in entities]
        return states

    async def get_entity_registry(self) -> Dict[str, Any]:
        return self.mock_data.get("entity_registry", {})

    async def get_area_registry(self) -> Dict[str, Any]:
        return self.mock_data.get("area_registry", {})
