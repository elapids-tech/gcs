import base64
import json
import re
import time
import asyncio
import socket
import contextlib
import traceback
from typing import Optional

import cv2
import numpy as np
import uvicorn
import os
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect, WebSocketState

from backend.mavlink_client import MavlinkClient
from backend.camera_calibration import CameraCalibration
from backend.video_recorder import VideoRecorder
from backend.projects import flight_area
from backend.app_setting import app_setting, ensure_settings_file

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
app.include_router(app_setting)
app.include_router(flight_area)

manager = ConnectionManager()

mavlink_client = MavlinkClient(host_ip="192.168.0.6")

VIDEO_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "recordings")
rec = VideoRecorder(output_dir=VIDEO_OUTPUT_DIR)

cc_0 = CameraCalibration(cols=4, rows=11, col_pitch_mm=20.0, row_pitch_mm=None)
cc_1 = CameraCalibration(cols=4, rows=11, col_pitch_mm=20.0, row_pitch_mm=None)
camera_0_allow_grid_pts_registration = False
camera_1_allow_grid_pts_registration = False
camera_calibration_counts = {0: 0, 1: 0}
last_broadcasted_calibration = {0: {"count": -1, "running": None}, 1: {"count": -1, "running": None}}
calibration_execute_status = {
    0: {"running": False, "started_at": None, "last_error": None, "result_available": False},
    1: {"running": False, "started_at": None, "last_error": None, "result_available": False},
}

# 受信した最新フレーム（JPEGバイト列と受信時刻）
latest_frame: Optional[dict] = None  # {"data": bytes, "ts": float}
frame_lock = asyncio.Lock()
pending_frame: Optional[dict] = None  # {"data": bytes, "ts": float}
processing_frame = False

# プレースホルダー画像（左右分割でJPEG保持）
placeholder_left_jpeg: Optional[bytes] = None
placeholder_right_jpeg: Optional[bytes] = None
placeholder_size: tuple[int, int] = PLACEHOLDER_DEFAULT_SIZE  # (w, h)
last_frame_size: Optional[tuple[int, int]] = None  # 実フレームサイズが判明したら更新

# 分割済みフレーム（左右JPEGバイト列と受信時刻）
latest_split_frame: Optional[dict] = None  # {"left": bytes, "right": bytes, "ts": float}

# UDP受信のTransport/Protocol
udp_transport: Optional[asyncio.DatagramTransport] = None
udp_protocol: Optional["UdpReceiverProtocol"] = None

def build_placeholder_image(size: tuple[int, int], text: str = "NO CONNECTION") -> np.ndarray:
    """指定サイズにラベルを描いたプレースホルダー画像を作成"""
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

    return img


def encode_jpeg(img: np.ndarray) -> bytes:
    ok, enc = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        raise RuntimeError("Failed to encode jpeg")
    return enc.tobytes()


def split_frame(img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    h, w = img.shape[:2]
    mid = w // 2
    left = img[:, :mid]
    right = img[:, mid:]
    return left, right


async def _broadcast_calibration_update(camera: int):
    count = camera_calibration_counts.get(camera, 0)
    running = camera_0_allow_grid_pts_registration if camera == 0 else camera_1_allow_grid_pts_registration
    last = last_broadcasted_calibration.get(camera)
    if last and last["count"] == count and last["running"] == running:
        return
    last_broadcasted_calibration[camera] = {"count": count, "running": running}
    payload = {
        "key": "cameraCalibrationUpdate",
        "value": {
            "camera": camera,
            "registeredCount": count,
            "running": running,
        },
    }
    await manager.broadcast(json.dumps(payload))


async def _update_latest_frame(data: bytes, ts: float):
    """最新フレームを保持（古いものは破棄）"""
    global pending_frame
    async with frame_lock:
        pending_frame = {"data": data, "ts": ts}


async def _image_processing_loop():
    """保持中の最新フレームだけを処理する"""
    global latest_frame, latest_split_frame, last_frame_size
    global placeholder_left_jpeg, placeholder_right_jpeg, placeholder_size
    global pending_frame, processing_frame

    while True:
        async with frame_lock:
            if processing_frame or pending_frame is None:
                frame = None
            else:
                processing_frame = True
                frame = pending_frame
                pending_frame = None

        if frame is None:
            await asyncio.sleep(0.001)
            continue

        data = frame["data"]
        ts = frame["ts"]

        try:
            arr = np.frombuffer(data, dtype=np.uint8)
            if arr.size == 0:
                continue
            gray = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)

            is_recording = rec.is_recording()
            if is_recording:
                rec.update(gray)

            color = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

            h, w = gray.shape[:2]

            if last_frame_size is None:
                last_frame_size = (w, h)

            if (w, h) != placeholder_size:
                placeholder_size = (w, h)
                placeholder_img = build_placeholder_image(placeholder_size)
                left_img, right_img = split_frame(placeholder_img)
                placeholder_left_jpeg = encode_jpeg(left_img)
                placeholder_right_jpeg = encode_jpeg(right_img)
                print(f"[video] placeholder resized to {placeholder_size}")

            left_img, right_img = split_frame(color)
            left_gray, right_gray = split_frame(gray)

            # カメラごとにキャリブレーションを実行する
            if camera_0_allow_grid_pts_registration:
                bw_left = cc_0.binarize(left_gray)
                centers_left = cc_0.find_asymmetric_grid(bw_left)
                if centers_left is not None:
                    accepted = cc_0.add_grid_points(centers_left, image_shape=left_gray.shape[:2])
                    if accepted:
                        camera_calibration_counts[0] = cc_0.get_registered_frame_count()
                        await _broadcast_calibration_update(0)
                    left_img = cc_0.draw_detected_points(left_img, centers_left)
                tile_counts = cc_0.get_tile_overlap_count()
                if tile_counts is not None:
                    left_img = cc_0.draw_overlay(left_img, tile_counts, alpha=0.5, max_count=10)
            if camera_1_allow_grid_pts_registration:
                bw_right = cc_1.binarize(right_gray)
                centers_right = cc_1.find_asymmetric_grid(bw_right)
                if centers_right is not None:
                    accepted = cc_1.add_grid_points(centers_right, image_shape=right_gray.shape[:2])
                    if accepted:
                        camera_calibration_counts[1] = cc_1.get_registered_frame_count()
                        await _broadcast_calibration_update(1)
                    right_img = cc_1.draw_detected_points(right_img, centers_right)
                tile_counts = cc_1.get_tile_overlap_count()
                if tile_counts is not None:
                    right_img = cc_1.draw_overlay(right_img, tile_counts, alpha=0.5, max_count=10)

            # encode jpeg
            left_jpeg = encode_jpeg(left_img)
            right_jpeg = encode_jpeg(right_img)

            async with frame_lock:
                latest_frame = {"data": data, "ts": ts}
                latest_split_frame = {"left": left_jpeg, "right": right_jpeg, "ts": ts}
        except Exception:
            pass
        finally:
            async with frame_lock:
                processing_frame = False


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


# Camera Setting Mode API

@app.post("/camera-setting-mode/request-drone-camera-parameters")
async def request_drone_camera_parameters():
    requested = mavlink_client.request_all_camera_settings_parameters()
    parameters = mavlink_client.get_camera_settings_parameters()
    print("debug: got camera parameters from drone:", parameters)
    return {"status": "ok", "requested": requested, "parameters": parameters}


@app.post("/camera-setting-mode/set-bin-threshold")
async def set_bin_threshold(threshold: int):
    """2値化の閾値を設定する。"""
    if not (-1 <= threshold <= 255):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Threshold must be between -1 and 255."},
        )

    ok = mavlink_client.send_bin_threshold_parameter(threshold)
    if not ok:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Failed to set bin threshold."},
        )

    return {"status": "ok", "message": f"Binary threshold set to {threshold}."}


@app.post("/recording/start")
async def start_recording():
    info = rec.start()
    return {"status": "ok", "filename": info.get("filename")}


@app.post("/recording/stop")
async def stop_recording():
    result_info = rec.stop()
    files = rec.get_video_file_name_list()
    return {"status": "ok", "filename": result_info.get("filename"), "files": files}


@app.get("/recording/list")
async def list_recordings():
    recording = rec.get_current_filename()
    files = rec.get_video_file_name_list()
    return {"status": "ok", "recording": recording, "files": files}


@app.get("/recording/download/{filename}")
async def download_recording(filename: str):
    if not re.match(r"^[\w\-]+\.mp4$", filename):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Invalid filename."},
        )
    filepath = os.path.join(VIDEO_OUTPUT_DIR, filename)
    if not os.path.isfile(filepath):
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "File not found."},
        )
    if rec.get_current_filename() == filename:
        return JSONResponse(
            status_code=409,
            content={"status": "error", "message": "File is currently being recorded."},
        )
    return FileResponse(filepath, media_type="video/mp4", filename=filename)


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
                if latest_split_frame is not None:
                    frame_data = latest_split_frame
                    frame_ts = latest_split_frame["ts"]

            now = time.time()
            stale = (frame_data is None) or (frame_ts is None) or (now - frame_ts > VIDEO_TIMEOUT_SEC)
            if stale:
                left = placeholder_left_jpeg
                right = placeholder_right_jpeg
            else:
                left = frame_data["left"]
                right = frame_data["right"]

            if left is None or right is None:
                continue

            payload = {
                "left": base64.b64encode(left).decode("ascii"),
                "right": base64.b64encode(right).decode("ascii"),
            }
            await websocket.send_text(json.dumps(payload))
    except WebSocketDisconnect:
        print("[/ws/video] client disconnected")
    except Exception as e:
        print(f"[/ws/video] error: {repr(e)}")
        traceback.print_exc()
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


_CAMERA_CONTROL_RANGES = {
    "brightness": (-64, 64),
    "contrast": (0, 95),
    "saturation": (0, 100),
    "hue": (-2000, 2000),
    "gamma": (100, 300),
    "gain": (0, 255),
    "exposure-time-absolute": (1, 10000),
    "white-balance-temperature": (2800, 6500),
    "sharpness": (1, 100),
}

def _send_camera_control(name: str, value: int) -> bool:
    if name == "brightness":
        return bool(mavlink_client.send_brightness_parameter(value))
    if name == "contrast":
        return bool(mavlink_client.send_contrast_parameter(value))
    if name == "saturation":
        return bool(mavlink_client.send_saturation_parameter(value))
    if name == "hue":
        return bool(mavlink_client.send_hue_parameter(value))
    if name == "gamma":
        return bool(mavlink_client.send_gamma_parameter(value))
    if name == "gain":
        return bool(mavlink_client.send_gain_parameter(value))
    if name == "exposure-time-absolute":
        return bool(mavlink_client.send_exposure_time_absolute_parameter(value))
    if name == "white-balance-temperature":
        return bool(mavlink_client.send_white_balance_temperature_parameter(value))
    if name == "sharpness":
        return bool(mavlink_client.send_sharpness_parameter(value))
    return False

@app.post("/camera-setting-mode/set-camera-control")
async def set_camera_control(name: str, value: int):
    """
    カメラ設定を一括で設定
    Args:
        name (str): パラメータ名(ハイフン区切り)
            brightness, contrast, saturation, hue, gamma, gain,
            exposure-time-absolute, white-balance-temperature, sharpness
        value (int): 設定値
    Returns:
        JSONResponse: result
    """
    if name not in _CAMERA_CONTROL_RANGES:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Unknown camera control name: {name}"},
        )

    lo, hi = _CAMERA_CONTROL_RANGES[name]
    if not (lo <= value <= hi):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"{name} must be between {lo} and {hi}."},
        )

    ok = _send_camera_control(name, int(value))
    if not ok:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Failed to set {name}."},
        )

    return {"status": "ok", "message": f"{name} set to {value}."}


@app.get("/camera-setting-mode/read-bin-threshold-on-drone")
async def get_bin_threshold():
    """ドローンに設定されている2値化閾値を取得する"""
    mavlink_client.send_bin_threshold_param_request_read()
    threshold = mavlink_client.get_bin_threshold_parameter()
    return {"status": "ok", "bin_threshold": threshold}


@app.post("/camera-setting-mode/keep-alive")
def send_enable_camera_setting_mode_signal():
    mavlink_client.set_camera_setting_mode_signal()
    return {"status": "ok"}


@app.post("/camera-setting-mode/camera-calibration/start")
async def start_camera_calibration(camera: int = 0):
    global camera_0_allow_grid_pts_registration, camera_1_allow_grid_pts_registration
    if camera == 0:
        if camera_1_allow_grid_pts_registration:
            return JSONResponse(
                status_code=409,
                content={"status": "error", "message": "Camera 1 calibration is running."},
            )
        camera_0_allow_grid_pts_registration = True
        camera_1_allow_grid_pts_registration = False
    elif camera == 1:
        if camera_0_allow_grid_pts_registration:
            return JSONResponse(
                status_code=409,
                content={"status": "error", "message": "Camera 0 calibration is running."},
            )
        camera_1_allow_grid_pts_registration = True
        camera_0_allow_grid_pts_registration = False
    else:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Invalid camera number: {camera}"},
        )
    for cam in (0, 1):
        await _broadcast_calibration_update(cam)
    return {"status": "ok", "running": True, "camera": camera}


@app.post("/camera-setting-mode/camera-calibration/stop")
async def stop_camera_calibration(camera: int = 0):
    global camera_0_allow_grid_pts_registration, camera_1_allow_grid_pts_registration
    camera_0_allow_grid_pts_registration = False
    camera_1_allow_grid_pts_registration = False
    for cam in (0, 1):
        await _broadcast_calibration_update(cam)
    return {"status": "ok", "running": camera_0_allow_grid_pts_registration or camera_1_allow_grid_pts_registration}


@app.get("/camera-setting-mode/camera-calibration/status")
def camera_calibration_status():
    return {"status": "ok", "running": camera_0_allow_grid_pts_registration or camera_1_allow_grid_pts_registration}


@app.post("/camera-setting-mode/camera-calibration/execute-calibration")
async def execute_camera_calibration(camera: int = 0, lens_type: str = "fisheye"):
    global camera_0_allow_grid_pts_registration, camera_1_allow_grid_pts_registration

    if camera not in (0, 1):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Invalid camera number: {camera}"},
        )

    if lens_type not in CameraCalibration.LENS_TYPES:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Invalid lens_type: {lens_type}"},
        )

    status = calibration_execute_status[camera]
    if status["running"]:
        return JSONResponse(
            status_code=409,
            content={"status": "error", "message": "Calibration is already running."},
        )

    if camera == 0:
        camera_0_allow_grid_pts_registration = False
        cc_0.lens_type = lens_type
    else:
        camera_1_allow_grid_pts_registration = False
        cc_1.lens_type = lens_type

    status["running"] = True
    status["started_at"] = time.time()
    status["last_error"] = None
    status["result_available"] = False

    async def _run_calibration():
        try:
            if camera == 0:
                performed = await asyncio.to_thread(cc_0.execute_calibration)
                result = cc_0.get_result()
            else:
                performed = await asyncio.to_thread(cc_1.execute_calibration)
                result = cc_1.get_result()
            status["result_available"] = result is not None
            if not performed and result is not None:
                status["last_error"] = str(result.get("reason"))
        except Exception as e:
            status["last_error"] = f"{type(e).__name__}: {e}"
            traceback.print_exc()
        finally:
            status["running"] = False

    asyncio.create_task(_run_calibration())
    return {"status": "ok", "camera": camera, "running": True}


@app.get("/camera-setting-mode/camera-calibration/execute-status")
def get_execute_calibration_status(camera: int = 0):
    if camera not in (0, 1):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Invalid camera number: {camera}"},
        )

    status = calibration_execute_status[camera]
    started_at = status["started_at"]
    if camera == 0:
        status["result_available"] = cc_0.get_result() is not None
    else:
        status["result_available"] = cc_1.get_result() is not None
    elapsed = time.time() - started_at if started_at else None
    return {
        "status": "ok",
        "camera": camera,
        "running": status["running"],
        "started_at": started_at,
        "elapsed_sec": elapsed,
        "last_error": status["last_error"],
        "result_available": status["result_available"],
    }


@app.get("/camera-setting-mode/camera-calibration/download")
def download_camera_calibration(camera: int = 0):
    if calibration_execute_status.get(camera, {}).get("running"):
        return JSONResponse(
            status_code=409,
            content={"status": "error", "message": "Calibration is running."},
        )
    if camera == 0:
        result = cc_0.get_result()
    elif camera == 1:
        result = cc_1.get_result()
    else:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Invalid camera number: {camera}"},
        )

    if result is None:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "No calibration result available."},
        )

    payload = json.dumps(result, indent=2)
    filename = f"camera_{camera}_calibration.json"
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/camera-setting-mode/camera-calibration/save-to-drone")
def save_calibration_to_drone(camera: int = 0):
    if camera == 0:
        result = cc_0.get_result()
        # jsonファイルを出力しdroneに送信。
        # 送信が完了したらdrone_app_initを実行し、キャリブレーションjsonを読み込ませる。
    elif camera == 1:
        result = cc_1.get_result()
    else:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Invalid camera number: {camera}"},
        )
    return {"status": "ok"}


@app.post("/camera-setting-mode/camera-calibration/reset-calibration-data")
async def reset_calibration_data(camera: int = 0):
    if camera not in (0, 1):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Invalid camera number: {camera}"},
        )

    if calibration_execute_status.get(camera, {}).get("running"):
        return JSONResponse(
            status_code=409,
            content={"status": "error", "message": "Calibration is running."},
        )

    cal = cc_0 if camera == 0 else cc_1
    if cal.is_executing():
        return JSONResponse(
            status_code=409,
            content={"status": "error", "message": "Calibration is running."},
        )

    try:
        cal.reset_calibration_data()
    except RuntimeError as exc:
        return JSONResponse(
            status_code=409,
            content={"status": "error", "message": str(exc)},
        )

    count = cal.get_registered_frame_count()
    camera_calibration_counts[camera] = count
    calibration_execute_status[camera]["result_available"] = False
    calibration_execute_status[camera]["last_error"] = None
    await _broadcast_calibration_update(camera)
    return {"status": "ok", "camera": camera, "registeredCount": count}


async def periodic_task():
    """30Hzでテレメトリデータをフロントエンドにブロードキャストする"""
    try:
        while True:
            position = mavlink_client.get_drone_position()
            quaternion = mavlink_client.get_drone_quaternion()
            has_odometry = mavlink_client.has_drone_odometry()
            sysid = 1

            drone_pose = {
                "key": "dronePoseUpdate",
                "value": {
                    "sysid": sysid,
                    "position": list(position),
                    "quaternion": list(quaternion),
                    "hasOdometry": has_odometry,
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
            
            if action == "set_home":
                print("set_home command received")
                ok = mavlink_client.set_home_from_odometry(wait_update=True)
                print(f"set_home_from_odometry result: {ok}")

            elif action == "takeoff":
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
    global udp_transport, udp_protocol, placeholder_left_jpeg, placeholder_right_jpeg
    print("[startup] FastAPI app starting...")

    try:
        ensure_settings_file()
        print("[startup] app settings file ready")
    except Exception as e:
        print(f"[startup] app settings init failed: {repr(e)}")
        traceback.print_exc()
        raise

    try:
        placeholder_img = build_placeholder_image(placeholder_size)
        left_img, right_img = split_frame(placeholder_img)
        placeholder_left_jpeg = encode_jpeg(left_img)
        placeholder_right_jpeg = encode_jpeg(right_img)
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
    asyncio.create_task(_image_processing_loop())
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
