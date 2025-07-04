import ultralytics
import logging
import cv2

class AI():
    def __init__(self):
        self.model = ultralytics.YOLO("ai_components/yolo11n.pt")
        self.gst = ""
        self.logger = logging.Logger("CALROV Yaz")
        
    def detect(self, frame):
        self.predictions = self.model.predict(frame, conf = 0.7)
        
        for self.prediction in self.predictions:
            for self.box in self.prediction.boxes:
                self.object_name = self.prediction.names[int(self.box.cls[0])]
                
                x1, y1, x2, y2 = int(self.box.xyxy[0][0]), int(self.box.xyxy[0][1]), int(self.box.xyxy[0][2]), int(self.box.xyxy[0][3])
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color = (0, 0, 255), thickness = 2)
                cv2.putText(frame, self.object_name, (x1, y1 - 10), fontFace = 2, color = (0, 0, 255), fontScale = 1)

                self.logger.critical(self.object_name)

        return cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    def main(self):
        video = cv2.VideoCapture(self.gst, cv2.CAP_GSTREAMER)
        
        while True:
            ret, self.frame = video.read()
            
            if ret:
                self.frame = self.detect(self.frame)
                
                cv2.imshow("CAM", self.frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
        video.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    AI().main()