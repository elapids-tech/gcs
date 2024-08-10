import json
import os
import time
import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from typing import Dict

from drone_controller import DroneController

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
    def __init__(self) -> None:
        self.last_update = time.time()
        self.coordinates = {"x": 0, "y": 0, "z": 0}
        self.landmarks_corners = []

    def update_coordinates(self):
        if self.coordinates['x'] == 10:
            self.coordinates['x'] = 0
            self.coordinates['y'] = 0
            self.coordinates['z'] = 0
        else:
            self.coordinates['x'] += 1
            self.coordinates['y'] += 1
            self.coordinates['z'] += 1

        self.last_update = time.time()

    def get_coordinates(self):
        return self.coordinates

drone_controller = DroneController(interval=0.01, host='192.168.0.6', port=5000)
drone_controller.start()

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
            result = drone_controller.get_drone_attitude_axis()
            if result == None:
                continue

            data = {
                "key": "dronePosUpdate",
                "value": result
            }
            
            print('send json data:', data)
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(0.016) 

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket disconnected") 


@app.post("/upload/")
async def upload_file(request: Request):
    body = await request.body()
    json_data = body.decode('utf-8')

    data = json.loads(json_data)

    project.landmarks_corners.clear()

    for marker_id in data['landmarks']:
        for i, pos in enumerate(data['landmarks'][marker_id]['corners']):
            id = str(marker_id) + str(i)
            project.landmarks_corners.append({"id":id, "x":pos[0], "y":pos[1], "z":pos[2]})

    await manager.broadcast(json.dumps(project.landmarks_corners))

    return {"state_message": 0}

@app.post("/start")
def start():
    print('start pressed')
    drone_controller.set_drone_state(1)
    print(f'drone_state:{drone_controller.drone_state}')
    return {"status": f"{drone_controller.drone_state}"}

@app.post("/stop")
def stop():
    print('stop pressed')
    drone_controller.set_drone_state(0)
    print(f'drone_state:{drone_controller.drone_state}')
    return {"status": f"{drone_controller.drone_state}"}

if __name__ == '__main__':
    pass