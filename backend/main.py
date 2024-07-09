from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from typing import List
from typing import Dict
# from pydantic import BaseModel

import radio

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