import socket
import json
from typing import Dict

class Wifi:
    def __init__(self, drone_ip="192.168.0.10", port=8889):
        """
        Initialize the Wifi class.

        :param drone_ip: The IP address of the drone. Default is "192.168.0.10".
        :type drone_ip: str
        :param port: The port number to use. Default is 8889.
        :type port: int
        """
        self.drone_ip = drone_ip
        self.port = port
        self.udp_socket = None

        self.udp_setup()

    def udp_setup(self):
        """
        Set up UDP communication.
        
        Creates a socket using the specified IP address and port number, and saves it to the instance variable.
        """
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.connect((self.drone_ip, self.port))

    def udp_send(self, data: Dict[str, float]):
        """
        Send data (in JSON format) to a specific IP address.
        
        The data is converted to JSON format and sent.

        :param data: The data to be sent. Given as a dictionary.
        :type data: dict
        :raises ValueError: If the UDP socket is not set up.
        """
        if self.udp_socket is None:
            raise ValueError("UDP socket is not set up. Call udp_setup() first.")
        
        json_data = json.dumps(data)
        self.udp_socket.sendall(json_data.encode('utf-8'))
