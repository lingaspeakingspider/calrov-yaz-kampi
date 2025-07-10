import sys
import cv2
import numpy as np
import logging
from ultralytics import YOLO
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QSlider, QGroupBox, QFormLayout, QComboBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage, QPixmap
from mavlink_controller import MAVLinkWorker


class LevelColorFormatter(logging.Formatter):
    COLORS = {'DEBUG': '\033[36m', 'INFO': '\033[34m',
              'WARNING': '\033[33m', 'ERROR': '\033[31m', 'CRITICAL': '\033[41m'}
    RESET = '\033[0m'

    def format(self, record):
        original_levelname, color = record.levelname, self.COLORS.get(
            record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        formatted = super().format(record)
        record.levelname = original_levelname
        return formatted


logger, handler, formatter = logging.getLogger(), logging.StreamHandler(
), LevelColorFormatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class CameraWorker(QThread):
    frame_ready = pyqtSignal(QImage)

    def __init__(self, camera_index=0):
        super().__init__()
        self.running = True
        self.camera_index = camera_index
        self.model = None
        self.cap = None

        try:
            self.model = YOLO('yolov11.pt')
            logging.info("YOLOv11 model loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load YOLO model: {e}")

    def run(self):
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            logging.error(f"Cannot open camera at index {self.camera_index}.")
            return

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break

            if self.model:
                results = self.model(frame, verbose=False)
                frame = results[0].plot()

            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h,
                              bytes_per_line, QImage.Format.Format_RGB888)
            self.frame_ready.emit(qt_image.copy())

        if self.cap:
            self.cap.release()
        logging.info("Camera thread's run method finished.")

    def stop(self):
        logging.info("Stopping camera worker...")
        self.running = False
        if self.cap:
            self.cap.release()
        self.wait()
        logging.info("Camera worker stopped successfully.")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROV Control Interface")
        self.setGeometry(100, 100, 1400, 800)
        self.mavlink_worker = MAVLinkWorker(simulation=True)
        self.camera_worker = CameraWorker(camera_index=0)
        self.setup_ui()
        self.connect_signals()
        self.mavlink_worker.start()
        self.camera_worker.start()

    def closeEvent(self, event):
        logging.info("Closing application...")
        self.camera_worker.stop()
        self.mavlink_worker.stop()
        event.accept()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        video_group = QGroupBox("Camera Feed")
        video_layout = QVBoxLayout()
        self.video_label = QLabel("Connecting to camera...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setFixedSize(800, 600)
        self.video_label.setStyleSheet(
            "background-color: black; color: white; border: 1px solid gray;")
        video_layout.addWidget(self.video_label)
        video_group.setLayout(video_layout)
        controls_layout = QVBoxLayout()
        right_panel_widget = QWidget()
        right_panel_widget.setLayout(controls_layout)
        right_panel_widget.setFixedWidth(450)
        conn_group = QGroupBox("Connection")
        conn_layout = QVBoxLayout()
        self.conn_status_label = QLabel("Status: Disconnected")
        conn_layout.addWidget(self.conn_status_label)
        conn_group.setLayout(conn_layout)
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
        flight_controls_group = QGroupBox("Vehicle Controls")
        flight_controls_layout = QVBoxLayout()
        arm_layout = QHBoxLayout()
        self.arm_button = QPushButton("ARM")
        self.disarm_button = QPushButton("DISARM")
        arm_layout.addWidget(self.arm_button)
        arm_layout.addWidget(self.disarm_button)
        flight_controls_layout.addLayout(arm_layout)
        mode_layout = QGridLayout()
        self.manual_button = QPushButton("MANUAL")
        self.stabilize_button = QPushButton("STABILIZE")
        self.depth_hold_button = QPushButton("ALT_HOLD")
        mode_layout.addWidget(self.manual_button, 0, 0)
        mode_layout.addWidget(self.stabilize_button, 0, 1)
        mode_layout.addWidget(self.depth_hold_button, 1, 0, 1, 2)
        flight_controls_layout.addLayout(mode_layout)
        flight_controls_group.setLayout(flight_controls_layout)
        rc_group = QGroupBox("Manual Control")
        rc_layout = QGridLayout()
        self.pitch_slider = self.create_slider()
        self.roll_slider = self.create_slider()
        self.throttle_slider = self.create_slider()
        self.yaw_slider = self.create_slider()
        rc_layout.addWidget(QLabel("Forward"), 0, 0,
                            Qt.AlignmentFlag.AlignCenter)
        rc_layout.addWidget(self.pitch_slider, 1, 0)
        rc_layout.addWidget(QLabel("Backward"), 2, 0,
                            Qt.AlignmentFlag.AlignCenter)
        rc_layout.addWidget(QLabel("Strafe L"), 0, 1,
                            Qt.AlignmentFlag.AlignCenter)
        rc_layout.addWidget(self.roll_slider, 1, 1)
        rc_layout.addWidget(QLabel("Strafe R"), 2, 1,
                            Qt.AlignmentFlag.AlignCenter)
        rc_layout.addWidget(QLabel("Up"), 0, 2, Qt.AlignmentFlag.AlignCenter)
        rc_layout.addWidget(self.throttle_slider, 1, 2)
        rc_layout.addWidget(QLabel("Down"), 2, 2, Qt.AlignmentFlag.AlignCenter)
        rc_layout.addWidget(QLabel("Turn L"), 0, 3,
                            Qt.AlignmentFlag.AlignCenter)
        rc_layout.addWidget(self.yaw_slider, 1, 3)
        rc_layout.addWidget(QLabel("Turn R"), 2, 3,
                            Qt.AlignmentFlag.AlignCenter)
        self.center_rc_button = QPushButton("Center All Controls")
        rc_layout.addWidget(self.center_rc_button, 3, 0, 1, 4)
        rc_group.setLayout(rc_layout)
        camera_group = QGroupBox("Camera Control")
        camera_layout = QHBoxLayout()
        self.camera_switch_combo = QComboBox()
        self.camera_switch_combo.addItems([f"Camera {i}" for i in range(3)])
        camera_layout.addWidget(QLabel("Select Camera:"))
        camera_layout.addWidget(self.camera_switch_combo)
        camera_group.setLayout(camera_layout)
        controls_layout.addWidget(conn_group)
        controls_layout.addWidget(telemetry_group)
        controls_layout.addWidget(flight_controls_group)
        controls_layout.addWidget(rc_group)
        controls_layout.addWidget(camera_group)
        controls_layout.addStretch()
        main_layout.addWidget(video_group)
        main_layout.addWidget(right_panel_widget)

    def create_slider(self):
        slider = QSlider(Qt.Orientation.Vertical)
        slider.setMinimum(1100)
        slider.setMaximum(1900)
        slider.setValue(1500)
        slider.setTickPosition(QSlider.TickPosition.TicksBothSides)
        slider.setTickInterval(100)
        slider.setMinimumHeight(150)
        return slider

    def connect_signals(self):
        self.mavlink_worker.connection_status_changed.connect(
            self.update_connection_status)
        self.mavlink_worker.telemetry_updated.connect(self.update_telemetry)
        self.camera_worker.frame_ready.connect(self.update_video_frame)
        self.arm_button.clicked.connect(
            lambda: self.mavlink_worker.arm_disarm(True))
        self.disarm_button.clicked.connect(
            lambda: self.mavlink_worker.arm_disarm(False))
        self.manual_button.clicked.connect(
            lambda: self.mavlink_worker.set_mode('MANUAL'))
        self.stabilize_button.clicked.connect(
            lambda: self.mavlink_worker.set_mode('STABILIZE'))
        self.depth_hold_button.clicked.connect(
            lambda: self.mavlink_worker.set_mode('ALT_HOLD'))
        self.center_rc_button.clicked.connect(self.center_rc_controls)
        self.camera_switch_combo.currentIndexChanged.connect(
            self.switch_camera)
        self.pitch_slider.valueChanged.connect(self.update_rc_overrides)
        self.roll_slider.valueChanged.connect(self.update_rc_overrides)
        self.throttle_slider.valueChanged.connect(self.update_rc_overrides)
        self.yaw_slider.valueChanged.connect(self.update_rc_overrides)

    def update_connection_status(self, status):
        self.conn_status_label.setText(f"Status: {status}")
        self.conn_status_label.setStyleSheet(
            "color: green;" if "Connected" in status else "color: red;")

    def update_telemetry(self, roll, pitch, yaw, depth):
        self.roll_label.setText(f"{roll:.2f} °")
        self.pitch_label.setText(f"{pitch:.2f} °")
        self.yaw_label.setText(f"{yaw:.2f} °")
        self.depth_label.setText(f"{depth:.2f} m")

    def update_video_frame(self, image):
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(pixmap.scaled(self.video_label.width(
        ), self.video_label.height(), Qt.AspectRatioMode.KeepAspectRatio))

    def update_rc_overrides(self):
        pitch = self.pitch_slider.value()
        roll = self.roll_slider.value()
        throttle = self.throttle_slider.value()
        yaw = self.yaw_slider.value()
        logging.debug(
            f"RC Override DEBUG -> Pitch:{pitch}, Roll:{roll}, Throttle:{throttle}, Yaw:{yaw}")
        self.mavlink_worker.set_rc_override(
            roll=roll, pitch=pitch, throttle=throttle, yaw=yaw)

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
