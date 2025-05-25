from pymavlink import mavutil
import threading
import time
import math

class DroneController:
    def __init__(self, connection_string='udpout:127.0.0.1:14551', source_system=255):
        self.master = mavutil.mavlink_connection(connection_string, source_system=source_system)
        self.target_system = None
        self.target_component = 1
        self.start_time = time.monotonic()

        self._running = threading.Event()
        self._running.set()

        self._heartbeat_thread = threading.Thread(target=self._send_heartbeat_loop, daemon=True)
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)

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
            target_system=self.target_system,
            target_component=self.target_component,
            command=mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            confirmation=0,
            param1=1 if arm else 0,
            param2=0, param3=0, param4=0,
            param5=0, param6=0, param7=0
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

    def flight_test(self):
        self.wait_for_heartbeat()

        self.set_arm(True)
        time.sleep(2)

        self.set_mode("GUIDED")
        time.sleep(2)

        for i in range(20):
            angle = i * 18
            radius = 3.0
            x = radius * math.cos(math.radians(angle))
            y = radius * math.sin(math.radians(angle))
            z = 5.0
            self.send_guided_position(x, y, z, yaw_deg=angle)
            time.sleep(0.5)

        self.set_mode("LAND")
        time.sleep(5)

        self.set_arm(False)

# --- 使用例 ---
if __name__ == "__main__":
    drone = DroneController()
    try:
        drone.start()
        drone.flight_test()
    finally:
        drone.stop()
