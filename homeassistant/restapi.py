import requests

# Home Assistant的URL和访问令牌
hass_url = "http://localhost:8123"
token = "your_long_lived_access_token"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

# 获取所有实体的状态
response = requests.get(f"{hass_url}/api/states", headers=headers)
print(response.json())

# 调用服务示例（打开灯）
payload = {"entity_id": "light.living_room"}
response = requests.post(
    f"{hass_url}/api/services/light/turn_on", headers=headers, json=payload
)
