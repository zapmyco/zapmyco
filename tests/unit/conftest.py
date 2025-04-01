import pytest
from unittest.mock import MagicMock, patch
import asyncio


@pytest.fixture
def mock_ha_client():
    """创建一个模拟的 HomeAssistant 客户端"""
    client = MagicMock()
    client.connect = asyncio.coroutine(lambda: True)
    client.disconnect = asyncio.coroutine(lambda: None)
    client.call_service = asyncio.coroutine(
        lambda domain, service, **kwargs: {"success": True}
    )
    client.get_state = asyncio.coroutine(
        lambda entity_id: {"state": "on", "attributes": {}}
    )
    return client
