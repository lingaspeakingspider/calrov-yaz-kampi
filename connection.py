import time
import threading
import logging
import keyboard
from pymavlink import mavutil
from typing import Optional, Any
import os

# --- AYARLAR ---
CONNECTION_STRING = 'udp:127.0.0.1:14551'
HEARTBEAT_LOG_FILE = 'heartbeat_log.txt'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
default_modes = {
    'STABILIZE': 0,
    'ACRO': 1,
    'ALT_HOLD': 2,
    'AUTO': 3,
    'GUIDED': 4,
    'LOITER': 5,
    'RTL': 6,
    'CIRCLE': 7,
    'LAND': 9,
    'MANUAL': 10,
    'POSHOLD': 16,
    'BRAKE': 11
}

#logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

master: Optional[Any] = None
keyboard_mode_active = True

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
        record.levelname = original_levelname  # Orijinal haline döndür
        return formatted

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = LevelColorFormatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

def heartbeat_listener():
    logging.info("Heartbeat dinleyici başlatıldı.")
    while True:
        if not keyboard_mode_active or not master:
            break
            
        #msg = master.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
        msg = master.wait_heartbeat()
        if not msg:
            continue

        msg_dict = msg.to_dict()
        
        try:
            with open(HEARTBEAT_LOG_FILE, 'a') as f:
                f.write(str(msg_dict) + '\n')
        except Exception as e:
            logging.error(f"Heartbeat dosyasına yazılırken hata oluştu: {e}")
        
        time.sleep(0.1)
    logging.info("Heartbeat dinleyici durduruldu.")


def set_rc_channel_override(roll=1500, pitch=1500, throttle=1500, yaw=1500):
    if not master:
        return
    
    master.mav.rc_channels_override_send(
        master.target_system,
        master.target_component,
        int(roll),
        int(pitch),
        int(throttle),
        int(yaw),
        0, 0, 0, 0)
    logging.info(f"Hareket komutu -> İleri/Geri (Pitch): {pitch}, Sağ/Sol (Roll): {roll}, Yükselme (Throttle): {throttle}, Yaw: {yaw}")

def arm_disarm(arm: bool):
    if not master:
        return
    if arm:
        master.mav.command_long_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1, 0, 0, 0, 0, 0, 0)
        logging.info("ARM komutu gönderildi.")
    else:
        master.mav.command_long_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            0, 0, 0, 0, 0, 0, 0)
        logging.info("DISARM komutu gönderildi.")

def set_mode(mode_name):
    if not master:
        return
    
    modes = master.mode_mapping()
    if not modes:
        logging.warning("Mod haritası alınamadı, varsayılan modlar kullanılacak.")
        modes = default_modes

    if mode_name not in modes:
        logging.warning(f"Bilinmeyen mod: {mode_name}. Kullanılabilir modlar: {list(modes.keys())}")
        return
    
    mode_id = modes[mode_name]
    master.mav.set_mode_send(
        master.target_system,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        mode_id)
    logging.info(f"Mod değiştirme komutu gönderildi: {mode_name}")


def set_servo(servo_id, pwm_value):
    if not master:
        return
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
        0,
        servo_id,
        pwm_value,
        0, 0, 0, 0, 0)
    logging.info(f"Servo {servo_id} için PWM değeri {pwm_value} olarak ayarlandı.")


def keyboard_controller():
    global keyboard_mode_active
    logging.info("Klavye kontrol modu başlatıldı. Komutlar için tuşları kullanın.")
    logging.info("W/A/S/D: İleri/Sol/Geri/Sağ | ↑/↓: Yükselme/Alçalma | ←/→: Yaw | Q/E: Arm/Disarm | 1/2/3: Modlar | Z: Servo | Esc: Çıkış")

    neutral = 1500
    step = 100
    
    pitch = neutral # W/S (İleri/Geri)
    roll = neutral  # A/D (Sağ/Sol)
    throttle = 1500 # Yukarı/Aşağı ok (Yükselme/Alçalma)
    yaw = neutral   # Sol/Sağ ok

    while keyboard_mode_active:
        try:
            event = keyboard.read_event()
            if event.event_type == keyboard.KEY_DOWN:
                key = event.name
                
                # Hareket değerlerini sıfırlama tuşu
                if key == 'r':
                    pitch, roll, throttle, yaw = neutral, neutral, neutral, neutral
                    logging.info("Tüm hareket komutları nötr pozisyona getirildi.")
                
                # Hareket Komutları
                elif key == 'w': pitch -= step
                elif key == 's': pitch += step
                elif key == 'a': roll -= step
                elif key == 'd': roll += step
                elif key == 'up': throttle += step
                elif key == 'down': throttle -= step
                elif key == 'left': yaw -= step
                elif key == 'right': yaw += step
                
                # Arm/Disarm
                elif key == 'q': arm_disarm(True)
                elif key == 'e': arm_disarm(False)

                # Mod Değiştirme
                elif key == '1': set_mode('MANUAL')
                elif key == '2': set_mode('ALT_HOLD')
                elif key == '3': set_mode('STABILIZE')

                # Servo Komutu
                elif key == 'z':
                    # Örnek: 4 numaralı servoyu 1200 PWM değerine ayarla
                    set_servo(4, 1200) 
                
                # Çıkış
                elif key == 'esc':
                    logging.info("Klavye kontrol modundan çıkılıyor...")
                    keyboard_mode_active = False
                    break

                # Değişen hareket değerlerini sınırlar içinde tut (clamp) ve gönder
                pitch = max(1100, min(1900, pitch))
                roll = max(1100, min(1900, roll))
                throttle = max(1100, min(1900, throttle))
                yaw = max(1100, min(1900, yaw))
                
                if key in ['w', 'a', 's', 'd', 'up', 'down', 'left', 'right', 'r']:
                    set_rc_channel_override(roll, pitch, throttle, yaw)

        except Exception as e:
            logging.error(f"Klavye kontrolcüsünde hata: {e}")
            break
            
    logging.info("Klavye kontrolcüsü durduruldu.")

def main():
    current_directory = os.getcwd()
    file_path = os.path.abspath(HEARTBEAT_LOG_FILE)
    logging.info(f"Mevcut çalışma dizini: {current_directory}")
    logging.info(f"Log dosyası şu mutlak yola kaydedilecek: {file_path}")

    global master
    
    try:
        master = mavutil.mavlink_connection(CONNECTION_STRING, autoreconnect=True)
        logging.info(f"{CONNECTION_STRING} adresine bağlanılıyor...")

        master.wait_heartbeat()
        #master.recv_match(type='HEARTBEAT')
        logging.info("Heartbeat alındı! Araçla bağlantı kuruldu.")
        logging.info(f"Sistem ID: {master.target_system}, Komponent ID: {master.target_component}")  # type: ignore

        heartbeat_thread = threading.Thread(target=heartbeat_listener, daemon=True)
        keyboard_thread = threading.Thread(target=keyboard_controller)

        heartbeat_thread.start()
        keyboard_thread.start()

        keyboard_thread.join()

    except KeyboardInterrupt:
        logging.warning("Program kullanıcı tarafından sonlandırıldı (CTRL+C).")
    except Exception as e:
        logging.critical(f"Ana programda kritik bir hata oluştu: {e}")
    finally:
        keyboard_mode_active = False
        if master:
            set_rc_channel_override()
            arm_disarm(False)
            logging.info("Güvenlik için araç disarm edildi ve kanallar nötr yapıldı.")
            master.close()
        logging.info("Program sonlandırıldı.")

if __name__ == "__main__":
    main()