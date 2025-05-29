import socket
import time
import threading
import math
from pymavlink import mavutil

class DroneController:
    def __init__(self, remote_ip, remote_port, local_port, source_system=255):
        self.remote_addr = (remote_ip, remote_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', local_port))

        self.master = mavutil.mavlink_connection(
            device=None,
            input=self.sock,
            write=self._write_msg,
            source_system=source_system
        )

        self.target_system = None
        self.target_component = 1
        self.start_time = time.monotonic()

        self._running = threading.Event()
        self._running.set()

        self._heartbeat_thread = threading.Thread(target=self._send_heartbeat_loop, daemon=True)
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)

    def _write_msg(self, data):
        self.sock.sendto(data, self.remote_addr)

    def start(self):
        self._heartbeat_thread.start()
        self._listen_thread.start()

    def stop(self):
        self._running.clear()
        self._heartbeat_thread.join(timeout=2)
        self._listen_thread.join(timeout=2)

    def _send_heartbeat_loop(self):
        while self._running.is_set():
            self.master.mav.heartbeat_send(
                mavutil.mavlink.MAV_TYPE_GCS,
                mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                0, 0,
                mavutil.mavlink.MAV_STATE_ACTIVE
            )
            time.sleep(1)

    def _listen_loop(self):
        while self._running.is_set():
            msg = self.master.recv_match(blocking=True, timeout=1)
            if msg and msg.get_type() == 'HEARTBEAT':
                sysid = msg.get_srcSystem()
                if self.target_system is None:
                    self.target_system = sysid
                print(f"[Python] Received HEARTBEAT from sysid={sysid}")

    def wait_for_heartbeat(self):
        while self.target_system is None:
            time.sleep(0.5)

    def set_mode(self, mode_str):
        if self.target_system is None:
            return
        try:
            mode = self.master.mode_mapping()[mode_str]
        except KeyError:
            print(f"Unknown mode: {mode_str}")
            return
        self.master.mav.set_mode_send(
            self.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode
        )

    def set_arm(self, arm: bool):
        if self.target_system is None:
            return
        self.master.mav.command_long_send(
            self.target_system,
            self.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1 if arm else 0,
            0, 0, 0, 0, 0, 0
        )

    def send_guided_position(self, x, y, z, yaw_deg):
        if self.target_system is None:
            return
        yaw_rad = math.radians(yaw_deg)
        type_mask = (
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_VX_IGNORE |
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_VY_IGNORE |
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_VZ_IGNORE |
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_AX_IGNORE |
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_AY_IGNORE |
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_AZ_IGNORE |
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_RATE_IGNORE
        )
        time_boot_ms = int((time.monotonic() - self.start_time) * 1000)
        self.master.mav.set_position_target_local_ned_send(
            time_boot_ms,
            self.target_system,
            self.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_ENU,
            type_mask,
            x, y, z,
            0, 0, 0,
            0, 0, 0,
            yaw_rad, 0
        )
