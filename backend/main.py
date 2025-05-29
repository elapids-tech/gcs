import json
import socket
import asyncio
from pydantic import BaseModel
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from radio import DroneController

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

class DroneState:
    def __init__(self):
        self.position = [0.0, 0.0, 0.0]
        self.quaternion = [0.0, 0.0, 0.0, 1.0]

class Setpoint(BaseModel):
    x: float
    y: float
    z: float
    yaw_deg: float

manager = ConnectionManager()
project = ProjectManager()
drone_ctl = DroneController(
    remote_ip='192.168.0.3',     # ← Raspberry Pi の IP
    remote_port=14551,
    local_port=14550
)

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
    drone_ctl.start()
    asyncio.create_task(periodic_task())
    print("[startup] periodic_task started.")

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

@app.post("/arm")
def arm():
    print('arm pressed')
    drone_ctl.set_arm(True)

@app.post("/disarm")
def disarm():
    print('disarm pressed')
    drone_ctl.set_arm(False)

@app.post("/guide")
def set_guide_mode():
    print('guide pressed')
    drone_ctl.set_mode('GUIDED')

@app.post("/auto")
def set_auto_mode():
    print('auto pressed')
    drone_ctl.set_mode('AUTO')

@app.post("/set-setpoint")
def set_setpoint(setpoint: Setpoint):
    print("=== /set-setpoint endpoint called ===")
    print(f"Received setpoint:")
    print(f"  x       = {setpoint.x}")
    print(f"  y       = {setpoint.y}")
    print(f"  z       = {setpoint.z}")
    print(f"  yaw_deg = {setpoint.yaw_deg}")

    drone_ctl.send_guided_position(setpoint.x, setpoint.y, setpoint.z, setpoint.yaw_deg)
    print("Sent setpoint to drone_ctl.\n")

    return JSONResponse(
        status_code=200,
        content={"status": "success", "message": "Setpoint command sent to drone."}
    )

@app.post("/start")
def start():
    print('start pressed')

@app.post("/stop")
def stop():
    print('stop pressed')

async def periodic_task():
    while True:
        await asyncio.sleep(0.0167)  # 60 FPS

        

        # control（無線）クラスから受信したデータを内部クラスに格納

        # control（無線）クラスから受信したデータをフロントエンドに送信する

@app.on_event("shutdown")
async def shutdown_event():
    drone_ctl.stop()

if __name__ == '__main__':
    pass
