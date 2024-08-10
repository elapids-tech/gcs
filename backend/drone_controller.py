import json
import socket
import time
import threading
import numpy as np
from scipy.spatial.transform import Rotation as R

class DroneController:
    def __init__(self, interval=1, host='192.168.0.1', port=5000, recv_port=5001):
        self.drone_state = 0
        self.interval = interval
        self.host = host
        self.port = port
        self.recv_port = recv_port
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.received_data = None

    def start(self):
        self.send_thread = threading.Thread(target=self._send, daemon=True)
        self.recv_thread = threading.Thread(target=self._receive, daemon=True)
        self.send_thread.start()
        self.recv_thread.start()

    def stop(self):
        self.stop_event.set()
        self.send_thread.join()
        self.recv_thread.join()    
    
    def set_drone_state(self, state: int):
        with self.lock:
            self.drone_state = state
            print(f"Drone state set to: {self.drone_state}")

    def get_received_data(self):
        with self.lock:
            return self.received_data
        
    def get_drone_attitude_axis(self): 
        with self.lock: 
            if self.received_data is None:
                return None

            x_axis = np.array([0.2, 0, 0])  
            y_axis = np.array([0, 0.2, 0]) 
            z_axis = np.array([0, 0, 0.2])    

            # rotation を Rotation オブジェクトに変換
            rotation = R.from_rotvec(np.array(self.received_data['rvec']))
            translation = np.array(self.received_data['tvec'])

            rotated_x_axis = rotation.apply(x_axis) + translation
            rotated_y_axis = rotation.apply(y_axis) + translation
            rotated_z_axis = rotation.apply(z_axis) + translation

            attitude_axis = [{"points":[translation.tolist(), rotated_x_axis.tolist()], "color":"red"},
                             {"points":[translation.tolist(), rotated_y_axis.tolist()], "color":"green"},
                             {"points":[translation.tolist(), rotated_z_axis.tolist()], "color":"blue"}]
        
            return attitude_axis


    def _send(self):
        while not self.stop_event.is_set():
            send_data = {'time': time.time(), 'state': self.drone_state}
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    json_data = json.dumps(send_data)
                    sock.sendto(json_data.encode('utf-8'), (self.host, self.port))
            except Exception as e:
                print(f"Error sending data: {e}")
            time.sleep(self.interval)

    def _receive(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(('', self.recv_port))
            while not self.stop_event.is_set():
                try:
                    data, addr = sock.recvfrom(1024)
                    received_message = json.loads(data.decode('utf-8'))
                    with self.lock:
                        self.received_data = received_message
                    # print(f"Received: {received_message} from {addr}")
                except Exception as e:
                    print(f"Error receiving data: {e}")


if __name__ == '__main__':
    drone = DroneController()
    