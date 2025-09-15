import json
import asyncio
from pydantic import BaseModel
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from threading import Lock
import cv2
import numpy as np
from datetime import datetime
from backend.mavlink_client import MavlinkClient

mavlink_client = MavlinkClient()

clients = set()

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

class Setpoint(BaseModel):
    x: float
    y: float
    z: float
    yaw_deg: float

manager = ConnectionManager()

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

@app.websocket("/ws/video")
async def video_stream(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            # テスト用ダミーフレームを作成する。
            frame = np.full((480, 640, 3), 200, dtype=np.uint8)  # 480x640, RGB, 灰色

            # 現在時刻を描画する。
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame,
                now,
                (50, 240),  # 位置
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 0, 0),  # 黒文字
                2,
                cv2.LINE_AA,
            )

            # JPEGに変換 
            _, jpeg = cv2.imencode(".jpg", frame)
            data = jpeg.tobytes()

            await websocket.send_bytes(data)

            # 15fps
            await asyncio.sleep(1 / 15)

    except WebSocketDisconnect:
        print("クライアント切断")
    except Exception as e:
        print(f"予期せぬエラー: {e}")
    finally:
        pass

async def periodic_task():
    """
    30hzでmavlink clientのtelemetry情報を取得し、websocketで送信する。
    """
    while True:
        position = mavlink_client.get_drone_position()
        quaternion = mavlink_client.get_drone_quaternion()

        # 現状sysidは1に固定。将来的に複数ドローンに対応する。
        sysid = 1
        drone_pose = { "key":"dronePoseUpdate" ,
                      "value": { "sysid": sysid,
                      "position": list(position),
                      "quaternion": list(quaternion)}}

        await manager.broadcast(json.dumps(drone_pose))

        await asyncio.sleep(0.0333)  # 30 FPS

@app.post("/start")
def start():
    print("[/start] start endpoint called")

@app.post("/stop")
def stop():
    print("[/stop] stop endpoint called")    

@app.post("/arm")
def arm():
    print('arm pressed')
    return {"status": "arm command sent"}

@app.post("/disarm")
def disarm():
    print('disarm pressed')
    return {"status": "disarm command sent"}

@app.post("/guide")
def set_guide_mode():
    print('guide pressed')
    return {"status": "GUIDED mode set"}

@app.post("/auto")
def set_auto_mode():
    print('auto pressed')
    return {"status": "AUTO mode set"}

@app.post("/set-setpoint")
def set_setpoint(setpoint: Setpoint):
    print("=== /set-setpoint endpoint called ===")
    print(f"  x       = {setpoint.x}")
    print(f"  y       = {setpoint.y}")
    print(f"  z       = {setpoint.z}")
    print(f"  yaw_deg = {setpoint.yaw_deg}")
    
    return JSONResponse(
        status_code=200,
        content={"status": "success", "message": "Setpoint command sent to drone."}
    )

@app.post("/config-mode/keep-alive")
def send_enable_config_mode_signal():
    mavlink_client.set_config_mode_signal()
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    print("[startup] FastAPI app started.")
    asyncio.create_task(periodic_task())
    print("[startup] periodic_task started as background task.")

@app.on_event("shutdown")
async def shutdown_event():
    mavlink_client.stop()
    print("[shutdown] Mavlink client stopped.")