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

drone_controller = DroneController(interval=1, host='192.168.0.5', port=5000)
drone_controller.start()

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
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(1)  
            # 座標を更新する関数呼び出し
            project.update_coordinates()
            coordinates = project.get_coordinates()
            await websocket.send_json(coordinates)
    except Exception as e:
        print(f"Connection closed: {e}")
    finally:
        await websocket.close()

@app.get("/coordinates")
async def get_coordinates():
    return JSONResponse(content=project.get_coordinates())

# @app.post("/coordinates")
# async def set_coordinates(request: Request):
#     global coordinates
#     new_coordinates = await request.json()
#     coordinates = new_coordinates
#     return JSONResponse(content=coordinates)

@app.post("/upload/")
async def upload_file(request: Request):
    body = await request.body()
    json_data = body.decode('utf-8')

    data = json.loads(json_data)

    for marker_id in data['landmarks']:
        for i, corner in enumerate(marker_id['corners']):
            id = int(marker_id + str(i))
            project.landmarks_corners.append({"id": id, "x": 0, "y": 0, "z": 0})

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

# @app.get("/data")
# async def get_data():
#     file_path = os.path.join(os.path.dirname(__file__), '..', 'data.json')
#     with open(file_path, 'r') as file:
#         data = json.load(file)
#     return data

# @app.get("setproject/{file_path}")
# async def set_project(file_path):
#     project.set_project(file_path)

# @app.post("setcampos/{file_path}")
# async def set_cam_pos(file_path:str):
#     project.set_cam_pos(file_path)

if __name__ == '__main__':
    pass