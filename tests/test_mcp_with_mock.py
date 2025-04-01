import pytest
from zapmyco.integrations.home_assistant.mcp import HomeAssistantMCP
from zapmyco.integrations.home_assistant.context_provider import MockContextProvider

# 模拟数据
MOCK_HOME_ASSISTANT_DATA = {
    "states": [
        {
            "entity_id": "light.living_room",
            "state": "on",
            "attributes": {
                "friendly_name": "客厅灯",
                "brightness": 255,
                "color_temp": 300,
            },
        },
        {
            "entity_id": "switch.bedroom",
            "state": "off",
            "attributes": {"friendly_name": "卧室开关"},
        },
    ],
    "entity_registry": {
        "light.living_room": {
            "name": "客厅灯",
            "capabilities": {"supported_features": ["brightness", "color_temp"]},
            "area_id": "living_room",
        },
        "switch.bedroom": {
            "name": "卧室开关",
            "capabilities": {},
            "area_id": "bedroom",
        },
    },
    "area_registry": {"living_room": {"name": "客厅"}, "bedroom": {"name": "卧室"}},
}


@pytest.mark.asyncio
async def test_get_context_with_mock():
    # 创建模拟上下文提供者
    mock_provider = MockContextProvider(MOCK_HOME_ASSISTANT_DATA)

    # 创建 MCP 实例（ha_client 可以是 None，因为我们使用模拟提供者）
    mcp = HomeAssistantMCP(None, context_provider=mock_provider)

    # 测试获取上下文
    context = await mcp.get_context()

    # 验证返回的上下文
    assert len(context["device_states"]) == 2
    assert context["device_states"][0]["entity_id"] == "light.living_room"
    assert context["device_states"][1]["entity_id"] == "switch.bedroom"

    # 验证区域信息
    assert "living_room" in context["areas"]
    assert context["areas"]["living_room"]["name"] == "客厅"

    # 验证设备能力
    assert "light.living_room" in context["device_capabilities"]
    capabilities = context["device_capabilities"]["light.living_room"]
    assert "actions" in capabilities
    assert "turn_on" in capabilities["actions"]


@pytest.mark.asyncio
async def test_get_context_with_specific_entities():
    mock_provider = MockContextProvider(MOCK_HOME_ASSISTANT_DATA)
    mcp = HomeAssistantMCP(None, context_provider=mock_provider)

    # 测试获取特定实体的上下文
    context = await mcp.get_context(entities=["light.living_room"])

    # 验证只返回了指定的实体
    assert len(context["device_states"]) == 1
    assert context["device_states"][0]["entity_id"] == "light.living_room"
