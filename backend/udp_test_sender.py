import socket
import json

HOST = "backend"  # コンテナ名を使用
PORT = 5001
MESSAGE = b"Hello, UDP!"
send_data = {'time': 111, 'state': 222}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
json_data = json.dumps(send_data)
sock.sendto(json_data.encode('utf-8'), (HOST, PORT))
print("Message sent")