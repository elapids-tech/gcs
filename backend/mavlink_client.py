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
        local_port: int = 14610,
        my_sysid: int = 250,
        my_compid: int = 190,
        target_sysid: int = 1,
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

        self.px4_raw_pos = [0.0, 0.0, 0.0]  # PX4 LOCAL_FRD
        self.px4_raw_quat = [0.0, 0.0, 0.0, 1.0]  # PX4 quaternion

        # ハートビート送信スレッド起動
        self._heartbeat_interval = 1.0 / max(heartbeat_hz, 0.1)
        t1 = threading.Thread(target=self._send_heartbeat, daemon=True)
        t1.start()
        self._threads.append(t1)

        # 受信メッセージ処理スレッド起動
        t2 = threading.Thread(target=self._read_message_to_me, daemon=True)
        t2.start()
        self._threads.append(t2)

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

    def _read_message_to_me(self):
        while self._running:
            try:
                msg = self.mav_in.recv_match(blocking=True, timeout=1.0)
            except Exception:
                continue

            if msg is None:
                continue

            try:
                src_sys = msg.get_srcSystem()
                src_comp = msg.get_srcComponent()
            except Exception:
                continue

            if src_sys != self.target_sysid or src_comp != self.target_compid:
                continue

            mtype = msg.get_type()

            if mtype == "ODOMETRY":
                try:
                    x = float(getattr(msg, "x", 0.0))
                    y = float(getattr(msg, "y", 0.0))
                    z = float(getattr(msg, "z", 0.0))

                    q = getattr(msg, "q", None)
                    if q is None or len(q) < 4:
                        continue

                    w  = float(q[0])
                    qx = float(q[1])
                    qy = float(q[2])
                    qz = float(q[3])

                    # NaN / inf が含まれていたらこのメッセージは捨てる
                    vals = (x, y, z, w, qx, qy, qz)
                    if not all(math.isfinite(v) for v in vals):
                        continue

                    self.px4_raw_pos = [x, y, z]
                    self.px4_raw_quat = [qx, qy, qz, w]

                except Exception:
                    continue
   
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
        ドローンから受信した位置テレメトリーデータをz-up右手座標系に変換して返す。
        Returns:
            list[float]: [x, y, z]
        """
        fx, fy, fz = self.px4_raw_pos  # PX4 FRD (z-down)
        ex = fx
        ey = -fy
        ez = -fz
        return [ex, ey, ez]
    
    def get_drone_quaternion(self) -> list[float]:
        """
        ドローンから受信したクォータニオンテレメトリーデータをz-up右手座標系に変更してリターンする。
        Returns:
            list[float]: [x, y, z, w]
        """
        qx, qy, qz, qw = self.px4_raw_quat  # PX4生データ [x, y, z, w] (z-down)

        # PX4生クォータニオン -> (w, x, y, z)
        w = qw
        x = qx
        y = qy
        z = qz

        # 正規化
        n = (w * w + x * x + y * y + z * z) ** 0.5
        if n == 0.0:
            return [0.0, 0.0, 0.0, 1.0]
        w /= n
        x /= n
        y /= n
        z /= n

        # クォータニオン -> 回転行列 (body -> world, z-down)
        R00 = 1.0 - 2.0 * (y * y + z * z)
        R01 = 2.0 * (x * y - z * w)
        R02 = 2.0 * (x * z + y * w)

        R10 = 2.0 * (x * y + z * w)
        R11 = 1.0 - 2.0 * (x * x + z * z)
        R12 = 2.0 * (y * z - x * w)

        R20 = 2.0 * (x * z - y * w)
        R21 = 2.0 * (y * z + x * w)
        R22 = 1.0 - 2.0 * (x * x + y * y)

        # 世界座標 z-down -> z-up への変換
        # 位置の変換 ex = fx, ey = -fy, ez = -fz に対応させるため、
        # 姿勢は R_zup = T * R_zdown, T = diag(1, -1, -1)
        R00p = R00
        R01p = R01
        R02p = R02

        R10p = -R10
        R11p = -R11
        R12p = -R12

        R20p = -R20
        R21p = -R21
        R22p = -R22

        # 回転行列 -> クォータニオン (w, x, y, z)
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

        # 戻り値は z-up 右手系の [x, y, z, w]
        return [qx2, qy2, qz2, qw2]

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
