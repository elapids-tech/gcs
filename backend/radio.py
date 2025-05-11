import socket
import threading
import asyncio
import struct

# uint8_t, uint32_t, 4 doubles, uint8_t
RX_PACKET_FORMAT = "<B I dddd B"
RX_PACKET_SIZE = struct.calcsize(RX_PACKET_FORMAT)
receive_data_type = ["DRONE_WORLD_POS", "DRONE_WORLD_QUAT"]

# uint8_t, uint32_t, 3 doubles, uint8_t
TX_PACKET_FORMAT = "<B I ddd B"
TX_PACKET_SIZE = struct.calcsize(TX_PACKET_FORMAT)
send_data_type = ["HEART_BEAT", "CONTROL_PACKET", "DATA_PACKET"]

class Radio:
    def __init__(self, drone_ip="192.168.0.10", port=8889):

        self.drone_ip = drone_ip
        self.port = port
        self.udp_socket = None

        self.is_running = False
        self.heart_beat_sending_flag = False

        self.rx_buffer = []
        self.tx_buffer = []

        self.udp_setup()

        # スレッドを立ち上げる
        self.thread = threading.Thread(target=self.send_heart_beat, daemon=True)
        self.is_running = True
        self.thread.start()

    def calculate_checksum(self, data_bytes):
        checksum = 0
        for b in data_bytes:
            checksum ^= b
        return checksum

    def udp_setup(self):

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.connect((self.drone_ip, self.port))

        self.is_running = True
        self.heart_beat_sending_flag = True

    async def send_heart_beat(self):
        while self.is_running:
            await asyncio.sleep(1)
            if self.heart_beat_sending_flag:
                index = send_data_type.index("HEART_BEAT")
                # 'B' は unsigned char = uint8_t
                packed_index = struct.pack('B', index)

                # UDP送信
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(packed_index, ('127.0.0.1', 5005)) 

    async def receive(self):
        while self.is_running:
            data, addr = sock.recvfrom(1024)
            if len(data) >= TX_PACKET_SIZE:
                raw = data[:-1]
                received_checksum = data[-1]
                calc_checksum = self.calculate_checksum(raw)
                if received_checksum == calc_checksum:
                    unpacked = struct.unpack(TX_PACKET_FORMAT, data)
                    self.rx_buffer.append(unpacked)

    def popRxBuffer(self):

        # self.rx_bufferからfifoで値を取得

        unpacked = struct.unpack(TX_PACKET_FORMAT, data)

        data_type = unpacked[0]
        [unpacked[2], unpacked[3], unpacked[4], unpacked[5]]

        return type, data

    def send_immediate(self, type, data):
        # 
        # type is uint8_t

        # get current time 
        time_stamp = 

        checksum = self.calculate_checksum()

        send_packet = 
        sock.sendto(send_packet, dest_addr)

        # 成功したらtrue

        # 失敗したらfalse

