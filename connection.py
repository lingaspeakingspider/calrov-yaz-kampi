from pymavlink import mavutil
from pynput import keyboard
import threading
import logging
import time
import os

class Controls():
    def __init__(self, connection, logger):
        self.connection = connection
        self.logger = logger

    def show_coordinates(self):
        locationData = self.connection.recv_match(type = "LOCAL_POSITION_NED", blocking = True).to_dict()
        time.sleep(0.1)
        attitudeData = self.connection.recv_match(type = "ATTITUDE", blocking = True).to_dict()
        time.sleep(0.1)
        
        x, y, z, yaw = locationData["x"], locationData["y"], locationData["z"], attitudeData["yaw"]
        
        self.logger.critical(f"x : {x}, y : {y}, z : {z}, yaw : {yaw}")
    
    def go_forward(self):
        self.connection.mav.manual_control_send(self.connection.target_system, 500, 0, 500, 0, 0)
        self.show_coordinates()
        self.logger.critical("A")

    def go_backward(self):
        self.connection.mav.manual_control_send(self.connection.target_system, -500, 0, 500, 0, 0)
        self.show_coordinates()
        self.logger.critical("B")
        
    def go_right(self):
        self.connection.mav.manual_control_send(self.connection.target_system, 0, 500, 500, 0, 0)
        self.show_coordinates()
        self.logger.critical("C")
        
    def go_left(self):
        self.connection.mav.manual_control_send(self.connection.target_system, 0, -500, 500, 0, 0)
        self.show_coordinates()
        self.logger.critical("D")
    
    def rise(self):
        self.connection.mav.manual_control_send(self.connection.target_system, 0, 0, 0, 0, 0)
        self.show_coordinates()
        self.logger.critical("E")
        
    def dive(self):
        self.connection.mav.manual_control_send(self.connection.target_system, 0, 0, 1000, 0, 0)
        self.show_coordinates()
        self.logger.critical("F")
    
    def right_yaw(self):
        self.connection.mav.command_long_send(self.connection.target_system, self.connection.target_component, mavutil.mavlink.MAV_CMD_CONDITION_YAW, 0, 45, 0, 0, 0, 0, 0, 0)
        self.show_coordinates()
        self.logger.critical("G")
    
    def left_yaw(self):
        self.connection.mav.command_long_send(self.connection.target_system, self.connection.target_component, mavutil.mavlink.MAV_CMD_CONDITION_YAW, 0, 45, 0, -1, 0, 0, 0, 0)
        self.show_coordinates()
        self.logger.critical("H")
    
    def arm(self):
        self.connection.arducopter_arm()
        """
        self.logger.critical("WAIT FOR ARM")
        self.connection.motors_armed_wait()
        """
        self.logger.critical("ARMED")

    def disarm(self):
        self.connection.arducopter_disarm()
        """
        self.logger.critical("WAIT FOR DISARM")
        self.connection.motors_disarmed_wait()
        """
        self.logger.critical("DISARMED")
    
    def set_mode(self, mode):
        try:
            if mode != "DEPTH_HOLD":
                mode_id = self.connection.mode_mapping()[mode]
                
                self.connection.set_mode(mode_id)
                
                self.logger.critical(f"MODE SET : {mode}")

            else:
                self.logger.critical(f"Mode : {mode}")
                target_depth = 2000
                
                while True:
                    current_depth = self.connection.recv_match(type = "GLOBAL_POSITION_INT", blocking = True).to_dict()
                    time.sleep(0.1)
                    
                    error = int(target_depth) - int(current_depth["relative_alt"])

                    self.z_p_value = 1.0 * error
                    self.z_p_value = max(self.z_p_value, -200)
                    self.z_p_value = min(self.z_p_value, 200)

                    self.z_i_value += 0.5 * error
                    self.z_i_value = max(self.z_i_value, -85.0)
                    self.z_i_value = min(self.z_i_value, 85)

                    self.z_d_value = (error - self.z_last_error) * 0.6
                    self.z_d_value = max(self.z_d_value, -58)
                    self.z_d_value = min(self.z_d_value, 58)

                    self.z_value = self.z_p_value + self.z_i_value + self.z_d_value + 410
                    self.z_value = max(self.z_value, 200)
                    self.z_value = min(self.z_value, 700)

                    self.z_last_error = error
    
        except Exception as e:
            self.logger.critical(e)
            return 1
    
    def servo(self, servo_n, microseconds):
        self.connection.mav.command_long_send(self.connection.target_system, self.connection.target_component, mavutil.mavlink.MAV_CMD_DO_SET_SERVO, 0, servo_n + 8, microseconds, 0,0,0,0,0)
        self.show_coordinates()
        self.logger.critical("I")

class Connection():
    def __init__(self, connection, logger, controller : Controls):
        self.controller = controller
        
        self.connection = connection
        self.logger = logger
        
        self.createKeyboardListener()
        
    def writeTxtFile(self, data):
        with open("datas.txt", "a") as self.file:
            self.file.write(str(data) + "\n")
    
    def createKeyboardListener(self):
        self.listener = keyboard.Listener(on_press = self.onPress)
        self.listener.start()
    
    def closeKeyboardListener(self):
        self.listener.stop()
    
    def resumeKeyboardListener(self):
        self.createKeyboardListener()
    
    def onPress(self, key):
        try:
            if key == keyboard.Key.esc:
                self.listener.stop()
                self.logger.critical("Connection Closed")
                self.close()

            elif key == keyboard.Key.up:
                self.logger.critical("RISE")
                self.controller.rise()
                
            elif key == keyboard.Key.down:
                self.logger.critical("DIVE")
                self.controller.dive()
                
            elif key == keyboard.Key.right:
                self.logger.critical("RIGHT-YAW")
                self.controller.right_yaw()
                
            elif key == keyboard.Key.left:
                self.logger.critical("LEFT-YAW")
                self.controller.left_yaw()

            elif key.char == 'q':
                self.logger.critical("ARM")
                self.controller.arm()
            
            elif key.char == 'e':
                self.logger.critical("DISARM")
                self.controller.disarm()
                
            elif key.char == '1':
                self.logger.critical("MANUEL")
                check = self.controller.set_mode('MANUAL')
                
                if check == 1: self.close()
                
            elif key.char == '2':
                self.logger.critical("DEPTH HOLD")
                check = self.controller.set_mode('DEPTH_HOLD')
                
                if check == 1: self.close()
            
            elif key.char == '3':
                self.logger.critical("STABILIZE")
                check = self.controller.set_mode("STABILIZE")
                
                if check == 1: self.close()
            
            elif key.char == 'w':
                self.logger.critical("FORWARD")
                self.controller.go_forward()
                
            elif key.char == 'a':
                self.logger.critical("LEFT")
                self.controller.go_left()
                
            elif key.char == 's':
                self.logger.critical("BACKWARD")
                self.controller.go_backward()
                
            elif key.char == 'd':
                self.logger.critical("RIGHT")
                self.controller.go_right()
            
            elif key.char == 'z':
                self.logger.critical("SERVO")
                
                for i in range(1100, 1900, 50):
                    self.controller.servo(1, i)
                    time.sleep(0.125)

            else:
                self.logger.critical("INVALID")
        
        except Exception as e:
            self.logger.critical(e)

    def close(self):
        try:
            self.file.close()
            self.connection.close()
            os.remove("datas.txt")
        
        except Exception as e:
            self.logger.critical(e)
        
        finally:
            exit()

def main():
    connection = mavutil.mavlink_connection('udp:127.0.0.1:14550', source_system=1)
    logger = logging.Logger("CALROV Yaz")
    
    controller = Controls(connection, logger)
    connectionClassObject = Connection(connection, logger, controller)

    connection.wait_heartbeat()
    logger.critical("Connection created succesfully!")

    while True:
        connectionData = connection.recv_match(type = "HEARTBEAT", blocking = True).to_dict()

        dataThread = threading.Thread(target = connectionClassObject.writeTxtFile, args = (connectionData, ))
        
        dataThread.start()
        
        time.sleep(0.01)
    
if __name__ == "__main__":
    main()