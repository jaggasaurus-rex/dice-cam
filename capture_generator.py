import cv2
import os
import time
from settle_detector import *
from config import *
from camera import capture

capture_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures")

def saveCapture(roi):
    os.makedirs(capture_directory, exist_ok=True)
    file_name = f"roll_{time.strftime('%Y%m%d_%H%M%S')}.png"
    file_location = os.path.join(capture_directory, file_name)

    ret, frame = capture.read()
    if ret is False:
        raise Exception("Camera read error")

    cropped_frame = cropToRoi(frame, roi)
    cv2.imwrite(file_location, cropped_frame)
    