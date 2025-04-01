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


class MockHomeAssistantClient:
    """Home Assistant 客户端的模拟实现"""

    def __init__(self, mock_data):
        self.mock_data = mock_data

    async def get_states(self, entities=None):
        states = self.mock_data["states"]
        if entities:
            return [state for state in states if state["entity_id"] in entities]
        return states

    async def get_entity_registry(self):
        return self.mock_data["entity_registry"]

    async def get_area_registry(self):
        return self.mock_data["area_registry"]

    async def call_service(self, **kwargs):
        return {"success": True, "message": "模拟服务调用成功"}
