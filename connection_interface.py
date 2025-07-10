from pymavlink import mavutil
import time

class Controls():
    def __init__(self, connection, logger):
        self.connection = connection
        self.logger = logger
        self.speed = 0
    
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
    
    def manual(self):
        mode_id = self.connection.mode_mapping()["MANUAL"]
                
        self.connection.set_mode(mode_id)
                
        self.logger.critical(f"MODE SET : MANUAL")
    
    def stabilize(self):
        mode_id = self.connection.mode_mapping()["STABILIZE"]
                
        self.connection.set_mode(mode_id)
                
        self.logger.critical(f"MODE SET : STABILIZE")
    
    def depth_hold(self):
        self.logger.critical(f"Mode : DEPTH HOLD")
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

    def setGain(self, value):
        self.logger.critical(value)
        self.speed = value / 2
        self.connection.mav.command_long_send(self.connection.target_system, self.connection.target_component, mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, 0, 0, self.speed, 0, 0, 0, 0, 0)
    
class Connection():
    def __init__(self, logger):
        self.logger = logger
    
    def createConnection(self):
        self.connection = ""#mavutil.mavlink_connection('udp:127.0.0.1:14550', source_system=1)
        #self.connection.wait_heartbeat()
        self.logger.critical("Connection Created Succesfully")
        
        return self.connection
                
    def close(self, conn):
        conn.close()