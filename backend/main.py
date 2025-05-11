import json
import socket
import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

UDP_IP = "0.0.0.0"
UDP_PORT = 5001

heart_beat_sending_flag = 

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

app = FastAPI()
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
    
    radio.send(arm)

    print('start pressed')

@app.post("/stop")
def stop():

    radio.send(disarm)

    print('stop pressed')

# --- UDP受信タスク ---
async def udp_receiver():
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(True)
    print(f"UDP server listening on {UDP_IP}:{UDP_PORT}")

    while True:
        try:
            data, addr = await loop.run_in_executor(None, sock.recvfrom, 4096)
            message = data.decode('utf-8', errors='ignore')

            try:
                json_data = json.loads(message)
                print(f"Parsed JSON data:\n{json.dumps(json_data, indent=2)}")

                # ↓ C++ 送信形式 { "pos": [...], "quat": [...] }
                if "pos" in json_data and "quat" in json_data:
                    project.drone_pose = {
                        "position": json_data["pos"],
                        "quaternion": json_data["quat"]
                    }

            except json.JSONDecodeError:
                print("Warning: Received data is not valid JSON")

        except Exception as e:
            print(f"UDP receive error: {type(e).__name__}: {e}")
            await asyncio.sleep(1)

async def send_heart_beat():
    while True:
        await asyncio.sleep(1)
        if heart_beat_sending_flag:

            sock.sendto(packet, dest_addr)

# --- サーバ起動時に並列実行 ---
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(udp_receiver())
    asyncio.create_task(broadcast_drone_pose())

if __name__ == '__main__':
    pass
