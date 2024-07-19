from fastapi import FastAPI, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from typing import List
from typing import Dict
import radio
import shutil

class Project:
    camPos = {}

    def __init__(self) -> None:
        pass

    def set_project(file_path):
        pass

    def set_cam_pos(file_path):
        print(file_path)

proj = Project()
app = FastAPI()
wifi = radio.Wifi(drone_ip="192.168.0.2", port=5000)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Reactアプリが動作するポートを指定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.post("/start")
def start():
    print('start')
    return {"status": "started"}

@app.post("/pause")
def pause():
    print('pause')
    return {"status": "paused"}

@app.post("/exit")
def exit():
    print('exit')
    return {"status": "exited"}

@app.post("/disarm")
def disarm():
    print('disarm')
    return {"status": "disarmed"}


# class Position(BaseModel):
#     x: float
#     y: float
#     z: float

@app.post("/pos_send")
async def pos_send(pos: Dict[str, float]):
    print(type(pos))
    print(pos)
    wifi.udp_send(pos)
    # return {"received_data": pos}


@app.get("/read_project")
async def read_project():
    return {"message": "Project data"}