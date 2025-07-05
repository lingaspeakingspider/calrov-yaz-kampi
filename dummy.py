from pymavlink import mavutil
import time
import logging
import keyboard

master = mavutil.mavlink_connection('udpout:127.0.0.1:14550')

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

logging.info("Heartbeat gönderici başlatıldı. Çıkmak için ESC tuşuna basın.")

try:
    while True:
        if keyboard.is_pressed('esc'):
            logging.info("ESC tuşuna basıldı. Program sonlandırılıyor.")
            break

        master.mav.heartbeat_send( # type: ignore
            mavutil.mavlink.MAV_TYPE_GENERIC,
            mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
            0, 0, 0
        )
        logging.info("Heartbeat gönderildi.")
        time.sleep(1)

except KeyboardInterrupt:
    logging.warning("Klavye kesintisi (CTRL+C) ile program sonlandırıldı.")

finally:
    logging.info("Program kapatıldı.")