import socket
import time
import threading
import math
from pymavlink import mavutil

class DroneController:
    def __init__(self, remote_ip, remote_port, local_port, source_system=255):
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.local_port = local_port
        self.source_system = source_system

        self.recv_conn = mavutil.mavlink_connection(f'udp:0.0.0.0:{local_port}')
        self.send_conn = mavutil.mavlink_connection(f'udpout:{remote_ip}:{remote_port}', source_system=source_system)

        self.target_system = None
        self.target_component = 1
        self.start_time = time.monotonic()

        self._running = threading.Event()
        self._running.set()

        self._heartbeat_thread = threading.Thread(target=self._send_heartbeat_loop, daemon=True)
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._heartbeat_thread.start()
        self._listen_thread.start()

    def stop(self):
        self._running.clear()
        try:
            if self._heartbeat_thread and self._heartbeat_thread.is_alive():
                self._heartbeat_thread.join(timeout=2)
        except Exception as e:
            print(f"[stop] Error stopping heartbeat thread: {e}")
        try:
            if self._listen_thread and self._listen_thread.is_alive():
                self._listen_thread.join(timeout=2)
        except Exception as e:
            print(f"[stop] Error stopping listen thread: {e}")

        self._heartbeat_thread = None
        self._listen_thread = None

        try:
            if self.recv_conn:
                self.recv_conn.close()
        except Exception as e:
            print(f"[stop] Error closing recv_conn: {e}")

        try:
            if self.send_conn:
                self.send_conn.close()
        except Exception as e:
            print(f"[stop] Error closing send_conn: {e}")

    def __del__(self):
        try:
            self.stop()
            print("[DroneController] __del__ called. Resources cleaned up.")
        except Exception as e:
            print(f"[DroneController] __del__ encountered an error: {e}")

    def is_running(self):
        return (
            self._heartbeat_thread is not None and self._heartbeat_thread.is_alive() and
            self._listen_thread is not None and self._listen_thread.is_alive()
        )

    def _send_heartbeat_loop(self):
        while self._running.is_set():
            try:
                self.send_conn.mav.heartbeat_send(
                    mavutil.mavlink.MAV_TYPE_GCS,
                    mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                    0, 0,
                    mavutil.mavlink.MAV_STATE_ACTIVE
                )
            except Exception as e:
                print(f"[heartbeat] send error: {e}")
            time.sleep(1)

    def _listen_loop(self):
        while self._running.is_set():
            try:
                msg = self.recv_conn.recv_match(blocking=True, timeout=1)
                if msg and msg.get_type() == 'HEARTBEAT':
                    sysid = msg.get_srcSystem()
                    if self.target_system is None:
                        self.target_system = sysid
                    print(f"[Python] Received HEARTBEAT from sysid={sysid}")
            except Exception as e:
                print(f"[listen] receive error: {e}")

    def wait_for_heartbeat(self):
        while self.target_system is None:
            time.sleep(0.5)

    def set_mode(self, mode_str):
        if self.target_system is None:
            return
        try:
            mode = self.send_conn.mode_mapping()[mode_str]
            self.send_conn.mav.set_mode_send(
                self.target_system,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                mode
            )
        except KeyError:
            print(f"[set_mode] Unknown mode: {mode_str}")
        except Exception as e:
            print(f"[set_mode] Error: {e}")

    def set_arm(self, arm: bool):
        if self.target_system is None:
            return
        try:
            self.send_conn.mav.command_long_send(
                self.target_system,
                self.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,
                1 if arm else 0,
                0, 0, 0, 0, 0, 0
            )
        except Exception as e:
            print(f"[set_arm] Error: {e}")

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
        try:
            self.send_conn.mav.set_position_target_local_ned_send(
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
        except Exception as e:
            print(f"[send_guided_position] Error: {e}")
