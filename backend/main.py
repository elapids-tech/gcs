import json
import os
import time
import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from typing import Dict

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
        self.landmarks.append({"id":id, "x": x, "y": y, "z": z})

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
        project.landmarks.append({"id":id, "x":pos[0], "y":pos[1], "z":pos[2]})

    send_data = {"key":"setLandmarks", "value":project.landmarks}
    print(send_data)
    await manager.broadcast(json.dumps(send_data))

    return {"state_message": 0}

@app.post("/upload-image")
async def upload_imgae(request: Request):
    pass
    


@app.post("/start")
def start():
    print('start pressed')
    # drone_controller.set_drone_state(1)
    # print(f'drone_state:{drone_controller.drone_state}')
    # return {"status": f"{drone_controller.drone_state}"}

@app.post("/stop")
def stop():
    print('stop pressed')
    # drone_controller.set_drone_state(0)
    # print(f'drone_state:{drone_controller.drone_state}')
    # return {"status": f"{drone_controller.drone_state}"}

if __name__ == '__main__':
    pass