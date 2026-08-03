import cv2
import statistics
from general_variables import *
import time
from config import *
from camera import capture
from frame_initialization import *


def frameConversion(frame):
    bw = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(bw, (5,5), 0)
    return blur

def frameDiff(active, prev):
    diff = cv2.absdiff(active,prev)
    result = cv2.mean(diff, mask=None)
    return result[0]

def displayWindow(frame):
    cv2.imshow("dice cam", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        return True

def cropToRoi(frame, roi):
    x, y, w, h = roi
    return frame[y:y+h, x:x+w]

def frameNoise(roi):
    prev = None
    samples = []
    counter = 0
    active = True
    threshold = 0.0
    while active == True:
        ret, frame = capture.read()
        if ret is False:
            raise Exception("Camera read error")
        crop = cropToRoi(frame, roi)
        blur = frameConversion(crop)
        if prev is not None:
            result = frameDiff(blur, prev)
            if result == 0:
                continue
            counter+=1
            if counter >= 30:
                samples.append(result)
            
        prev = blur

        if counter >= 60:
            mean_frame_noise = statistics.mean(samples) + 4 * statistics.stdev(samples)
            threshold = mean_frame_noise * error_margin
            active = False
    return threshold, prev

def cameraCalibration(roi):
    print("Calibrating - Keep Tray Empty and Still")
    threshold, background = frameNoise(roi)  #need to insert ROI
    print("Calibration complete, waiting for roll")
    return threshold, background

def dieRollDetection(threshold, roi):
    prev = None
    result = 0.0
    moving = False
    quiet_since = None
    above_thresh_count = 0
    while True:
        ret, frame = capture.read()
        if ret is False:
            raise Exception("Camera read error")
        cropped = cropToRoi(frame, roi)
        current_frame = frameConversion(cropped)
        if prev is not None:
            result = frameDiff(current_frame, prev)
            if result == 0:
                continue
            elif result > threshold:
                above_thresh_count+= 1
                if above_thresh_count >= 5:
                    moving = True
                    quiet_since = None
                
            elif result <= threshold:
                above_thresh_count = 0
                if moving == True:
                    if quiet_since is None:
                        quiet_since = time.monotonic()
                    elif time.monotonic() - quiet_since >= roll_dwell:
                        moving = False
                        quiet_since = None
                        yield "SETTLE"

        prev = current_frame

