import json
import os
import shutil
import signal
import time
import socket
import threading
from fastapi import FastAPI, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from typing import Dict


class Project:
    camPos = {}

    def __init__(self) -> None:
        pass

    def set_project(file_path):
        pass

    def set_cam_pos(file_path):
        print(file_path)


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
                    print(f"Sent: {send_data}")
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


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Reactアプリが動作するポートを指定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

proj = Project()

drone_control = DroneControl(interval=0.5, host='drone', port=5000)
drone_control.start()

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

@app.get("setproject/{file_path}")
async def set_project(file_path):
    proj.set_project(file_path)

@app.post("setcampos/{file_path}")
async def set_cam_pos(file_path:str):
    proj.set_cam_pos(file_path)

@app.post("/upload/")
async def upload_file(request: Request):
    body = await request.body()
    text = body.decode('utf-8') 

    lines = text.splitlines()

    for i, line in enumerate(lines):
        print(line)
        # Project.camPos = {'{i}':}
        # if count == 20:
        #     stripped_line = line.strip()
        #     if stripped_line != "None":
        #         float_list = [float(value) for value in stripped_line.split(',')]
        #         result.append(float_list)
        #         count = 0
        # else:
        #     count += 1

    # for i in range(len(result)):
    #     cx = result[i][0]
    #     cy = result[i][2]
    #     cz = -result[i][1]

    #     v_xx = result[i][3]
    #     v_xy = result[i][5]
    #     v_xz = -result[i][4]

    #     v_yx = result[i][6]
    #     v_yy = result[i][8]
    #     v_yz = -result[i][7]

    #     v_zx = result[i][9]
    #     v_zy = result[i][11]
    #     v_zz = -result[i][10]
    return {"received_content": body.decode('utf-8')}

# class Position(BaseModel):
#     x: float
#     y: float
#     z: float

# @app.post("/pos_send")
# async def pos_send(pos: Dict[str, float]):
#     print(type(pos))
#     print(pos)
#     wifi.udp_send(pos)
#     # return {"received_data": pos}