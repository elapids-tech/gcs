import math
import socket
import threading
import time
from typing import Dict, Optional, Tuple

from pymavlink import mavutil


class DroneState:
    def __init__(self):
        self.mode = "UNKNOWN"
        self.armed = False
        self.battery_voltage = 0.0
        self.battery_remaining = 0
        self.position = [0.0, 0.0, 0.0]
        self.attitude = [0.0, 0.0, 0.0]


class MavlinkClient:
    """
    Minimal MAVLink client (GCS side).

    Parameters
    ----------
    host_ip : str
        Companion board IP.
    host_port : int, default 14551
        Destination UDP port on companion (mavlink-router "from_gcs").
    local_port : int, default 14611
        Local UDP port (bind). TX source port and RX port.
    my_sysid : int, default 200
        GCS MAVLink system id.
    my_compid : int, default 190
        GCS MAVLink component id.
    target_sysid : int, default 201
        App MAVLink system id.
    target_compid : int, default 191
        App MAVLink component id.
    heartbeat_hz : float, default 1.0
        Heartbeat send rate.
    enable_stdout_log : bool, default False
        Print minimal RX logs.
    rx_timeout_sec : float, default 1.0
        Socket recv timeout (stop responsiveness).
    """

    MAV_CMD_MY_APP_SET_CONFIG_MODE = 31000
    MAV_CMD_MY_APP_VIDEO_STREAMING_MODE = 31001

    def __init__(
        self,
        host_ip: str,
        host_port: int = 14551,
        local_port: int = 14611,
        my_sysid: int = 200,
        my_compid: int = 190,
        target_sysid: int = 201,
        target_compid: int = 191,
        heartbeat_hz: float = 1.0,
        enable_stdout_log: bool = False,
        rx_timeout_sec: float = 1.0,
    ):
        self._enable_stdout_log = enable_stdout_log

        self.host_ip = host_ip
        self.host_port = int(host_port)
        self.local_port = int(local_port)

        self.my_sysid = int(my_sysid)
        self.my_compid = int(my_compid)
        self.target_sysid = int(target_sysid)
        self.target_compid = int(target_compid)

        self._dest: Tuple[str, int] = (self.host_ip, self.host_port)

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", self.local_port))
        self._sock.settimeout(float(rx_timeout_sec))

        self._mav = mavutil.mavlink.MAVLink(self)
        self._mav.srcSystem = self.my_sysid
        self._mav.srcComponent = self.my_compid

        self._running = True
        self._threads = []

        self.px4_raw_pos = [0.0, 0.0, 0.0]
        self.px4_raw_quat = [0.0, 0.0, 0.0, 1.0]

        self._param_lock = threading.Lock()
        self._param_cv = threading.Condition(self._param_lock)
        self._params: Dict[str, float] = {}

        self._heartbeat_interval = 1.0 / max(float(heartbeat_hz), 0.1)

        t1 = threading.Thread(target=self._tx_heartbeat_loop, daemon=True)
        t2 = threading.Thread(target=self._rx_loop, daemon=True)
        t1.start()
        t2.start()
        self._threads.append(t1)
        self._threads.append(t2)

    def write(self, b: bytes) -> int:
        try:
            return self._sock.sendto(b, self._dest)
        except Exception:
            return 0

    def _log(self, s: str) -> None:
        if self._enable_stdout_log:
            print(s)

    def stop(self) -> None:
        self._running = False
        for t in self._threads:
            t.join(timeout=1.0)
        try:
            self._sock.close()
        except Exception:
            pass

    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass

    def _tx_heartbeat_loop(self) -> None:
        while self._running:
            try:
                self._mav.heartbeat_send(
                    mavutil.mavlink.MAV_TYPE_GCS,
                    mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                    0,
                    0,
                    mavutil.mavlink.MAV_STATE_ACTIVE,
                )
            except Exception:
                pass
            time.sleep(self._heartbeat_interval)

    def _rx_loop(self) -> None:
        while self._running:
            try:
                data, _addr = self._sock.recvfrom(4096)
            except socket.timeout:
                continue
            except Exception:
                continue

            if not data:
                continue

            for b in data:
                try:
                    msg = self._mav.parse_char(bytes([b]))
                except Exception:
                    msg = None

                if msg is None:
                    continue

                self._handle_message(msg)

    def _handle_message(self, msg) -> None:
        try:
            src_sys = int(msg.get_srcSystem())
            src_comp = int(msg.get_srcComponent())
        except Exception:
            return

        mtype = msg.get_type()

        if mtype == "ODOMETRY":
            self._handle_odometry(msg)
            return

        if mtype == "PARAM_VALUE":
            if src_sys == self.target_sysid and src_comp == self.target_compid:
                self._handle_param_value(msg)
            return

        self._log(f"[rx] type={mtype} sys={src_sys} comp={src_comp}")

    def _handle_odometry(self, msg) -> None:
        try:
            x = float(getattr(msg, "x", 0.0))
            y = float(getattr(msg, "y", 0.0))
            z = float(getattr(msg, "z", 0.0))

            q = getattr(msg, "q", None)
            if q is None or len(q) < 4:
                return

            w = float(q[0])
            qx = float(q[1])
            qy = float(q[2])
            qz = float(q[3])

            vals = (x, y, z, w, qx, qy, qz)
            if not all(math.isfinite(v) for v in vals):
                return

            self.px4_raw_pos = [x, y, z]
            self.px4_raw_quat = [qx, qy, qz, w]
        except Exception:
            return

    def _handle_param_value(self, msg) -> None:
        try:
            raw = msg.param_id
            if isinstance(raw, (bytes, bytearray)):
                rx_id = raw.decode("ascii", errors="ignore")
            else:
                rx_id = str(raw)
            rx_id = rx_id.rstrip("\x00").strip()

            val = float(getattr(msg, "param_value", 0.0))
            if not math.isfinite(val):
                return

            with self._param_cv:
                self._params[rx_id] = val
                self._param_cv.notify_all()

            self._log(f"[rx] param_value id={rx_id} value={val}")
        except Exception:
            return

    def get_param_cached(self, param_id: str) -> Optional[float]:
        key = param_id.strip()
        with self._param_lock:
            return self._params.get(key)

    def get_drone_position(self) -> list[float]:
        fx, fy, fz = self.px4_raw_pos
        return [fx, -fy, -fz]

    def get_drone_quaternion(self) -> list[float]:
        qx, qy, qz, qw = self.px4_raw_quat

        w = qw
        x = qx
        y = qy
        z = qz

        n = (w * w + x * x + y * y + z * z) ** 0.5
        if n == 0.0:
            return [0.0, 0.0, 0.0, 1.0]
        w /= n
        x /= n
        y /= n
        z /= n

        R00 = 1.0 - 2.0 * (y * y + z * z)
        R01 = 2.0 * (x * y - z * w)
        R02 = 2.0 * (x * z + y * w)

        R10 = 2.0 * (x * y + z * w)
        R11 = 1.0 - 2.0 * (x * x + z * z)
        R12 = 2.0 * (y * z - x * w)

        R20 = 2.0 * (x * z - y * w)
        R21 = 2.0 * (y * z + x * w)
        R22 = 1.0 - 2.0 * (x * x + y * y)

        R00p = R00
        R01p = R01
        R02p = R02

        R10p = -R10
        R11p = -R11
        R12p = -R12

        R20p = -R20
        R21p = -R21
        R22p = -R22

        tr = R00p + R11p + R22p
        if tr > 0.0:
            S = (tr + 1.0) ** 0.5 * 2.0
            qw2 = 0.25 * S
            qx2 = (R21p - R12p) / S
            qy2 = (R02p - R20p) / S
            qz2 = (R10p - R01p) / S
        elif (R00p > R11p) and (R00p > R22p):
            S = (1.0 + R00p - R11p - R22p) ** 0.5 * 2.0
            qw2 = (R21p - R12p) / S
            qx2 = 0.25 * S
            qy2 = (R01p + R10p) / S
            qz2 = (R02p + R20p) / S
        elif R11p > R22p:
            S = (1.0 - R00p + R11p - R22p) ** 0.5 * 2.0
            qw2 = (R02p - R20p) / S
            qx2 = (R01p + R10p) / S
            qy2 = 0.25 * S
            qz2 = (R12p + R21p) / S
        else:
            S = (1.0 - R00p - R11p + R22p) ** 0.5 * 2.0
            qw2 = (R10p - R01p) / S
            qx2 = (R02p + R20p) / S
            qy2 = (R12p + R21p) / S
            qz2 = 0.25 * S

        n2 = (qw2 * qw2 + qx2 * qx2 + qy2 * qy2 + qz2 * qz2) ** 0.5
        if n2 == 0.0:
            return [0.0, 0.0, 0.0, 1.0]

        qw2 /= n2
        qx2 /= n2
        qy2 /= n2
        qz2 /= n2

        return [qx2, qy2, qz2, qw2]

    def set_config_mode_signal(self) -> None:
        try:
            self._mav.command_long_send(
                self.target_sysid,
                self.target_compid,
                self.MAV_CMD_MY_APP_SET_CONFIG_MODE,
                0,
                1, 0, 0, 0, 0, 0, 0,
            )
        except Exception:
            pass

    def set_video_streaming_mode_signal(self) -> None:
        try:
            self._mav.command_long_send(
                self.target_sysid,
                self.target_compid,
                self.MAV_CMD_MY_APP_VIDEO_STREAMING_MODE,
                0,
                1, 0, 0, 0, 0, 0, 0,
            )
        except Exception:
            pass

    def send_bin_threshold_parameter(self, threshold: int, timeout_sec: float = 2.0) -> bool:
        param_id = "BIN_TH"
        threshold = max(-1, min(255, int(threshold)))
    
        try:
            self._mav.param_set_send(
                self.target_sysid,
                self.target_compid,
                param_id.encode("ascii"),
                float(threshold),
                mavutil.mavlink.MAV_PARAM_TYPE_INT32,
            )
        except Exception:
            return False
    
        deadline = time.time() + max(0.0, float(timeout_sec))
    
        with self._param_cv:
            while True:
                cur = self._params.get(param_id)
                if cur is not None:
                    cur_i = int(round(float(cur)))
                    if cur_i == threshold:
                        return True
    
                remain = deadline - time.time()
                if remain <= 0.0:
                    return False
    
                self._param_cv.wait(timeout=remain)
    
    def get_bin_threshold_parameter(self, timeout_sec: float = 2.0) -> Optional[int]:
        param_id = "BIN_TH"
        pass