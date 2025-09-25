import socket
import time
import threading
import math
from typing import Optional
from pymavlink import mavutil


class DroneState:
    """
    ドローンの状態を保持するクラス。
    現状は未使用。必要に応じて拡張可能。
    """
    def __init__(self):
        self.mode = "UNKNOWN"  # フライトモード
        self.armed = False     # アーム状態
        self.battery_voltage = 0.0
        self.battery_remaining = 0
        self.position = [0.0, 0.0, 0.0]  # x, y, z
        self.attitude = [0.0, 0.0, 0.0]  # roll, pitch, yaw


class MavlinkClient:
    """
    UDPベースのMAVLinkクライアント。
    コンテナ間通信やホスト名解決を前提とし、
    IPまたはコンテナ名（ホスト名）で接続先を指定可能。

    主な機能:
      - ハートビート送信（定期的）
      - モード切替コマンド送信
      - 2値化閾値コマンド送信とACK受信
      - ダミーのドローン位置・姿勢取得（サンプル用）

    Parameters:
        host (str): 送信先IPまたはホスト名
        port (int): 送信先UDPポート（デフォルト: 14610）
        local_port (int): 受信UDPポート（デフォルト: 14611）
        my_sysid (int): 自システムID（デフォルト: 250）
        my_compid (int): 自コンポーネントID（デフォルト: 190）
        target_sysid (int): 送信先システムID（デフォルト: 201）
        target_compid (int): 送信先コンポーネントID（デフォルト: 191）
        heartbeat_hz (float): ハートビート送信周波数（Hz, デフォルト: 1.0）
    """

    def __init__(
        self,
        host: str,
        port: int = 14610,
        local_port: int = 14611,
        my_sysid: int = 250,
        my_compid: int = 190,
        target_sysid: int = 201,
        target_compid: int = 191,
        heartbeat_hz: float = 1.0,
    ):
        # スレッド制御用フラグ・リスト
        self._running = True
        self._threads = []

        # 接続設定
        self.host = host
        self.port = port
        self.local_port = local_port

        self.my_sysid = my_sysid
        self.my_compid = my_compid
        self.target_sysid = target_sysid
        self.target_compid = target_compid

        # FCU用ID（未使用、必要なら利用）
        self.fcu_sysid = 1
        self.fcu_compid = 1

        # MAVLink送信用コネクション
        self.mav_out = mavutil.mavlink_connection(
            f"udpout:{self.host}:{self.port}",
            source_system=self.my_sysid,
            source_component=self.my_compid
        )

        # MAVLink受信用コネクション
        self.mav_in = mavutil.mavlink_connection(
            f"udpin:0.0.0.0:{self.local_port}"
        )

        # サンプル用ダミー値（本番は実データ取得に置換）
        self.drone_pos = [1.0, 1.0, 1.0]  # x, y, z
        self.drone_pose = [0.2, 0.4, 0.6, 1.0]  # x, y, z, w (quaternion)

        # ハートビート送信スレッド起動
        self._heartbeat_interval = 1.0 / max(heartbeat_hz, 0.1)
        t1 = threading.Thread(target=self._send_heartbeat, daemon=True)
        t1.start()
        self._threads.append(t1)

    def _send_heartbeat(self):
        """
        一定間隔でハートビートを送信する内部スレッド処理。
        通信途絶時は例外を握りつぶしてリトライ。
        """
        while self._running:
            try:
                self.mav_out.mav.heartbeat_send(
                    mavutil.mavlink.MAV_TYPE_GCS,
                    mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                    0,
                    0,
                    mavutil.mavlink.MAV_STATE_ACTIVE,
                )
            except Exception:
                # 通信途絶など一時的な例外は握りつぶしてリトライ
                pass
            time.sleep(self._heartbeat_interval)

    def stop(self):
        """
        スレッド停止・コネクション解放。
        明示的に呼び出してリソースをクリーンアップ。
        """
        self._running = False
        for t in self._threads:
            t.join(timeout=1.0)
        try:
            self.mav_out.close()
            self.mav_in.close()
        except Exception:
            pass

    def get_drone_position(self) -> list[float]:
        """
        ドローンの位置（x, y, z）を取得（現状ダミー値）。
        Returns:
            list[float]: [x, y, z]
        """
        return self.drone_pos

    def get_drone_quaternion(self) -> list[float]:
        """
        ドローンの姿勢（クォータニオン: x, y, z, w）を取得（現状ダミー値）。
        Returns:
            list[float]: [x, y, z, w]
        """
        return self.drone_pose

    def set_config_mode_signal(self):
        """
        設定モード切替コマンドを送信。
        呼び出し側で2Hz程度で定期的に呼び出すことを想定。
        """
        self.mav_out.mav.command_long_send(
            self.target_sysid,
            self.target_compid,
            31000,  # MAV_CMD_MY_APP_SET_MODE
            0,
            1, 0, 0, 0, 0, 0, 0,
        )

    def send_bin_threshold(self, threshold: int) -> bool:
        """
        2値化の閾値をコンパニオン側に送信し、ACK応答で成否を返す。
        Args:
            threshold (int): 2値化の閾値
        Returns:
            bool: ACK受信かつ受理された場合True、失敗時False
        """
        self.mav_out.mav.command_long_send(
            self.target_sysid,
            self.target_compid,
            31001,  # MAV_CMD_MY_APP_SET_BIN_THRESHOLD
            0,
            threshold, 0, 0, 0, 0, 0, 0,
        )
        try:
            print("Waiting for ACK on 14611")
            msg = self.mav_in.recv_match(type="COMMAND_ACK", blocking=True, timeout=2)
            print("Received ACK:", msg)
            if msg:
                print("command:", getattr(msg, 'command', None))
                print("result:", getattr(msg, 'result', None))
                print("sysid:", getattr(msg, 'get_srcSystem', lambda: None)())
                print("compid:", getattr(msg, 'get_srcComponent', lambda: None)())
                if msg.command == 31001 and msg.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
                    return True
            return False
        except Exception:
            return False

    def send_recording_param(self, is_recording: bool):
        """
        録画パラメータコマンドを送信。
        """
        send_recording_param = 0
        if is_recording == True:
            send_recording_param = 1
        else:
            send_recording_param = 0

        self.mav_out.mav.command_long_send(
            self.target_sysid,
            self.target_compid,
            31002,  # MAV_CMD_MY_APP_RECORDING_PARAM
            0,
            send_recording_param, 0, 0, 0, 0, 0, 0,
        )
    
    def __del__(self):
        """
        デストラクタ。明示的にstop()が呼ばれない場合でも可能な限りクリーンアップ。
        """
        try:
            self.stop()
        except Exception:
            pass
