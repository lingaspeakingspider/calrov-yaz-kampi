import sys
import cv2
import numpy as np
import logging
from ultralytics import YOLO
from pymavlink import mavutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QSlider, QGroupBox, QFormLayout, QComboBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap

class LevelColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[34m',     # Blue
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[41m', # Red background
    }
    RESET = '\033[0m'

    def format(self, record):
        original_levelname = record.levelname
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        formatted = super().format(record)
        record.levelname = original_levelname
        return formatted

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = LevelColorFormatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

class MAVLinkWorker(QThread):
    connection_status_changed = pyqtSignal(str)
    telemetry_updated = pyqtSignal(float, float, float, float)  # roll, pitch, yaw, depth

    def __init__(self, connection_string='udp:127.0.0.1:14551'):
        super().__init__()
        self.connection_string = connection_string
        self.master = None
        self.running = True
        self.default_modes = {
            'STABILIZE': 0, 'ACRO': 1, 'ALT_HOLD': 2, 'AUTO': 3, 'GUIDED': 4,
            'LOITER': 5, 'RTL': 6, 'CIRCLE': 7, 'LAND': 9, 'MANUAL': 10
        }

    def run(self):
        try:
            logging.info(f"Connecting to vehicle on: {self.connection_string}")
            self.master = mavutil.mavlink_connection(self.connection_string, autoreconnect=True)
            self.master.wait_heartbeat()
            logging.info("Heartbeat received! Connection established.")
            self.connection_status_changed.emit(f"Connected to SYSID:{self.master.target_system}")

            while self.running:
                msg = self.master.recv_match(type=['ATTITUDE', 'VFR_HUD'], blocking=True, timeout=1)
                if not msg:
                    continue

                msg_type = msg.get_type()
                if msg_type == 'ATTITUDE':
                    roll = np.degrees(msg.roll)
                    pitch = np.degrees(msg.pitch)
                    yaw = np.degrees(msg.yaw)
                    self.telemetry_updated.emit(roll, pitch, yaw, getattr(self, 'last_depth', 0))
                elif msg_type == 'VFR_HUD':
                    self.last_depth = msg.alt
                    self.telemetry_updated.emit(getattr(self, 'last_roll', 0), getattr(self, 'last_pitch', 0), getattr(self, 'last_yaw', 0), self.last_depth)
                
                if msg_type == 'ATTITUDE':
                    self.last_roll, self.last_pitch, self.last_yaw = np.degrees(msg.roll), np.degrees(msg.pitch), np.degrees(msg.yaw)

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

    def arm_disarm(self, arm):
        if not self.master: return
        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
            1 if arm else 0, 0, 0, 0, 0, 0, 0)
        logging.info(f"Command {'ARM' if arm else 'DISARM'} sent.")

    def set_mode(self, mode_name):
        if not self.master: return
        modes = self.master.mode_mapping() or self.default_modes
        if mode_name.upper() not in modes:
            logging.warning(f"Mode '{mode_name}' not available.")
            return
        
        mode_id = modes[mode_name.upper()]
        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id)
        logging.info(f"Command to set mode to '{mode_name}' sent.")

    def set_rc_override(self, roll, pitch, throttle, yaw):
        if not self.master: return
        self.master.mav.rc_channels_override_send(
            self.master.target_system, self.master.target_component,
            int(roll), int(pitch), int(throttle), int(yaw), 0, 0, 0, 0)

class CameraWorker(QThread):
    frame_ready = pyqtSignal(QImage)

    def __init__(self, camera_index=0):
        super().__init__()
        self.running = True
        self.camera_index = camera_index
        self.model = None
        try:
            self.model = YOLO('yolov11.pt')
            logging.info("YOLOv11 model loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load YOLO model: {e}")

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            logging.error(f"Cannot open camera at index {self.camera_index}.")
            return

        while self.running:
            ret, frame = cap.read()
            if not ret:
                break

            if self.model:
                results = self.model(frame, verbose=False)
                for r in results:
                    for box in r.boxes:
                        if box.conf[0] > 0.5:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            cls_id = int(box.cls[0])
                            class_name = self.model.names[cls_id]
                            label = f"{class_name}: {box.conf[0]:.2f}"
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                            cv2.putText(frame, label, (x1, y1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.frame_ready.emit(qt_image.copy())

        cap.release()
        logging.info("Camera thread stopped.")

    def stop(self):
        self.running = False
        self.wait()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROV Control and Vision Interface")
        self.setGeometry(100, 100, 1200, 700)

        self.mavlink_worker = MAVLinkWorker()
        self.camera_worker = CameraWorker(camera_index=0)

        self.setup_ui()
        self.connect_signals()

        self.mavlink_worker.start()
        self.camera_worker.start()
        
    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # --- Left Panel (Video) ---
        video_group = QGroupBox("Camera Feed")
        video_layout = QVBoxLayout()
        self.video_label = QLabel("Connecting to camera...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setFixedSize(800, 600)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        video_layout.addWidget(self.video_label)
        video_group.setLayout(video_layout)

        # --- Right Panel (Controls & Telemetry) ---
        controls_layout = QVBoxLayout()

        # Connection
        conn_group = QGroupBox("Connection")
        conn_layout = QVBoxLayout()
        self.conn_status_label = QLabel("Status: Disconnected")
        conn_layout.addWidget(self.conn_status_label)
        conn_group.setLayout(conn_layout)

        # Telemetry
        telemetry_group = QGroupBox("Telemetry Data")
        telemetry_layout = QFormLayout()
        self.roll_label = QLabel("0.00 °")
        self.pitch_label = QLabel("0.00 °")
        self.yaw_label = QLabel("0.00 °")
        self.depth_label = QLabel("0.00 m")
        telemetry_layout.addRow("Roll:", self.roll_label)
        telemetry_layout.addRow("Pitch:", self.pitch_label)
        telemetry_layout.addRow("Yaw:", self.yaw_label)
        telemetry_layout.addRow("Depth/Altitude:", self.depth_label)
        telemetry_group.setLayout(telemetry_layout)
        
        # Controls
        flight_controls_group = QGroupBox("Flight Controls")
        flight_controls_layout = QVBoxLayout()
        
        # Arm/Disarm Buttons
        arm_layout = QHBoxLayout()
        self.arm_button = QPushButton("ARM")
        self.disarm_button = QPushButton("DISARM")
        arm_layout.addWidget(self.arm_button)
        arm_layout.addWidget(self.disarm_button)
        flight_controls_layout.addLayout(arm_layout)

        # Mode Buttons
        mode_layout = QHBoxLayout()
        self.manual_button = QPushButton("MANUAL")
        self.stabilize_button = QPushButton("STABILIZE")
        self.depth_hold_button = QPushButton("DEPTH HOLD")
        mode_layout.addWidget(self.manual_button)
        mode_layout.addWidget(self.stabilize_button)
        mode_layout.addWidget(self.depth_hold_button)
        flight_controls_layout.addLayout(mode_layout)
        flight_controls_group.setLayout(flight_controls_layout)

        # Sliders (Gain)
        rc_group = QGroupBox("Manual Control (Gain Sliders)")
        rc_layout = QGridLayout()
        self.pitch_slider = self.create_slider() # Forward/Back
        self.roll_slider = self.create_slider()  # Left/Right
        self.throttle_slider = self.create_slider() # Up/Down
        self.yaw_slider = self.create_slider()    # Rotate
        rc_layout.addWidget(QLabel("Forward"), 0, 0, Qt.AlignmentFlag.AlignCenter)
        rc_layout.addWidget(self.pitch_slider, 1, 0)
        rc_layout.addWidget(QLabel("Backward"), 2, 0, Qt.AlignmentFlag.AlignCenter)
        
        rc_layout.addWidget(QLabel("Up"), 0, 1, Qt.AlignmentFlag.AlignCenter)
        rc_layout.addWidget(self.throttle_slider, 1, 1)
        rc_layout.addWidget(QLabel("Down"), 2, 1, Qt.AlignmentFlag.AlignCenter)

        rc_layout.addWidget(QLabel("Left"), 0, 2, Qt.AlignmentFlag.AlignCenter)
        rc_layout.addWidget(self.roll_slider, 1, 2)
        rc_layout.addWidget(QLabel("Right"), 2, 2, Qt.AlignmentFlag.AlignCenter)

        rc_layout.addWidget(QLabel("Turn L"), 0, 3, Qt.AlignmentFlag.AlignCenter)
        rc_layout.addWidget(self.yaw_slider, 1, 3)
        rc_layout.addWidget(QLabel("Turn R"), 2, 3, Qt.AlignmentFlag.AlignCenter)
        
        self.center_rc_button = QPushButton("Center All Controls")
        rc_layout.addWidget(self.center_rc_button, 3, 0, 1, 4)

        rc_group.setLayout(rc_layout)
        
        # Camera Controls
        camera_group = QGroupBox("Camera Control")
        camera_layout = QHBoxLayout()
        self.camera_switch_combo = QComboBox()
        self.camera_switch_combo.addItems(["Camera 0", "Camera 1", "Camera 2"]) # Add more if needed
        camera_layout.addWidget(QLabel("Select Camera:"))
        camera_layout.addWidget(self.camera_switch_combo)
        camera_group.setLayout(camera_layout)

        # Add all widgets to the right panel
        controls_layout.addWidget(conn_group)
        controls_layout.addWidget(telemetry_group)
        controls_layout.addWidget(flight_controls_group)
        controls_layout.addWidget(rc_group)
        controls_layout.addWidget(camera_group)
        controls_layout.addStretch()

        # Add panels to main layout
        main_layout.addWidget(video_group)
        main_layout.addLayout(controls_layout)

    def create_slider(self):
        slider = QSlider(Qt.Orientation.Vertical)
        slider.setMinimum(1100)
        slider.setMaximum(1900)
        slider.setValue(1500)
        slider.setTickPosition(QSlider.TickPosition.TicksLeft)
        slider.setTickInterval(100)
        return slider

    def connect_signals(self):
        # Worker signals
        self.mavlink_worker.connection_status_changed.connect(self.update_connection_status)
        self.mavlink_worker.telemetry_updated.connect(self.update_telemetry)
        self.camera_worker.frame_ready.connect(self.update_video_frame)

        # Button signals
        self.arm_button.clicked.connect(lambda: self.mavlink_worker.arm_disarm(True))
        self.disarm_button.clicked.connect(lambda: self.mavlink_worker.arm_disarm(False))
        self.manual_button.clicked.connect(lambda: self.mavlink_worker.set_mode('MANUAL'))
        self.stabilize_button.clicked.connect(lambda: self.mavlink_worker.set_mode('STABILIZE'))
        self.depth_hold_button.clicked.connect(lambda: self.mavlink_worker.set_mode('ALT_HOLD'))
        self.center_rc_button.clicked.connect(self.center_rc_controls)
        self.camera_switch_combo.currentIndexChanged.connect(self.switch_camera)
        
        # Slider signals
        self.pitch_slider.valueChanged.connect(self.update_rc_overrides)
        self.roll_slider.valueChanged.connect(self.update_rc_overrides)
        self.throttle_slider.valueChanged.connect(self.update_rc_overrides)
        self.yaw_slider.valueChanged.connect(self.update_rc_overrides)

    def update_connection_status(self, status):
        self.conn_status_label.setText(f"Status: {status}")

    def update_telemetry(self, roll, pitch, yaw, depth):
        self.roll_label.setText(f"{roll:.2f} °")
        self.pitch_label.setText(f"{pitch:.2f} °")
        self.yaw_label.setText(f"{yaw:.2f} °")
        self.depth_label.setText(f"{depth:.2f} m")

    def update_video_frame(self, image):
        self.video_label.setPixmap(QPixmap.fromImage(image).scaled(
            self.video_label.width(), self.video_label.height(), Qt.AspectRatioMode.KeepAspectRatio
        ))

    def update_rc_overrides(self):
        pitch = self.pitch_slider.value()
        roll = self.roll_slider.value()
        throttle = self.throttle_slider.value()
        yaw = self.yaw_slider.value()
        
        self.mavlink_worker.set_rc_override(roll, pitch, throttle, yaw)

    def center_rc_controls(self):
        self.pitch_slider.setValue(1500)
        self.roll_slider.setValue(1500)
        self.throttle_slider.setValue(1500)
        self.yaw_slider.setValue(1500)
        self.update_rc_overrides()

    def switch_camera(self, index):
        logging.info(f"Switching to camera index {index}")
        self.camera_worker.stop()
        self.camera_worker = CameraWorker(camera_index=index)
        self.camera_worker.frame_ready.connect(self.update_video_frame)
        self.camera_worker.start()

    def closeEvent(self, event):
        logging.info("Closing application...")
        self.camera_worker.stop()
        self.mavlink_worker.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())