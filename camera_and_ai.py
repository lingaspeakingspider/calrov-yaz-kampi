import cv2
import numpy as np
from ultralytics import YOLO
import logging

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

class LevelColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[34m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[41m',
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
formatter = LevelColorFormatter(LOG_FORMAT)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# Trackbar callback fonksiyonu (boş)
def nothing(x):
    pass

try:
    model = YOLO('yolov11.pt')
    logging.info("YOLOv11 modeli başarıyla yüklendi.")
except Exception as e:
    logging.error(f"YOLO modeli yüklenirken bir hata oluştu: {e}")
    exit()

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    logging.error("Kamera açılamadı. Lütfen cihaz bağlantısını kontrol edin.")
    exit()
else:
    logging.info("Kamera başarıyla başlatıldı.")

window_name = "YOLOv11 Nesne Tespiti ve HSV Filtresi"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

# HSV ayar penceresi
control_window = "HSV Kontrol"
cv2.namedWindow(control_window, cv2.WINDOW_NORMAL)
cv2.resizeWindow(control_window, 400, 300)

# Trackbar'ları kontrol penceresine ekle
cv2.createTrackbar('H Min', control_window, 35, 179, nothing)
cv2.createTrackbar('S Min', control_window, 100, 255, nothing)
cv2.createTrackbar('V Min', control_window, 100, 255, nothing)
cv2.createTrackbar('H Max', control_window, 85, 179, nothing)
cv2.createTrackbar('S Max', control_window, 255, 255, nothing)
cv2.createTrackbar('V Max', control_window, 255, 255, nothing)

while True:
    ret, frame = cap.read()
    if not ret:
        logging.warning("Kare alınamadı, kamera bağlantısı kopmuş olabilir.")
        break
    
    display_width = 640
    display_height = 480
    frame = cv2.resize(frame, (display_width, display_height))
    
    # YOLO tespiti
    results = model(frame)
    for r in results:
        boxes = r.boxes
        for box in boxes:
            cls_id = int(box.cls[0])
            class_name = model.names[cls_id]
            confidence = float(box.conf[0])
            
            if confidence > 0.5:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                label = f"{class_name}: {confidence:.2f}"
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    # Trackbar değerlerini al
    h_min = cv2.getTrackbarPos('H Min', control_window)
    s_min = cv2.getTrackbarPos('S Min', control_window)
    v_min = cv2.getTrackbarPos('V Min', control_window)
    h_max = cv2.getTrackbarPos('H Max', control_window)
    s_max = cv2.getTrackbarPos('S Max', control_window)
    v_max = cv2.getTrackbarPos('V Max', control_window)
    
    lower_green = np.array([h_min, s_min, v_min])
    upper_green = np.array([h_max, s_max, v_max])
    
    # HSV filtresi
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv_frame, lower_green, upper_green)
    
    # Morfolojik işlemler - gürültüyü azalt
    kernel = np.ones((3,3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Filtrelenmiş sonuç - doğru renk filtresi
    hsv_filtered_result = cv2.bitwise_and(frame, frame, mask=mask)
    
    # Alternatif görüntüleme seçenekleri (yorumdan çıkarabilirsiniz):
    # 1. Seçili olmayan alanları karartma:
    # hsv_filtered_result = frame.copy()
    # hsv_filtered_result[mask == 0] = hsv_filtered_result[mask == 0] * 0.2
    
    # 2. Seçili alanlar renkli, geri kalan gri:
    # gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # gray_frame = cv2.cvtColor(gray_frame, cv2.COLOR_GRAY2BGR)
    # mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    # hsv_filtered_result = np.where(mask_3channel > 0, frame, gray_frame)
    
    # Kontrol penceresi için bilgi metni
    info_img = np.zeros((300, 400, 3), dtype=np.uint8)
    cv2.putText(info_img, f"H: {h_min}-{h_max}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(info_img, f"S: {s_min}-{s_max}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(info_img, f"V: {v_min}-{v_max}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(info_img, "Renk Araliklari:", (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(info_img, "Yesil: H=35-85", (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(info_img, "Mavi: H=100-130", (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
    cv2.putText(info_img, "Kirmizi: H=0-10,170-179", (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.putText(info_img, "Sari: H=15-35", (10, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    cv2.putText(info_img, "Q: Cikis", (10, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.imshow(control_window, info_img)
    
    combined_output = np.hstack((frame, hsv_filtered_result))
    cv2.imshow(window_name, combined_output)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        logging.info("Program kullanıcı tarafından sonlandırıldı.")
        break

cap.release()
cv2.destroyAllWindows()
logging.info("Tüm kaynaklar serbest bırakıldı.")