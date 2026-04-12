import math
import socket
import threading
import time
from typing import Dict, Optional, Tuple

import os
os.environ["MAVLINK20"] = "1"
os.environ["MAVLINK_DIALECT"] = "common"
from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink2


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

    # drone mode control command (custom MAVLink command, not standard)
    MAV_CMD_APP_SET_IDLE_MODE = 31000
    MAV_CMD_APP_SET_POSE_ESTIMATION_MODE = 31001
    MAV_CMD_APP_SET_PARAMETER_SETTING_MODE = 31002
    MAV_CMD_APP_SET_CAMERA_SETTING_MODE = 31003

    # FCU (ArduPilot) target ids
    FCU_SYSID = 1
    FCU_COMPID = 1

    # Magic value for MAV_CMD_COMPONENT_ARM_DISARM param2 to force disarm
    # regardless of safety checks (ArduPilot convention)
    FORCE_DISARM_MAGIC_VALUE = 21196

    PARAM_BIN_THRESHOLD = "BIN_TH"
    PARAM_BRIGHTNESS = "CAM_BRIGHT"
    PARAM_CONTRAST = "CAM_CONT"
    PARAM_SATURATION = "CAM_SAT"
    PARAM_HUE = "CAM_HUE"
    PARAM_GAMMA = "CAM_GAM"
    PARAM_GAIN = "CAM_GAIN"
    PARAM_WB_TEMP = "CAM_WBT"
    PARAM_SHARPNESS = "CAM_SHARP"
    PARAM_EXPOSURE_ABS = "CAM_EXP"
    PARAM_FPS = "CAM_FPS"

    CAMERA_SETTING_PARAM_IDS = (
        PARAM_BIN_THRESHOLD,
        PARAM_BRIGHTNESS,
        PARAM_CONTRAST,
        PARAM_SATURATION,
        PARAM_HUE,
        PARAM_GAMMA,
        PARAM_GAIN,
        PARAM_WB_TEMP,
        PARAM_SHARPNESS,
        PARAM_EXPOSURE_ABS,
    )

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

        self._mav = mavlink2.MAVLink(self)
        self._mav.srcSystem = self.my_sysid
        self._mav.srcComponent = self.my_compid

        self._running = True
        self._threads = []

        self.px4_raw_pos = [0.0, 0.0, 0.0]
        self.px4_raw_quat = [0.0, 0.0, 0.0, 1.0]

        self._param_lock = threading.Lock()
        self._param_cv = threading.Condition(self._param_lock)
        self._params: Dict[str, float] = {}
        self._param_update_seq: Dict[str, int] = {}

        self._ack_lock = threading.Lock()
        self._ack_cv = threading.Condition(self._ack_lock)
        self._ack_seq: Dict[int, int] = {}
        self._ack_result: Dict[int, int] = {}

        self._camera_settings_request_lock = threading.Lock()
        self._camera_settings_request_min_interval_sec = 2.0
        self._last_camera_settings_request_sent_at = 0.0

        self._heartbeat_interval = 1.0 / max(float(heartbeat_hz), 0.1)

        t1 = threading.Thread(target=self._tx_heartbeat_loop, daemon=True)
        t2 = threading.Thread(target=self._rx_loop, daemon=True)
        t1.start()
        t2.start()
        self._threads.append(t1)
        self._threads.append(t2)

    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass

    def write(self, b: bytes) -> int:
        try:
            return self._sock.sendto(b, self._dest)
        except Exception:
            return 0

    def stop(self) -> None:
        self._running = False
        for t in self._threads:
            t.join(timeout=1.0)
        try:
            self._sock.close()
        except Exception:
            pass

    def set_idle_mode_signal(self) -> None:
        try:
            self._mav.command_long_send(
                self.target_sysid,
                self.target_compid,
                self.MAV_CMD_APP_SET_IDLE_MODE,
                0,
                1, 0, 0, 0, 0, 0, 0,
            )
        except Exception:
            pass

    # Camera setting mode 

    def set_camera_setting_mode_signal(self) -> None:
        try:
            self._mav.command_long_send(
                self.target_sysid,
                self.target_compid,
                self.MAV_CMD_APP_SET_CAMERA_SETTING_MODE,
                0,
                1, 0, 0, 0, 0, 0, 0,
            )
        except Exception:
            pass

    def set_gps_global_origin(
        self,
        lat_deg: float,
        lon_deg: float,
        alt_m: float,
    ) -> bool:
        """Send SET_GPS_GLOBAL_ORIGIN message to FCU.

        SET_GPS_GLOBAL_ORIGIN is a MAVLink message (not a command), so no
        COMMAND_ACK is expected.  It tells the FCU's EKF where the local
        coordinate origin maps to in geographic coordinates.

        Args:
            lat_deg: Latitude in degrees.
            lon_deg: Longitude in degrees.
            alt_m: Altitude in metres above MSL.

        Returns:
            True if the message was sent without error, False otherwise.
        """
        lat = int(round(lat_deg * 1e7))   # degrees → degE7
        lon = int(round(lon_deg * 1e7))   # degrees → degE7
        alt_mm = int(round(alt_m * 1000.0))  # metres → millimetres

        try:
            self._mav.set_gps_global_origin_send(
                self.FCU_SYSID,
                lat,
                lon,
                alt_mm,
            )
        except Exception:
            return False

        return True

    def set_home(
        self,
        use_current: bool,
        lat_deg: float = 0.0,
        lon_deg: float = 0.0,
        alt_m: float = 0.0,
        wait_ack: bool = True,
        timeout_sec: float = 2.0,
    ) -> bool:
        """Send MAV_CMD_DO_SET_HOME to FCU.

        MAV_CMD_DO_SET_HOME parameter mapping (MAVLink spec):
          param1 – Use current location: 1 = use current, 0 = use specified
          param2 – Empty
          param3 – Empty
          param4 – Yaw angle [deg] (NaN to use current heading)
          param5 – Latitude [deg]
          param6 – Longitude [deg]
          param7 – Altitude [m]
        """
        if use_current:
            p1 = 1.0
            p5, p6, p7 = 0.0, 0.0, 0.0
        else:
            p1 = 0.0
            p5 = float(lat_deg)
            p6 = float(lon_deg)
            p7 = float(alt_m)

        try:
            self._mav.command_long_send(
                self.FCU_SYSID,
                self.FCU_COMPID,
                mavutil.mavlink.MAV_CMD_DO_SET_HOME,
                0,
                p1, 0.0, 0.0, float("nan"), p5, p6, p7,
            )
        except Exception:
            return False

        if not wait_ack:
            return True

        return self._wait_command_ack(
            mavutil.mavlink.MAV_CMD_DO_SET_HOME,
            timeout_sec,
        )

    def arm(self, timeout_sec: float = 3.0) -> bool:
        """Send MAV_CMD_COMPONENT_ARM_DISARM to arm the FCU motors.

        MAV_CMD_COMPONENT_ARM_DISARM parameter mapping (MAVLink spec):
          param1 – 0: disarm, 1: arm
          param2 – Force arm/disarm (21196 = force, 0 = normal safety checks)

        Returns:
            True if COMMAND_ACK with MAV_RESULT_ACCEPTED is received within
            *timeout_sec*, False otherwise.
        """
        try:
            self._mav.command_long_send(
                self.FCU_SYSID,
                self.FCU_COMPID,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,
                1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            )
        except Exception:
            return False

        return self._wait_command_ack(
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            timeout_sec,
        )

    def disarm(self, force: bool = False, timeout_sec: float = 3.0) -> bool:
        """Send MAV_CMD_COMPONENT_ARM_DISARM to disarm the FCU motors.

        Args:
            force: When True, send the force-disarm magic value (21196) in
                   param2 to bypass safety checks (use for emergency stop).
            timeout_sec: Seconds to wait for COMMAND_ACK.

        Returns:
            True if COMMAND_ACK with MAV_RESULT_ACCEPTED is received within
            *timeout_sec*, False otherwise.
        """
        param2 = float(self.FORCE_DISARM_MAGIC_VALUE) if force else 0.0
        try:
            self._mav.command_long_send(
                self.FCU_SYSID,
                self.FCU_COMPID,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,
                0.0, param2, 0.0, 0.0, 0.0, 0.0, 0.0,
            )
        except Exception:
            return False

        return self._wait_command_ack(
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            timeout_sec,
        )

    def takeoff(self, altitude_m: float, timeout_sec: float = 5.0) -> bool:
        """Send MAV_CMD_NAV_TAKEOFF to the FCU.

        The drone must already be armed and in GUIDED mode before calling
        this method.

        MAV_CMD_NAV_TAKEOFF parameter mapping (MAVLink spec):
          param1 – Minimum pitch [deg] (ignored by ArduCopter)
          param4 – Yaw angle [deg] (NaN to use current heading)
          param7 – Altitude [m]

        Args:
            altitude_m: Target takeoff altitude in metres (above home).
            timeout_sec: Seconds to wait for COMMAND_ACK.

        Returns:
            True if COMMAND_ACK with MAV_RESULT_ACCEPTED is received within
            *timeout_sec*, False otherwise.
        """
        try:
            self._mav.command_long_send(
                self.FCU_SYSID,
                self.FCU_COMPID,
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                0,
                0.0, 0.0, 0.0, float("nan"),
                0.0, 0.0, float(altitude_m),
            )
        except Exception:
            return False

        return self._wait_command_ack(
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            timeout_sec,
        )

    def land(self, timeout_sec: float = 5.0) -> bool:
        """Send MAV_CMD_NAV_LAND to the FCU.

        MAV_CMD_NAV_LAND parameter mapping (MAVLink spec):
          param1 – Abort altitude [m] (0 = use system default)
          param4 – Yaw angle [deg] (NaN to use current heading)
          param5 – Latitude [deg] (0 = current position)
          param6 – Longitude [deg] (0 = current position)
          param7 – Altitude [m] (0 = ground level)

        Args:
            timeout_sec: Seconds to wait for COMMAND_ACK.

        Returns:
            True if COMMAND_ACK with MAV_RESULT_ACCEPTED is received within
            *timeout_sec*, False otherwise.
        """
        try:
            self._mav.command_long_send(
                self.FCU_SYSID,
                self.FCU_COMPID,
                mavutil.mavlink.MAV_CMD_NAV_LAND,
                0,
                0.0, 0.0, 0.0, float("nan"),
                0.0, 0.0, 0.0,
            )
        except Exception:
            return False

        return self._wait_command_ack(
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            timeout_sec,
        )

    def send_bin_threshold_parameter(self, threshold: int, timeout_sec: float = 2.0) -> bool:
        return self._send_int32_param(self.PARAM_BIN_THRESHOLD, threshold, timeout_sec)

    def send_brightness_parameter(self, brightness: int, timeout_sec: float = 2.0) -> bool:
        return self._send_int32_param(self.PARAM_BRIGHTNESS, brightness, timeout_sec)

    def send_contrast_parameter(self, contrast: int, timeout_sec: float = 2.0) -> bool:
        return self._send_int32_param(self.PARAM_CONTRAST, contrast, timeout_sec)

    def send_saturation_parameter(self, saturation: int, timeout_sec: float = 2.0) -> bool:
        return self._send_int32_param(self.PARAM_SATURATION, saturation, timeout_sec)

    def send_hue_parameter(self, hue: int, timeout_sec: float = 2.0) -> bool:
        return self._send_int32_param(self.PARAM_HUE, hue, timeout_sec)

    def send_gamma_parameter(self, gamma: int, timeout_sec: float = 2.0) -> bool:
        return self._send_int32_param(self.PARAM_GAMMA, gamma, timeout_sec)

    def send_gain_parameter(self, gain: int, timeout_sec: float = 2.0) -> bool:
        return self._send_int32_param(self.PARAM_GAIN, gain, timeout_sec)

    def send_white_balance_temperature_parameter(self, wb_temp: int, timeout_sec: float = 2.0) -> bool:
        return self._send_int32_param(self.PARAM_WB_TEMP, wb_temp, timeout_sec)

    def send_sharpness_parameter(self, sharpness: int, timeout_sec: float = 2.0) -> bool:
        return self._send_int32_param(self.PARAM_SHARPNESS, sharpness, timeout_sec)

    def send_exposure_time_absolute_parameter(self, exposure_abs: int, timeout_sec: float = 2.0) -> bool:
        return self._send_int32_param(self.PARAM_EXPOSURE_ABS, exposure_abs, timeout_sec)

    def request_all_camera_settings_parameters(self, timeout_sec: float = 2.0) -> bool:
        """Request all camera setting parameters from the drone.

        This method sends PARAM_REQUEST_READ for each camera-related parameter and
        waits for corresponding PARAM_VALUE updates. Calls are throttled to avoid
        excessive request bursts.

        Args:
            timeout_sec: Total timeout budget in seconds for this bulk request.

        Returns:
            True if all parameter read requests received updated PARAM_VALUE within
            each per-parameter timeout, otherwise False.
        """
        now = time.monotonic()
        with self._camera_settings_request_lock:
            elapsed = now - self._last_camera_settings_request_sent_at
            if elapsed < self._camera_settings_request_min_interval_sec:
                self._log(
                    "[tx-skip] camera settings parameter request throttled "
                    f"({elapsed:.3f}s < {self._camera_settings_request_min_interval_sec:.3f}s)"
                )
                return False

            self._last_camera_settings_request_sent_at = now

        per_timeout = max(0.2, float(timeout_sec) / len(self.CAMERA_SETTING_PARAM_IDS))
        ok = True
        for pid in self.CAMERA_SETTING_PARAM_IDS:
            if not self._request_param_read(pid, per_timeout):
                ok = False
        return ok

    def _request_param_read(self, param_id: str, timeout_sec: float = 2.0) -> bool:
        """Send PARAM_REQUEST_READ and wait for a new PARAM_VALUE update.

        Args:
            param_id: Parameter ID to request.
            timeout_sec: Maximum time to wait for the requested parameter update.

        Returns:
            True when a newer PARAM_VALUE for ``param_id`` is observed, otherwise
            False on timeout or send failure.
        """
        key = str(param_id).strip()
        if not key:
            return False

        with self._param_cv:
            prev_seq = self._param_update_seq.get(key, 0)

        try:
            self._mav.param_request_read_send(
                self.target_sysid,
                self.target_compid,
                key.encode("ascii"),
                -1,
            )
        except Exception:
            return False

        deadline = time.monotonic() + max(0.0, float(timeout_sec))
        with self._param_cv:
            while True:
                if self._param_update_seq.get(key, 0) > prev_seq:
                    return True

                remain = deadline - time.monotonic()
                if remain <= 0.0:
                    return False

                self._param_cv.wait(timeout=remain)

    def get_bin_threshold_parameter(self) -> Optional[int]:
        """Return cached BIN_TH value as an integer.

        This method does not send MAVLink requests. Use
        ``send_bin_threshold_param_request_read`` beforehand when a refresh is
        required.
        """
        val = self.get_param_cached(self.PARAM_BIN_THRESHOLD)
        if val is None or not math.isfinite(val):
            return None
        return int(round(val))

    def send_bin_threshold_param_request_read(self, timeout_sec: float = 2.0) -> bool:
        return self._request_param_read(self.PARAM_BIN_THRESHOLD, timeout_sec)

    def send_brightness_param_request_read(self, timeout_sec: float = 2.0) -> bool:
        return self._request_param_read(self.PARAM_BRIGHTNESS, timeout_sec)

    def send_contrast_param_request_read(self, timeout_sec: float = 2.0) -> bool:
        return self._request_param_read(self.PARAM_CONTRAST, timeout_sec)

    def send_saturation_param_request_read(self, timeout_sec: float = 2.0) -> bool:
        return self._request_param_read(self.PARAM_SATURATION, timeout_sec)

    def send_hue_param_request_read(self, timeout_sec: float = 2.0) -> bool:
        return self._request_param_read(self.PARAM_HUE, timeout_sec)

    def send_gamma_param_request_read(self, timeout_sec: float = 2.0) -> bool:
        return self._request_param_read(self.PARAM_GAMMA, timeout_sec)

    def send_gain_param_request_read(self, timeout_sec: float = 2.0) -> bool:
        return self._request_param_read(self.PARAM_GAIN, timeout_sec)

    def send_white_balance_temperature_param_request_read(self, timeout_sec: float = 2.0) -> bool:
        return self._request_param_read(self.PARAM_WB_TEMP, timeout_sec)

    def send_sharpness_param_request_read(self, timeout_sec: float = 2.0) -> bool:
        return self._request_param_read(self.PARAM_SHARPNESS, timeout_sec)

    def send_exposure_time_absolute_param_request_read(self, timeout_sec: float = 2.0) -> bool:
        return self._request_param_read(self.PARAM_EXPOSURE_ABS, timeout_sec)

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

        if mtype == "COMMAND_ACK":
            if src_sys == self.FCU_SYSID and src_comp == self.FCU_COMPID:
                self._handle_command_ack(msg)
            return

        if mtype == "PARAM_VALUE":
            if src_sys == self.target_sysid and src_comp == self.target_compid:
                self._handle_param_value(msg)
            return

        self._log(f"[rx] type={mtype} sys={src_sys} comp={src_comp}")

    def _handle_command_ack(self, msg) -> None:
        try:
            cmd = int(getattr(msg, "command", -1))
            if cmd < 0:
                return

            result = int(
                getattr(msg, "result", mavutil.mavlink.MAV_RESULT_FAILED)
            )
            with self._ack_cv:
                self._ack_result[cmd] = result
                self._ack_seq[cmd] = self._ack_seq.get(cmd, 0) + 1
                self._ack_cv.notify_all()

            self._log(f"[rx] command_ack cmd={cmd} result={result}")
        except Exception:
            return

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
            
            # print(f"Received ODOMETRY: pos=({x:.2f}, {y:.2f}, {z:.2f}) quat=({qx:.3f}, {qy:.3f}, {qz:.3f}, {w:.3f})")

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
                self._param_update_seq[rx_id] = self._param_update_seq.get(rx_id, 0) + 1
                self._param_cv.notify_all()

            self._log(f"[rx] param_value id={rx_id} value={val}")
        except Exception:
            return

    def _wait_command_ack(self, cmd: int, timeout_sec: float) -> bool:
        with self._ack_cv:
            prev_seq = self._ack_seq.get(cmd, 0)

        deadline = time.monotonic() + max(0.0, float(timeout_sec))
        with self._ack_cv:
            while True:
                if self._ack_seq.get(cmd, 0) > prev_seq:
                    result = self._ack_result.get(
                        cmd,
                        mavutil.mavlink.MAV_RESULT_FAILED,
                    )
                    return result == mavutil.mavlink.MAV_RESULT_ACCEPTED

                remain = deadline - time.monotonic()
                if remain <= 0.0:
                    return False

                self._ack_cv.wait(timeout=remain)

    def get_param_cached(self, param_id: str) -> Optional[float]:
        key = param_id.strip()
        with self._param_lock:
            return self._params.get(key)

    def get_camera_settings_parameters(self) -> dict[str, Optional[int]]:
        """Return cached camera settings as a dictionary."""
        result: dict[str, Optional[int]] = {}
        for param_id in self.CAMERA_SETTING_PARAM_IDS:
            val = self.get_param_cached(param_id)
            if val is None or not math.isfinite(val):
                result[param_id] = None
            else:
                result[param_id] = int(round(val))
        return result

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

    
    def set_pose_estimation_mode_signal(self) -> None:
        try:
            self._mav.command_long_send(
                self.target_sysid,
                self.target_compid,
                self.MAV_CMD_APP_SET_POSE_ESTIMATION_MODE,
                0,
                1, 0, 0, 0, 0, 0, 0,
            )
        except Exception:
            pass

    def set_parameter_setting_mode_signal(self) -> None:
        try:
            self._mav.command_long_send(
                self.target_sysid,
                self.target_compid,
                self.MAV_CMD_APP_SET_PARAMETER_SETTING_MODE,
                0,
                1, 0, 0, 0, 0, 0, 0,
            )
        except Exception:
            pass

    def _send_int32_param(
        self,
        param_id: str,
        value: int,
        timeout_sec: float = 2.0,
    ) -> bool:
        """
        INT32パラメータを送信し、反映(=param_valueが一致)するまで待つ共通関数
        Args:
            param_id (str): MAVLink parameter id
            value (int): 設定値
            timeout_sec (float): タイムアウト秒
        Returns:
            bool: 成功ならTrue
        """
        param_id = str(param_id)
        value_i = int(value)

        try:
            self._mav.param_set_send(
                self.target_sysid,
                self.target_compid,
                param_id.encode("ascii"),
                float(value_i),
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
                    if cur_i == value_i:
                        return True

                remain = deadline - time.time()
                if remain <= 0.0:
                    return False

                self._param_cv.wait(timeout=remain)

    
    def _log(self, s: str) -> None:
        if self._enable_stdout_log:
            print(s)
