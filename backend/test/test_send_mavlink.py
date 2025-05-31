from pymavlink import mavutil
import time

master = mavutil.mavlink_connection('udpout:192.168.0.3:14551')

while True:
    master.mav.heartbeat_send(
        mavutil.mavlink.MAV_TYPE_QUADROTOR,
        mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
        0, 0, 0
    )
    print("sent heartbeat")
    time.sleep(1)
