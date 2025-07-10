from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import backend.imageProcessing_AI_interface as imageProcessing
import backend.connection_interface as connection_interface
import threading
import logging
import time
import sys
import cv2

class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        
        self.logger = logging.getLogger("CALROV YAZ GUI")
        
        self.connectionObj = connection_interface.Connection(self.logger)
        self.connection = self.connectionObj.createConnection()
        self.controllerObject = connection_interface.Controls(self.connection, self.logger)        
        self.ai = imageProcessing.AI("", "")
        
        self.camera_1_n = 0
        self.camera_2_n = 1
        
        self.initUI()
        
        cam1 = threading.Thread(target = self.readImage)
        cam2 = threading.Thread(target = self.readImage)
        telemetry = threading.Thread(target = self.telemetryDatas)
        
        cam1.start()
        cam2.start()
        telemetry.start()
        
    def initUI(self):
        self.resize(1600, 1000)
        
        self.arm_disarm_label = QLabel(self)
        self.arm_button = QPushButton(self)
        self.disarm_button = QPushButton(self)
        self.mode_label = QLabel(self)
        self.manual_button = QPushButton(self)
        self.stabilize_button = QPushButton(self)
        self.depth_hold_button = QPushButton(self)
        self.camera_label = QLabel(self)
        self.front_camera_button = QPushButton(self)
        self.bottom_camera_button = QPushButton(self)
        self.telemetry_label = QLabel(self)
        self.roll_label = QLabel(self)
        self.pitch_label = QLabel(self)
        self.yaw_label = QLabel(self)
        self.depth_label = QLabel(self)
        self.slider_label = QLabel(self)
        self.slider = QSlider(self)
        self.camera_1 = QLabel(self)
        self.camera_2 = QLabel(self)
        self.quit_button = QPushButton(self)
        
        self.arm_disarm_label.setText("ARM-DISARM self.buttons")
        self.arm_button.setText("ARM")
        self.disarm_button.setText("DISARM")
        self.mode_label.setText("SET MODE self.buttons")
        self.manual_button.setText("MANUAL")
        self.stabilize_button.setText("STABILIZE")
        self.depth_hold_button.setText("DEPTH HOLD")
        self.camera_label.setText("CHANGE CAMERA")
        self.front_camera_button.setText("FRONT")
        self.bottom_camera_button.setText("BOTTOM")
        self.telemetry_label.setText("TELEMETRY DATAS")
        self.roll_label.setText("ROLL : ")
        self.pitch_label.setText("PITCH : ")
        self.yaw_label.setText("YAW : ")
        self.depth_label.setText("DEPTH : ")
        self.slider_label.setText("GAIN SLIDER")
        self.slider.setGeometry(QRect(950, 55, 200, 16))
        self.camera_1.setGeometry(10, 100, 1550, 875)
        self.camera_2.setGeometry(1130, 645, 400, 300)
        self.quit_button.setText("QUIT")
        
        self.arm_disarm_label.move(55, 10)
        self.arm_button.move(25, 55)
        self.disarm_button.move(110, 55)
        self.mode_label.move(300, 10)
        self.manual_button.move(225, 55)
        self.stabilize_button.move(310, 55)
        self.depth_hold_button.move(395, 55)
        self.camera_label.move(650, 10)
        self.front_camera_button.move(610, 55)
        self.bottom_camera_button.move(695, 55)
        self.telemetry_label.move(1425, 10)
        self.roll_label.move(1375, 35)
        self.pitch_label.move(1375, 65)
        self.yaw_label.move(1525, 35)
        self.depth_label.move(1525, 65)
        self.slider_label.move(1025, 10)
        self.slider.setOrientation(Qt.Horizontal)
        self.quit_button.setGeometry(10, 975, 1550, 25)
        self.quit_button.move(10, 975)
        
        self.arm_button.clicked.connect(self.controllerObject.arm)
        self.disarm_button.clicked.connect(self.controllerObject.disarm)
        self.manual_button.clicked.connect(self.controllerObject.manual)
        self.stabilize_button.clicked.connect(self.controllerObject.stabilize)
        self.depth_hold_button.clicked.connect(self.controllerObject.depth_hold)
        self.front_camera_button.clicked.connect(self.front)
        self.bottom_camera_button.clicked.connect(self.bottom)
        self.quit_button.clicked.connect(self.quit)
        self.slider.valueChanged.connect(self.controllerObject.setGain)
    
    def telemetryDatas(self):
        while True:
            self.attitudeMsg = self.connection.recv_match(type = "ATTITUDE", blocking = True).to_dict()
            time.sleep(0.1)
            self.gpiMsg = self.connection.recv_match(type = "GLOBAL_POSITION_INT", blocing = True).to_dict()
            time.sleep(0.1)
            
            roll, pitch, yaw, depth = self.attitudeMsg["roll"], self.attitudeMsg["pitch"], self.attitudeMsg["yaw"], self.gpiMsg["relative_alt"]
            
            self.roll_label.setText(f"ROLL : {roll}")
            self.pitch_label.setText(f"PITCH : {pitch}")
            self.yaw_label.setText(f"YAW : {yaw}")
            self.depth_label.setText(f"DEPTH : {depth}")
    
    def front(self):
        if self.camera_1_n == 0 and self.camera_2_n == 1:
            pass
        
        else:
            self.camera_1_n = 0
            self.camera_2_n = 1
    
    def bottom(self):
        if self.camera_1_n == 0 and self.camera_2_n == 1:
            self.camera_1_n = 1
            self.camera_2_n = 0
            
        else:
            pass
    
    def readImage(self):
        video1 = cv2.VideoCapture(0)
        video2 = cv2.VideoCapture(1)
        
        while True:
            ret1, frame1 = video1.read()
            ret2, frame2 = video2.read()
            
            if ret1 and ret2:
                if self.camera_1_n == 0 and self.camera_2_n == 1:
                    self.displayImage(frame1, 0)
                    self.displayImage(frame2, 1)
                
                else:
                    self.displayImage(frame1, 1)
                    self.displayImage(frame2, 0)
    
    def displayImage(self, frame, num):
        frame = cv2.resize(frame, (640, 480))
                
        outImage = QImage(frame, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format_RGB888)
        outImage = outImage.rgbSwapped()
        
        if num == 0:
            self.camera_1.setPixmap(QPixmap.fromImage(outImage))
            self.camera_1.setScaledContents(True)
    
        else:
            self.camera_2.setPixmap(QPixmap.fromImage(outImage))
            self.camera_2.setScaledContents(True)
    
    def quit(self):
        self.ai.release1()
        self.ai.release2()
        self.destroy(True)
        sys.exit(0)
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())