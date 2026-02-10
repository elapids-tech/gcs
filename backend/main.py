import json
import time
import asyncio
import socket
import contextlib
import traceback
from typing import Optional

import cv2
import numpy as np
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect, WebSocketState

from backend.drone_settings import DroneSettings
from backend.mavlink_client import MavlinkClient

try:
    from uvicorn.protocols.utils import ClientDisconnected
except ImportError:
    class ClientDisconnected(Exception):
        pass 

# カメラフレームストリーミング 受信設定
UDP_FRAME_RECEIVE_IP = "0.0.0.0"
UDP_FRAME_RECEIVE_PORT = 5001
UDP_MAX_PAYLOAD = 65507
VIDEO_FPS = 15
VIDEO_TIMEOUT_SEC = 3.0
PLACEHOLDER_DEFAULT_SIZE = (1600, 600)  # (w, h)


class ConnectionManager:
    """テレメトリ用のWebSocket接続管理"""
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    def _is_connected(self, ws: WebSocket) -> bool:
        # Starlette 5系なら WebSocketState.CONNECTED。古い場合は属性が無いこともあるので防御的に。
        try:
            return ws.client_state == WebSocketState.CONNECTED
        except Exception:
            return True  # 状態が取れない実装でも送ってみてだめならexceptで外す

    async def broadcast(self, message: str):
        # 送信中に書き換えられないようコピーで回す
        stale: list[WebSocket] = []
        for ws in list(self.active_connections):
            # 明らかに切れてるものは送らない
            if not self._is_connected(ws):
                stale.append(ws)
                continue
            try:
                await ws.send_text(message)
            except (WebSocketDisconnect, ClientDisconnected, RuntimeError):
                # 予想どおりの切断は静かに回収（ログを汚さない）
                stale.append(ws)
            except Exception as e:
                # 想定外だけ軽く1行ログ（スタックトレースは出さない）
                print(f"[WebSocket] unexpected send error: {type(e).__name__}: {e}")
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)



class Setpoint(BaseModel):
    x: float
    y: float
    z: float
    yaw_deg: float


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()
mavlink_client = MavlinkClient(host="192.168.0.6")
drone_settings = DroneSettings()

# 受信した最新フレーム（JPEGバイト列と受信時刻）
latest_frame: Optional[dict] = None  # {"data": bytes, "ts": float}
frame_lock = asyncio.Lock()

# プレースホルダー画像（常にJPEGで持つ）
placeholder_jpeg: Optional[bytes] = None
placeholder_size: tuple[int, int] = PLACEHOLDER_DEFAULT_SIZE  # (w, h)
last_frame_size: Optional[tuple[int, int]] = None  # 実フレームサイズが判明したら更新

# UDP受信のTransport/Protocol
udp_transport: Optional[asyncio.DatagramTransport] = None
udp_protocol: Optional["UdpReceiverProtocol"] = None

def build_placeholder(size: tuple[int, int], text: str = "NO CONNECTION") -> bytes:
    """指定サイズにラベルを描いたJPEGプレースホルダーを作成"""
    w, h = size
    img = np.full((h, w, 3), 32, dtype=np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 2.2
    thickness = 4
    text_size, _ = cv2.getTextSize(text, font, scale, thickness)
    tx = (w - text_size[0]) // 2
    ty = (h + text_size[1]) // 2
    cv2.putText(img, text, (tx, ty), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)

    sub = "Waiting for UDP frames..."
    sub_size, _ = cv2.getTextSize(sub, font, 0.9, 2)
    sx = (w - sub_size[0]) // 2
    sy = ty + 40 + sub_size[1]
    cv2.putText(img, sub, (sx, sy), font, 0.9, (200, 200, 200), 2, cv2.LINE_AA)

    ok, enc = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        raise RuntimeError("Failed to build placeholder jpeg")
    return enc.tobytes()


async def _update_latest_frame(data: bytes, ts: float):
    """最新フレームを更新し、初回はプレースホルダーのサイズも合わせる"""
    global latest_frame, last_frame_size, placeholder_jpeg, placeholder_size
    async with frame_lock:
        latest_frame = {"data": data, "ts": ts}
    if last_frame_size is None:
        try:
            arr = np.frombuffer(data, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                h, w = img.shape[:2]
                last_frame_size = (w, h)
                if (w, h) != placeholder_size:
                    placeholder_size = (w, h)
                    placeholder_jpeg = build_placeholder(placeholder_size)
                    print(f"[video] placeholder resized to {placeholder_size}")
        except Exception:
            pass


class UdpReceiverProtocol(asyncio.DatagramProtocol):
    """1データグラム=1JPEGフレームとして受信"""
    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]
        sock = transport.get_extra_info("socket")
        addr = sock.getsockname() if sock else ("?", "?")
        print(f"[udp] listening on {addr}")

    def datagram_received(self, data: bytes, addr) -> None:
        try:
            now = time.time()
            asyncio.get_running_loop().create_task(_update_latest_frame(data, now))
        except Exception as e:
            print(f"[udp] datagram_received error: {repr(e)}")
            traceback.print_exc()

    def error_received(self, exc: Exception) -> None:
        print(f"[udp] transport error: {repr(exc)}")

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            print(f"[udp] connection lost: {repr(exc)}")
        else:
            print("[udp] connection closed cleanly")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """テレメトリ（JSONテキスト）の配信用"""
    await manager.connect(websocket)
    print("[/ws] client connected")
    try:
        while True:
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        print("[/ws] client disconnected")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[/ws] error: {repr(e)}")
        traceback.print_exc()
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


@app.websocket("/ws/video")
async def video_stream(websocket: WebSocket):
    """映像（JPEGバイナリ）を送信。途切れ時はプレースホルダー送信"""
    await websocket.accept()
    print("[/ws/video] client connected")
    try:
        interval = 1.0 / float(VIDEO_FPS)
        while True:
            await asyncio.sleep(interval)

            frame_data = None
            frame_ts = None
            async with frame_lock:
                if latest_frame is not None:
                    frame_data = latest_frame["data"]
                    frame_ts = latest_frame["ts"]

            now = time.time()
            stale = (frame_data is None) or (frame_ts is None) or (now - frame_ts > VIDEO_TIMEOUT_SEC)
            if stale:
                await websocket.send_bytes(placeholder_jpeg)  # type: ignore[arg-type]
            else:
                await websocket.send_bytes(frame_data)
    except WebSocketDisconnect:
        print("[/ws/video] client disconnected")
    except Exception as e:
        print(f"[/ws/video] error: {repr(e)}")
        traceback.print_exc()
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


@app.post("/config-mode/set-bin-threshold")
async def set_bin_threshold(threshold: int):
    """
    2値化の閾値を設定
    Args:
        threshold (int): 2値化の閾値 (-1: 二値化処理無効, 0-255: 閾値)
    Returns:
        JSONResponse: result 
    """
    if not (-1 <= threshold <= 255):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Threshold must be between -1 and 255."},
        )
    mavlink_client.send_bin_threshold(threshold)
    drone_settings.set_bin_threshold(threshold)
    return {"status": "ok", "message": f"Binary threshold set to {threshold}."}


@app.get("/config-mode/get-bin-threshold")
async def get_bin_threshold():
    """2値化の閾値を取得"""
    threshold = drone_settings.bin_threshold
    return {"status": "ok", "bin_threshold": threshold}


@app.post("/config-mode/keep-alive")
def send_enable_config_mode_signal():
    mavlink_client.set_config_mode_signal()
    return {"status": "ok"}


async def periodic_task():
    """30Hzでテレメトリデータをフロントエンドにブロードキャストする"""
    try:
        while True:
            position = mavlink_client.get_drone_position()
            quaternion = mavlink_client.get_drone_quaternion()
            sysid = 1

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
        print(f"[periodic_task] error: {repr(e)}")
        traceback.print_exc()


@app.websocket("/ws/drone/control")
async def drone_control_socket(websocket: WebSocket):
    await websocket.accept()
    print("Drone control WebSocket connected")

    try:
        while True:
            # ここでメッセージ受信完了まで await するため、ビジーループにはなりません
            message_text = await websocket.receive_text()
            data = json.loads(message_text)

            action = data.get("action")
            params = data.get("params", {})
            
            if action == "takeoff":
                print("takeoff command received")
                # 高度などが params に入っている想定
                altitude = params.get("altitude", 2.0)
                print("target altitude:", altitude)
                # send_mavlink_takeoff(altitude)

            elif action == "landing":
                print("landing command received")
                # send_mavlink_land()

            elif action == "emergency_stop":
                print("emergency stop command received")

            else:
                print("unknown action:", action)

    except WebSocketDisconnect:
        print("Drone control WebSocket disconnected")
        # ここでフェイルセーフ処理を行う想定
        # send_mavlink_velocity(0.0, 0.0, 0.0)
        # send_mavlink_hold_or_rtl()


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


@app.on_event("startup")
async def startup_event():
    """起動時の初期化（UDP受信開始とテレメトリ送信タスク開始）"""
    global udp_transport, udp_protocol, placeholder_jpeg
    print("[startup] FastAPI app starting...")

    try:
        placeholder_jpeg = build_placeholder(placeholder_size)
        print(f"[startup] placeholder ready: size={placeholder_size}")
    except Exception as e:
        print(f"[startup] placeholder build failed: {repr(e)}")
        traceback.print_exc()
        raise

    try:
        loop = asyncio.get_running_loop()
        udp_transport, udp_protocol = await loop.create_datagram_endpoint(
            lambda: UdpReceiverProtocol(),
            local_addr=(UDP_FRAME_RECEIVE_IP, UDP_FRAME_RECEIVE_PORT),
            family=socket.AF_INET,
            reuse_port=False,
        )
        print("[startup] udp datagram endpoint started")
    except Exception as e:
        print(f"[startup] UDP endpoint create failed: {repr(e)}")
        traceback.print_exc()
        raise

    asyncio.create_task(periodic_task())
    print("[startup] periodic_task started")


@app.on_event("shutdown")
async def shutdown_event():
    """終了時の後始末"""
    print("[shutdown] stopping...")

    try:
        if udp_transport is not None:
            udp_transport.close()
    except Exception as e:
        print(f"[shutdown] udp transport close error: {repr(e)}")

    with contextlib.suppress(Exception):
        mavlink_client.stop()

    print("[shutdown] resources cleaned up.")
