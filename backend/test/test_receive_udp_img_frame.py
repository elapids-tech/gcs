import socket
import cv2
import numpy as np

def main():
    UDP_IP = "0.0.0.0"
    UDP_PORT = 5001

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.settimeout(5.0)  # 5秒間データが来なければ終了とみなす

    print(f"Listening on {UDP_IP}:{UDP_PORT}")

    # 保存設定
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output_filename = "received_output.mp4"
    fps = 10.0
    frame_size = (1280, 800)  # (幅, 高さ)

    out = cv2.VideoWriter(output_filename, fourcc, fps, frame_size, isColor=False)
    if not out.isOpened():
        print("Failed to open VideoWriter. Check codec support.")
        sock.close()
        return

    frame_count = 0

    while True:
        try:
            data, addr = sock.recvfrom(65535)
            if not data:
                continue

            np_data = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(np_data, cv2.IMREAD_GRAYSCALE)  # モノクロでデコード

            if frame is None:
                print("Frame decode failed, skipping...")
                continue

            # サイズが一致しない場合はリサイズ
            if frame.shape[1] != frame_size[0] or frame.shape[0] != frame_size[1]:
                frame = cv2.resize(frame, frame_size)

            out.write(frame)
            frame_count += 1
            print(f"Received frame {frame.shape} from {addr}")

        except socket.timeout:
            print("No more data received. Closing...")
            break
        except Exception as e:
            print("Error:", e)
            break

    out.release()
    sock.close()

    if frame_count > 0:
        print(f"Saved {frame_count} frames to {output_filename}")
    else:
        print("No frames received, video not saved.")

if __name__ == "__main__":
    main()
