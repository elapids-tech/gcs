import json
import socket
import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
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
        self.drone_pose = None

    def add_landmark(self, id, x, y, z):
        self.landmarks.append({"id": id, "x": x, "y": y, "z": z})

    def update_drone_pose(self, position, quaternion):
        self.drone_pose = {
            "position": position,
            "quaternion": quaternion
        }

manager = ConnectionManager()
project = ProjectManager()

radio = Radio(recv_ip="idls_app_backend", recv_port=5001, 
              send_ip="drone", send_port=5000)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_drone_pose())
    print("[startup] broadcast_drone_pose task started")

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
    position = [0.0, 0.0, 0.0]
    quaternion = [0.0, 0.0, 0.0, 1.0]

    while True:
        await asyncio.sleep(0.0167)  # 60 FPS

        type, data = radio.popRxBuffer()
        if type == "DRONE_WORLD_POS":
            position = data[0:3]

        elif type == "DRONE_WORLD_QUAT":
            quaternion = data[0:4]

        drone_pose = {
            "position": position,
            "quaternion": quaternion
        }

        message = {
            "key": "dronePoseUpdate",
            "value": drone_pose
        }
        await manager.broadcast(json.dumps(message))


if __name__ == '__main__':
    pass
