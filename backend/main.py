import json
import asyncio
import socket
import contextlib
from typing import Optional

from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.mavlink_client import MavlinkClient


# 設定値
UDP_FRAME_RECEIVE_IP = "0.0.0.0"
UDP_FRAME_RECEIVE_PORT = 5001
UDP_MAX_PAYLOAD = 65507  # UDPで実効安全な最大ペイロード
VIDEO_FPS = 15  # /ws/video で送るフレームレート


class ConnectionManager:
    """テキストメッセージ用のWebSocket接続を管理する。"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"[WebSocket] send error: {e}")
                dead.append(connection)
        for d in dead:
            self.disconnect(d)


class Setpoint(BaseModel):
    x: float
    y: float
    z: float
    yaw_deg: float


# FastAPI 準備
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()
mavlink_client = MavlinkClient()

# 最新フレーム（JPEGバイト列）を保持
latest_frame: Optional[bytes] = None
frame_lock = asyncio.Lock()

# UDPソケットと受信タスク（起動時に初期化）
udp_sock: Optional[socket.socket] = None
udp_task: Optional[asyncio.Task] = None


def create_udp_socket() -> socket.socket:
    """UDPソケットを1つだけ生成して使い回す。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((UDP_FRAME_RECEIVE_IP, UDP_FRAME_RECEIVE_PORT))
    sock.setblocking(False)
    print(f"[udp] bound on {UDP_FRAME_RECEIVE_IP}:{UDP_FRAME_RECEIVE_PORT}")
    return sock


async def udp_frame_receiver():
    """
    Raspberry Pi からのフレームを常時受信し、latest_frame を更新する。
    前提：1フレーム = 1 UDP データグラム（JPEGバイト列）
    """
    global latest_frame
    loop = asyncio.get_running_loop()
    assert udp_sock is not None, "udp_sock is not initialized"

    try:
        while True:
            data, addr = await loop.sock_recvfrom(udp_sock, UDP_MAX_PAYLOAD)
            async with frame_lock:
                latest_frame = data
    except asyncio.CancelledError:
        print("[udp] receiver task cancelled")
        raise
    except Exception as e:
        print(f"[udp] receiver error: {e}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print("[/ws] WebSocket connection established")
    try:
        while True:
            # 必要に応じてクライアントからのメッセージを処理
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("[/ws] WebSocket disconnected")
    except Exception as e:
        manager.disconnect(websocket)
        print(f"[/ws] error: {e}")
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


@app.websocket("/ws/video")
async def video_stream(websocket: WebSocket):
    """クライアント接続中のみ、最新フレーム（JPEG）を送信する。"""
    await websocket.accept()
    print("[/ws/video] client connected")
    try:
        interval = 1.0 / float(VIDEO_FPS)
        while True:
            await asyncio.sleep(interval)
            async with frame_lock:
                frame = latest_frame
            if frame is not None:
                await websocket.send_bytes(frame)
    except WebSocketDisconnect:
        print("[/ws/video] client disconnected")
    except Exception as e:
        print(f"[/ws/video] error: {e}")
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


async def periodic_task():
    """30HzでMAVLinkテレメトリを取得し、/ws にブロードキャストする。"""
    try:
        while True:
            position = mavlink_client.get_drone_position()
            quaternion = mavlink_client.get_drone_quaternion()

            sysid = 1  # いまは固定。将来的に複数ドローン対応
            drone_pose = {
                "key": "dronePoseUpdate",
                "value": {
                    "sysid": sysid,
                    "position": list(position),
                    "quaternion": list(quaternion),
                },
            }

            await manager.broadcast(json.dumps(drone_pose))
            await asyncio.sleep(1.0 / 30.0)
    except asyncio.CancelledError:
        print("[periodic_task] cancelled")
        raise
    except Exception as e:
        print(f"[periodic_task] error: {e}")


@app.post("/start")
def start():
    print("[/start] start endpoint called")
    return {"status": "ok", "message": "start called"}


@app.post("/stop")
def stop():
    print("[/stop] stop endpoint called")
    return {"status": "ok", "message": "stop called"}


@app.post("/arm")
def arm():
    print("[/arm] arm pressed")
    return {"status": "ok", "message": "arm command sent"}


@app.post("/disarm")
def disarm():
    print("[/disarm] disarm pressed")
    return {"status": "ok", "message": "disarm command sent"}


@app.post("/guide")
def set_guide_mode():
    print("[/guide] guide pressed")
    return {"status": "ok", "message": "GUIDED mode set"}


@app.post("/auto")
def set_auto_mode():
    print("[/auto] auto pressed")
    return {"status": "ok", "message": "AUTO mode set"}


@app.post("/set-setpoint")
def set_setpoint(setpoint: Setpoint):
    print("=== /set-setpoint endpoint called ===")
    print(f"  x       = {setpoint.x}")
    print(f"  y       = {setpoint.y}")
    print(f"  z       = {setpoint.z}")
    print(f"  yaw_deg = {setpoint.yaw_deg}")
    return JSONResponse(
        status_code=200,
        content={"status": "success", "message": "Setpoint command sent to drone."},
    )


@app.post("/config-mode/keep-alive")
def send_enable_config_mode_signal():
    mavlink_client.set_config_mode_signal()
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    """アプリ起動時の初期化（UDP受信とテレメトリ送信タスクの起動）。"""
    global udp_sock, udp_task
    print("[startup] FastAPI app starting...")

    try:
        udp_sock = create_udp_socket()
    except OSError as e:
        print(f"[startup] UDP socket bind failed: {e}")
        raise

    udp_task = asyncio.create_task(udp_frame_receiver())
    print("[startup] udp_frame_receiver started")

    asyncio.create_task(periodic_task())
    print("[startup] periodic_task started")


@app.on_event("shutdown")
async def shutdown_event():
    """アプリ終了時の後始末。"""
    print("[shutdown] stopping...")

    if udp_task is not None:
        udp_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await udp_task

    if udp_sock is not None:
        with contextlib.suppress(Exception):
            udp_sock.close()

    with contextlib.suppress(Exception):
        mavlink_client.stop()

    print("[shutdown] resources cleaned up.")
