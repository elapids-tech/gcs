import socket
import time
import threading
import math
from pymavlink import mavutil

class DroneState:
    def __init__(self):
        self.mode = "UNKNOWN"
        self.armed = False
        self.battery_voltage = 0.0
        self.battery_remaining = 0
        self.position = [0.0, 0.0, 0.0]  # x, y, z
        self.attitude = [0.0, 0.0, 0.0]  # roll, pitch, yaw

class MavlinkClient:
    def __init__(self):
        # ハートビート送信用スレッド
        self._running = True
        self._threads = []

        # mavlink 接続設定
        self.local_port = 14610
        self.drone_app_ip = "192.168.0.6"
        self.drone_app_port = 14610
        self.my_sysid = 250
        self.my_compid = 190
        self.target_sysid = 201
        self.target_compid = 191
        self.fcu_sysid = 1
        self.fcu_compid = 1
        self.mav = mavutil.mavlink_connection(
            f'udpout:{self.drone_app_ip}:{self.drone_app_port}',
            source_system=self.my_sysid,
            source_component=self.my_compid
        )

        # drone state, telemetry情報
        self.drone_pos = [1.0, 1.0, 1.0]
        self.drone_pose = [0.2, 0.4, 0.6, 1.0]  # x,y,z,w

        t1 = threading.Thread(target=self._send_heartbeat, daemon=True)
        t1.start()
        self._threads.append(t1)

    def _send_heartbeat(self):
        while self._running:
            self.mav.mav.heartbeat_send(
                mavutil.mavlink.MAV_TYPE_GCS,
                mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                0, 0, mavutil.mavlink.MAV_STATE_ACTIVE
            )
            time.sleep(1.0)

    def stop(self):
        self._running = False
        for t in self._threads:
            t.join()

    def get_drone_position(self):
        return self.drone_pos
    
    def get_drone_quaternion(self):
        return self.drone_pose

    def set_config_mode_signal(self):
        """
        呼び出し側で2Hzで定期的に呼び出すことを想定している。
        """
        self.mav.mav.command_long_send(
            self.target_sysid, self.target_compid,
            31000,  # MAV_CMD_MY_APP_SET_MODE
            0,
            1, 0, 0, 0, 0, 0, 0
        )

    def set_bin_threshold(self, threshold: int):
        """
        2値化の閾値を設定する。
        """
        self.mav.mav.command_long_send(
            self.target_sysid, self.target_compid,
            31001,  # MAV_CMD_MY_APP_SET_BIN_THRESHOLD
            0,
            threshold, 0, 0, 0, 0, 0, 0
        )

    def __del__(self):
        self.stop()
