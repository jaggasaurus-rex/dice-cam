import cv2
import statistics
from general_variables import *
import time
from config import *
from camera import capture


def frameConversion(frame):
    bw = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(bw, (5,5), 0)
    return blur

def frameDiff(active, prev):
    diff = cv2.absdiff(active,prev)
    result = cv2.mean(diff, mask=None)
    return result[0]

def displayWindow(frame):
    cv2.imshow("dice came", frame)
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
    threshhold = 0.0
    while active == True:
        ret, frame = capture.read()
        if ret is False:
            break
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
            threshhold = mean_frame_noise * error_margin
            active = False
    return threshhold

def cameraCalibration(roi):
    print("Calibrating camera environment")
    threshhold = frameNoise(roi)  #need to insert ROI
    print("Calibration complete, waiting for roll")
    return threshhold

def dieRollDetection(threshhold, roi):
    prev = None
    result = 0.0
    moving = False
    quiet_since = None
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
            if result > threshhold:
                moving = True
                quiet_since = None
            if result <= threshhold:
                if moving == True:
                    if quiet_since is None:
                        quiet_since = time.monotonic()
                    elif time.monotonic() - quiet_since >= roll_dwell:
                        moving = False
                        quiet_since = None
                        return "SETTLE"

        prev = current_frame

def selectRoi():
    counter = 0
    active = True
    while active == True:
        ret, frame = capture.read()
        if ret is False:
            raise Exception("Camera read error")
        counter+=1
        if counter >= 30:
            roi = cv2.selectROI("Calibration Window", frame, showCrosshair=True, fromCenter=False)
            if roi[2] == 0 or roi[3] == 0: #user cancelled
                return None
            
            active = False

            return [int(v) for v in roi]

def firstRunROIConfig():
    cfg = loadConfig()
    if cfg["roi"] is not None:
        return cfg
    while True:
        roi = selectRoi()
        if roi is not None:
            break    
        print("ROI required - please drag a box")  # user cancelled - re-prompting

    cfg = writeEntryToConfig("roi", roi)
    cv2.destroyAllWindows()
    return cfg
