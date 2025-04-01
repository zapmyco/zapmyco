import os
import httpx
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Home Assistant的URL和访问令牌
hass_url = "http://localhost:8123"
access_token = os.getenv("HASS_ACCESS_TOKEN")
if not access_token:
    raise ValueError("请在 .env 文件中设置 HASS_ACCESS_TOKEN")

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
}


async def get_states():
    async with httpx.AsyncClient(proxies=None) as client:
        response = await client.get(f"{hass_url}/api/states", headers=headers)
        return response.json()


async def turn_on_light(entity_id: str):
    async with httpx.AsyncClient(proxies=None) as client:
        payload = {"entity_id": entity_id}
        response = await client.post(
            f"{hass_url}/api/services/light/turn_on", headers=headers, json=payload
        )
        return response.json()


async def main():
    # 获取所有实体的状态
    states = await get_states()
    print("所有实体状态:", states)

    # 调用服务示例（打开灯）
    result = await turn_on_light("light.living_room")
    print("开灯结果:", result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
