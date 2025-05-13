import json
import socket
import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from radio import Radio

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"WebSocket send error: {e}")
                self.disconnect(connection)

class ProjectManager:
    def __init__(self):
        self.landmarks = []
        self.drone_pose = None  # ← 追加

    def add_landmark(self, id, x, y, z):
        self.landmarks.append({"id": id, "x": x, "y": y, "z": z})

    def update_drone_pose(self, position, quaternion):
        self.drone_pose = {
            "position": position,
            "quaternion": quaternion
        }

manager = ConnectionManager()
project = ProjectManager()

# drone からの UDP を5001番で受信し、5000番に送信する
radio = Radio(recv_ip="idls_app_backend", recv_port=5001, 
              send_ip="drone", send_port=5000)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    task2 = asyncio.create_task(broadcast_drone_pose())
    
    yield  # この yield の後に shutdown 処理を書くことができる

    # Shutdown
    task2.cancel()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print("WebSocket connection established") 
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket disconnected") 

@app.post("/upload/")
async def upload_file(request: Request):
    body = await request.body()
    data = json.loads(body.decode('utf-8'))

    project.landmarks.clear()
    for landmark in data:
        id = str(landmark['id'])
        pos = landmark['center']
        project.landmarks.append({"id": id, "x": pos[0], "y": pos[1], "z": pos[2]})

    send_data = {"key": "setLandmarks", "value": project.landmarks}
    await manager.broadcast(json.dumps(send_data))
    return {"state_message": 0}

@app.post("/upload-image")
async def upload_image(request: Request):
    pass

@app.post("/start")
def start():
    radio.send_immediate("CONTROL_PACKET", "ARM")
    print('start pressed')

@app.post("/stop")
def stop():
    radio.send_immediate("CONTROL_PACKET", "DISARM")
    print('stop pressed')

async def broadcast_drone_pose():
    while True:
        await asyncio.sleep(0.0167)  # 60 FPS
        type, data = radio.popRxBuffer()

        if type == "DRONE_WORLD_POS":
            message = {
                "key": "dronePositionUpdate",
                "value": data
            }
            await manager.broadcast(json.dumps(message))

        elif type == "DRONE_WORLD_QUAT":
            message = {
                "key": "dronePoseUpdate",
                "value": data
            }
            await manager.broadcast(json.dumps(message))

if __name__ == '__main__':
    pass
