import json
from pydantic import BaseModel
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from radio import DroneController
from threading import Lock

REMOTE_IP = "192.168.0.3"
REMOTE_PORT = 14551
LOCAL_PORT = 14550

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
drone_ctl = None
drone_ctl_lock = Lock()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/start")
def start():
    global drone_ctl
    with drone_ctl_lock:
        if drone_ctl is None:
            drone_ctl = DroneController(
                remote_ip=REMOTE_IP,
                remote_port=REMOTE_PORT,
                local_port=LOCAL_PORT
            )
            print("[/start] DroneController instance created and communication started.")
            return {"status": "started"}
        else:
            print("[/start] DroneController already exists.")
            return {"status": "already running"}

@app.post("/stop")
def stop():
    global drone_ctl
    with drone_ctl_lock:
        if drone_ctl is not None:
            drone_ctl.stop()
            drone_ctl = None
            print("[/stop] DroneController stopped and instance deleted.")
            return {"status": "stopped"}
        else:
            print("[/stop] DroneController not running.")
            return {"status": "not running"}
        
@app.get("/status")
def get_status():
    global drone_ctl
    if drone_ctl is None:
        return {"initialized": False, "running": False}
    return {
        "initialized": True,
        "running": drone_ctl.is_running(),
        "target_system": drone_ctl.target_system,
    }

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
    global drone_ctl
    if drone_ctl:
        print('arm pressed')
        drone_ctl.set_arm(True)
    return {"status": "arm command sent"}

@app.post("/disarm")
def disarm():
    global drone_ctl
    if drone_ctl:
        print('disarm pressed')
        drone_ctl.set_arm(False)
    return {"status": "disarm command sent"}

@app.post("/guide")
def set_guide_mode():
    global drone_ctl
    if drone_ctl:
        print('guide pressed')
        drone_ctl.set_mode('GUIDED')
    return {"status": "GUIDED mode set"}

@app.post("/auto")
def set_auto_mode():
    global drone_ctl
    if drone_ctl:
        print('auto pressed')
        drone_ctl.set_mode('AUTO')
    return {"status": "AUTO mode set"}

@app.post("/set-setpoint")
def set_setpoint(setpoint: Setpoint):
    global drone_ctl
    if drone_ctl:
        print("=== /set-setpoint endpoint called ===")
        print(f"  x       = {setpoint.x}")
        print(f"  y       = {setpoint.y}")
        print(f"  z       = {setpoint.z}")
        print(f"  yaw_deg = {setpoint.yaw_deg}")

        drone_ctl.send_guided_position(setpoint.x, setpoint.y, setpoint.z, setpoint.yaw_deg)
        print("Sent setpoint to drone_ctl.")

    return JSONResponse(
        status_code=200,
        content={"status": "success", "message": "Setpoint command sent to drone."}
    )

@app.on_event("startup")
async def startup_event():
    global drone_ctl
    with drone_ctl_lock:
        if drone_ctl is None:
            drone_ctl = DroneController(
                remote_ip=REMOTE_IP,
                remote_port=REMOTE_PORT,
                local_port=LOCAL_PORT
            )
            print("[startup] DroneController instance created and communication started.")
        else:
            print("[startup] DroneController already initialized.")
    print("[startup] FastAPI app started.")

@app.on_event("shutdown")
async def shutdown_event():
    global drone_ctl
    with drone_ctl_lock:
        if drone_ctl:
            drone_ctl.stop()
            drone_ctl = None
            print("[shutdown] DroneController stopped and instance deleted.")