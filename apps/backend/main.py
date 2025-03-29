from fastapi import FastAPI, WebSocket
from api import router, devices_router
from db import Base, engine
from starlette.websockets import WebSocketDisconnect
from services.mi_api import set_device_state
import debugpy; 

app = FastAPI()

# Create database tables
Base.metadata.create_all(bind=engine)

# Register routes
app.include_router(router)
app.include_router(devices_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print("WebSocket连接请求到达")
    await websocket.accept()
    print("WebSocket连接已接受")
    try:
        while True:
            print("等待接收WebSocket消息...")
            data = await websocket.receive_text()
            print(f"收到原始消息: '{data}'")
            
            # Set value based on client message
            value = data.strip() == "1"
            print(f"处理后的值: {value}")
            
            # Call Xiaomi API service
            response = await set_device_state(
                device_id="1132894958",
                siid=2,
                piid=1,
                value=value
            )
            print(f"API response: {response}")
            
            print(f"Message received: {data}")  # Add log output
            await websocket.send_text(f"Server received message: {data}")
    except WebSocketDisconnect:
        print("Client disconnected")  # Add log output
    except Exception as e:
        print(f"Error occurred: {str(e)}")  # Add log output
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    
    print("Starting FastAPI server in debugging mode...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
