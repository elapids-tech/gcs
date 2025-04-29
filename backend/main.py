import json
import os
import time
import asyncio
import socket
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict

UDP_IP = "0.0.0.0"  # 受信を許可するIPアドレス (すべて)
UDP_PORT = 5001     # 受信ポート番号

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

class ProjectManager:
    def __init__(self):
        self.landmarks = []

    def add_landmark(self, id, x, y, z):
        self.landmarks.append({"id": id, "x": x, "y": y, "z": z})

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
            data = await websocket.receive_text()
            await manager.broadcast(f"Message from client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket disconnected") 

@app.post("/upload/")
async def upload_file(request: Request):
    print('upload_file')
    body = await request.body()
    json_data = body.decode('utf-8')

    data = json.loads(json_data)

    project.landmarks.clear()

    for landmark in data:
        id = str(landmark['id'])
        pos = landmark['center']
        project.landmarks.append({"id": id, "x": pos[0], "y": pos[1], "z": pos[2]})

    send_data = {"key": "setLandmarks", "value": project.landmarks}
    print(send_data)
    await manager.broadcast(json.dumps(send_data))

    return {"state_message": 0}

@app.post("/upload-image")
async def upload_image(request: Request):
    pass

@app.post("/start")
def start():
    print('start pressed')
    # drone_controller.set_drone_state(1)

@app.post("/stop")
def stop():
    print('stop pressed')
    # drone_controller.set_drone_state(0)

async def udp_receiver():
    loop = asyncio.get_running_loop()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(True)  # blockingにする

    print(f"UDP server listening on {UDP_IP}:{UDP_PORT}")

    while True:
        try:
            # 別スレッドでブロッキングrecvfromを実行
            data, addr = await loop.run_in_executor(None, sock.recvfrom, 4096)
            message = data.decode('utf-8', errors='ignore')
            print(f"Received UDP raw data from {addr}: {message}")

            try:
                json_data = json.loads(message)
                print(f"Parsed JSON data:\n{json.dumps(json_data, indent=2)}")
            except json.JSONDecodeError:
                print("Warning: Received data is not valid JSON")

        except Exception as e:
            print(f"UDP receive critical error: {type(e).__name__}: {e}")
            await asyncio.sleep(1)

# --- サーバ起動時にudp_receiverも一緒に走らせる ---
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(udp_receiver())

if __name__ == '__main__':
    pass
