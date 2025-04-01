import asyncio
import json
import os
import websockets
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


async def connect_to_hass():
    uri = f"ws://{os.getenv('HASS_URL')}/api/websocket"
    access_token = os.getenv("HASS_ACCESS_TOKEN")
    if not access_token:
        raise ValueError("请在 .env 文件中设置 HASS_ACCESS_TOKEN")

    async with websockets.connect(uri) as websocket:
        # 认证
        auth_response = await websocket.recv()
        await websocket.send(
            json.dumps(
                {
                    "type": "auth",
                    "access_token": access_token,
                }
            )
        )
        auth_result = await websocket.recv()
        print("认证结果:", auth_result)

        # 订阅事件
        await websocket.send(
            json.dumps(
                {"id": 1, "type": "subscribe_events", "event_type": "state_changed"}
            )
        )
        print("已订阅状态变更事件")

        # 持续接收事件
        while True:
            response = await websocket.recv()
            print(json.loads(response))


if __name__ == "__main__":
    asyncio.run(connect_to_hass())
