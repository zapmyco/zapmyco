from fastapi import FastAPI, WebSocket
from api import router, devices_router
from db import Base, engine
from starlette.websockets import WebSocketDisconnect
from services.mi_api import set_device_state

app = FastAPI()

# Create database tables
Base.metadata.create_all(bind=engine)

# Register routes
app.include_router(router)
app.include_router(devices_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            
            # Set value based on client message
            value = data.strip() == "1"
            
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

    # This mode enables direct debugging when running the file
    print("Starting server in debug mode...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
