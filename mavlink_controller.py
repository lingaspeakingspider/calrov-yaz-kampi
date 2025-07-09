import logging
import numpy as np
from pymavlink import mavutil
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Any


class MAVLinkWorker(QThread):
    connection_status_changed = pyqtSignal(str)
    telemetry_updated = pyqtSignal(float, float, float, float)

    def __init__(self, connection_string='udp:127.0.0.1:14551', simulation: bool = False):
        super().__init__()
        self.master: Any = None
        self.connection_string = connection_string
        self.master = None
        self.running = True
        self.simulation = simulation

        self.default_modes = {
            'STABILIZE': 0, 'ACRO': 1, 'ALT_HOLD': 2, 'AUTO': 3, 'GUIDED': 4,
            'LOITER': 5, 'RTL': 6, 'CIRCLE': 7, 'LAND': 9, 'MANUAL': 10
        }

        self.last_roll = 0.0
        self.last_pitch = 0.0
        self.last_yaw = 0.0
        self.last_depth = 0.0

    def run(self):
        if self.simulation:
            logging.info("MAVLink worker started in SIMULATION mode.")
            self.connection_status_changed.emit("Connected (SIMULATION)")
            while self.running:
                self.msleep(200)
            logging.info("MAVLink simulation thread stopped.")
            return

        try:
            logging.info(f"Connecting to vehicle on: {self.connection_string}")
            self.master = mavutil.mavlink_connection(
                self.connection_string, autoreconnect=True)
            if self.master is not None:
                self.master.wait_heartbeat()
            logging.info("Heartbeat received! Connection established.")
            self.connection_status_changed.emit(
                f"Connected to SYSID:{self.master.target_system}")

            self.master.mav.request_data_stream_send(
                self.master.target_system, self.master.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_ALL, 4, 1)

            while self.running:
                msg = self.master.recv_match(
                    type=['ATTITUDE', 'VFR_HUD'], blocking=True, timeout=1)
                if not msg:
                    continue
                msg_type = msg.get_type()
                if msg_type == 'ATTITUDE':
                    self.last_roll, self.last_pitch, self.last_yaw = np.degrees(
                        msg.roll), np.degrees(msg.pitch), np.degrees(msg.yaw)
                elif msg_type == 'VFR_HUD':
                    self.last_depth = msg.alt
                self.telemetry_updated.emit(
                    self.last_roll, self.last_pitch, self.last_yaw, self.last_depth)
        except Exception as e:
            logging.error(f"MAVLink connection error: {e}")
            self.connection_status_changed.emit("Disconnected")
        finally:
            if self.master:
                self.master.close()
            logging.info("MAVLink thread stopped.")

    def stop(self):
        self.running = False
        self.wait()

    def arm_disarm(self, arm: bool):
        if self.simulation:
            logging.info(
                f"[SIM] Command {'ARM' if arm else 'DISARM'} received.")
            return
        if not self.master:
            return
        self.master.mav.command_long_send(...)
        logging.info(f"Command {'ARM' if arm else 'DISARM'} sent.")

    def set_mode(self, mode_name: str):
        if self.simulation:
            logging.info(
                f"[SIM] Command to set mode to '{mode_name}' received.")
            return
        if not self.master:
            return
        logging.info(f"Command to set mode to '{mode_name}' sent.")

    def set_rc_override(self, roll, pitch, throttle, yaw):
        if self.simulation:
            self.last_roll = np.interp(roll, [1100, 1900], [-45, 45])
            self.last_pitch = np.interp(pitch, [1100, 1900], [-45, 45])
            self.last_yaw = np.interp(yaw, [1100, 1900], [-180, 180])
            self.last_depth = np.interp(throttle, [1100, 1900], [0, 50])

            self.telemetry_updated.emit(
                self.last_roll, self.last_pitch, self.last_yaw, self.last_depth)
            return

        if not self.master:
            return
        self.master.mav.rc_channels_override_send(
            self.master.target_system, self.master.target_component,
            int(pitch), int(roll), int(throttle), int(yaw), 0, 0, 0, 0)
