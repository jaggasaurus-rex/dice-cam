import cv2
import os
import datetime
from settle_detector import *
from config import *
from camera import capture

capture_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures")
os.makedirs(capture_directory, exist_ok=True)


def saveSingleFrame(frame):
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    file_name = f"roll_{stamp}.png"
    file_location = os.path.join(capture_directory, file_name)
    if not cv2.imwrite(file_location, frame):
        raise IOError(f"Failed to write capture: {file_location}")

def generateAndSaveFrame(roi):
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    file_name = f"roll_{stamp}.png"
    file_location = os.path.join(capture_directory, file_name)

    ret, frame = capture.read()
    if ret is False:
        raise Exception("Camera read error")

    cropped_frame = cropToRoi(frame, roi)
    if not cv2.imwrite(file_location, cropped_frame):
        raise IOError(f"Failed to write capture: {file_location}")
            
def sharpness(frame, roi):
    gray = cv2.cvtColor(cropToRoi(frame, roi), cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def sharpestFrame(roi, count=8):
    best_frame = None
    best_score = -1.0
    for _ in range(count):
        ret, frame = capture.read()
        if ret is False:
            raise Exception("Camera read error")
        score = sharpness(frame, roi)
        if score > best_score:
            best_score = score
            best_frame = frame
    return best_frame, best_score