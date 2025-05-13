import socket
import threading
import struct
import time

# 受信パケット: type, timestamp, 4つのdouble, checksum
RX_PACKET_FORMAT = "<B I dddd B"
RX_PACKET_SIZE = struct.calcsize(RX_PACKET_FORMAT)
receive_data_type = ["DRONE_WORLD_POS", "DRONE_WORLD_QUAT"]

# 送信種別（インデックスと一致）
send_data_type = ["HEART_BEAT", "CONTROL_PACKET", "DATA_PACKET"]

# 送信パケットフォーマット
TX_CONTROL_PACKET_FORMAT = "<B I B B"  # type, timestamp, data, checksum
TX_CONTROL_PACKET_SIZE = struct.calcsize(TX_CONTROL_PACKET_FORMAT)
control_command = ["DISARM", "ARM", "TAKEOFF", "LAND", "GO_HOME", "SET_MODE"]

TX_PACKET_FORMAT = "<B I ddd B"       # type, timestamp, 3 doubles, checksum
TX_PACKET_SIZE = struct.calcsize(TX_PACKET_FORMAT)


class Radio:
    def __init__(self, recv_ip="0.0.0.0", recv_port=5001, send_ip="drone", send_port=5000):
        self.recv_ip = recv_ip
        self.recv_port = recv_port
        self.send_ip = send_ip
        self.send_port = send_port

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.recv_ip, self.recv_port))

        self.is_running = True
        self.heart_beat_sending_flag = True
        self.rx_buffer = []

        self.heartbeat_thread = threading.Thread(target=self.send_heart_beat, daemon=True)
        self.receive_thread = threading.Thread(target=self.receive, daemon=True)
        self.heartbeat_thread.start()
        self.receive_thread.start()

    def __del__(self):
        self.shutdown()

    def shutdown(self):
        self.is_running = False
        try:
            self.udp_socket.close()
        except:
            pass
        if self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=1)
        if self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1)

    def calculate_checksum(self, data_bytes):
        checksum = 0
        for b in data_bytes:
            checksum ^= b
        return checksum

    def send_heart_beat(self):
        while self.is_running:
            time.sleep(1)
            if self.heart_beat_sending_flag:
                type_index = send_data_type.index("HEART_BEAT")
                try:
                    packet = struct.pack("B", type_index)
                    self.udp_socket.sendto(packet, (self.send_ip, self.send_port))
                except Exception as e:
                    print(f"[send_heart_beat] Error: {e}")

    def receive(self):
        while self.is_running:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                print(f"[recv] from {addr}, size={len(data)}")

                if len(data) == RX_PACKET_SIZE:
                    raw = data[:-1]
                    checksum = data[-1]
                    if self.calculate_checksum(raw) == checksum:
                        unpacked = struct.unpack(RX_PACKET_FORMAT, data)
                        self.rx_buffer.append(unpacked)
            except Exception as e:
                print(f"[receive] Error: {e}")
                break

    def popRxBuffer(self):
        if not self.rx_buffer:
            return None, None
        unpacked = self.rx_buffer.pop(0)
        data_type = receive_data_type[unpacked[0]] if unpacked[0] < len(receive_data_type) else "UNKNOWN"
        data = unpacked[2:6]  # 4つのdouble
        return data_type, data

    def send_immediate(self, data_type_str, data):
        if data_type_str not in send_data_type or data_type_str == "HEART_BEAT":
            return False

        type_index = send_data_type.index(data_type_str)
        timestamp = int(time.time() * 1000)

        try:
            if data_type_str == "CONTROL_PACKET":
                assert isinstance(data, int) and 0 <= data <= 255
                packed = struct.pack(TX_CONTROL_PACKET_FORMAT[:-1], type_index, timestamp, data)
                checksum = self.calculate_checksum(packed)
                packet = packed + struct.pack('B', checksum)

            elif data_type_str == "DATA_PACKET":
                assert isinstance(data, (list, tuple)) and len(data) == 3
                packed = struct.pack(TX_PACKET_FORMAT[:-1], type_index, timestamp, *data)
                checksum = self.calculate_checksum(packed)
                packet = packed + struct.pack('B', checksum)

            else:
                return False

            self.udp_socket.sendto(packet, (self.send_ip, self.send_port))
            return True

        except Exception as e:
            print(f"[send_immediate] Send failed: {e}")
            return False
