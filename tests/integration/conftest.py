import pytest
import os
import asyncio
from integrations.home_assistant.main import HomeAssistantClient


@pytest.fixture
async def real_ha_client(ha_config):
    """创建一个连接到实际 HomeAssistant 的客户端"""
    # 从环境变量覆盖配置
    config = ha_config.copy()
    if "HA_BASE_URL" in os.environ:
        config["base_url"] = os.environ["HA_BASE_URL"]
    if "HA_ACCESS_TOKEN" in os.environ:
        config["access_token"] = os.environ["HA_ACCESS_TOKEN"]

    client = HomeAssistantClient(config)
    connected = await client.connect()

    if not connected:
        await client.disconnect()
        pytest.skip("无法连接到 Home Assistant")

    yield client

    await client.disconnect()
