import logging as log
from pymavlink import mavutil

class Connection:
    def __init__(self) -> None:
        self.mav = mavutil.mavlink_connection("udpin:127.0.0.1:14550")
        #self.mav.wait_heartbeat()
        self.mav.recv_match(type='HEARTBEAT')
        log.info("Connection established with MAVLink")