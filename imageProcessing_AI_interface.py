import logging
import cv2

class AI():
    def __init__(self, gst1, gst2):
        self.gst1 = gst1
        self.gst2 = gst2
        self.logger = logging.Logger("CALROV Yaz")
    
    def cam1(self, video):
        self.video1 = video
        ret1, self.frame1 = self.video1.read()
     
        return ret1, self.frame1
        
    def cam2(self, video):
        self.video2 = video
        ret2, self.frame2 = self.video2.read()
            
        return ret2, self.frame2
    
    def release1(self):
        self.video1.release()
    
    def release2(self):
        self.video2.release()