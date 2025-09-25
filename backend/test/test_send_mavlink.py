from pymavlink import mavutil
import time
from backend.mavlink_client import MavlinkClient

def test_send_heartbeat_three_times():
    master = mavutil.mavlink_connection('udpout:192.168.0.3:14551')
    for i in range(3):
        master.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_QUADROTOR,
            mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
            0, 0, 0
        )
        print(f"sent heartbeat {i+1}")
        time.sleep(1)

def test_send_bin_threshold():
    mavlink_client = MavlinkClient(host="drone")
    threshold = 1000
    result = mavlink_client.send_bin_threshold(threshold)
    print(f"send_bin_threshold result: {result}")
    assert result is True, "send_bin_threshold failed"

def test_control_recording():
    mavlink_client = MavlinkClient(host="drone")

    result = mavlink_client.send_recording_param(True)
    print(f"send_recording_param result: {result}")
    assert result is True, "send_recording_param failed"

    result = mavlink_client.send_recording_param(False)
    print(f"send_recording_param result: {result}")
    assert result is True, "send_recording_param failed"


if __name__ == "__main__":
    # test_send_heartbeat_three_times()
    test_send_bin_threshold()

