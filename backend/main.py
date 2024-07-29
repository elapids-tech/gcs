import json
import os
import time
import socket
import threading
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from typing import Dict


from pydantic import BaseModel
import asyncio


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

coordinates = {"x": 0, "y": 0, "z": 0}

@app.get("/coordinates")
async def get_coordinates():
    return JSONResponse(content=coordinates)

@app.post("/coordinates")
async def set_coordinates(request: Request):
    global coordinates
    new_coordinates = await request.json()
    coordinates = new_coordinates
    return JSONResponse(content=coordinates)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(1)  # 1秒ごとに更新
            # 座標を更新する関数呼び出し
            update_coordinates()
            await websocket.send_json(coordinates)
    except Exception as e:
        print(f"Connection closed: {e}")
    finally:
        await websocket.close()

def update_coordinates():
    global coordinates
    if coordinates['x'] == 10:
        coordinates['x'] = 0
        coordinates['y'] = 0
        coordinates['z'] = 0
    else:
        coordinates['x'] += 1
        coordinates['y'] += 1
        coordinates['z'] += 1



class DroneControl:
    def __init__(self, interval=1, host='192.168.0.1', port=5000, recv_port=5001):
        self.drone_state = 0
        self.interval = interval
        self.host = host
        self.port = port
        self.recv_port = recv_port
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.received_data = None

    def start(self):
        self.send_thread = threading.Thread(target=self._send, daemon=True)
        self.recv_thread = threading.Thread(target=self._receive, daemon=True)
        self.send_thread.start()
        self.recv_thread.start()

    def stop(self):
        self.stop_event.set()
        self.send_thread.join()
        self.recv_thread.join()    
    
    def set_drone_state(self, state: int):
        with self.lock:
            self.drone_state = state
            print(f"Drone state set to: {self.drone_state}")

    def get_received_data(self):
        with self.lock:
            return self.received_data

    def _send(self):
        while not self.stop_event.is_set():
            send_data = {'time': time.time(), 'state': self.drone_state}
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    json_data = json.dumps(send_data)
                    sock.sendto(json_data.encode('utf-8'), (self.host, self.port))
            except Exception as e:
                print(f"Error sending data: {e}")
            time.sleep(self.interval)

    def _receive(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(('', self.recv_port))
            while not self.stop_event.is_set():
                try:
                    data, addr = sock.recvfrom(1024)
                    received_message = json.loads(data.decode('utf-8'))
                    with self.lock:
                        self.received_data = received_message
                    print(f"Received: {received_message} from {addr}")
                except Exception as e:
                    print(f"Error receiving data: {e}")


drone_control = DroneControl(interval=1, host='192.168.0.5', port=5000)
drone_control.start()

@app.post("/upload/")
async def upload_file(request: Request):
    body = await request.body()
    json_data = body.decode('utf-8')

    # json.loadsを使用して文字列から辞書に変換
    data = json.loads(json_data)

    # keyの一覧を表示
    for i in data:
        print(i)
    
    return {"received_content": json_data}

@app.post("/start")
def start():
    print('start pressed')
    drone_control.set_drone_state(1)
    print(f'drone_state:{drone_control.drone_state}')
    return {"status": f"{drone_control.drone_state}"}

@app.post("/stop")
def stop():
    print('stop pressed')
    drone_control.set_drone_state(0)
    print(f'drone_state:{drone_control.drone_state}')
    return {"status": f"{drone_control.drone_state}"}

@app.get("/data")
async def get_data():
    file_path = os.path.join(os.path.dirname(__file__), '..', 'data.json')
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

# @app.get("setproject/{file_path}")
# async def set_project(file_path):
#     project.set_project(file_path)

# @app.post("setcampos/{file_path}")
# async def set_cam_pos(file_path:str):
#     project.set_cam_pos(file_path)

