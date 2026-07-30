import cv2
import statistics
from general_variables import *
import time
from config import *


capture = cv2.VideoCapture(0, apiPreference=cv2.CAP_ANY)

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

def frameNoise():
    prev = None
    samples = []
    counter = 0
    active = True
    threshhold = 0.0
    while active == True:
        ret, frame = capture.read()
        if ret is False:
            break
        blur = frameConversion(frame)
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

def cameraCalibration():
    print("Calibrating camera environment")
    threshhold = frameNoise()
    print("Calibration complete, waiting for roll")
    return threshhold

def dieRollDetection(threshhold):
    prev = None
    result = 0.0
    moving = False
    quiet_since = None
    while True:
        ret, frame = capture.read()
        if ret is False:
            raise Exception("Camera read error")
        current_frame = frameConversion(frame)
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
            break     # user cancelled - re-prompting
        print("ROI required - please drag a box")

    cfg["roi"] = roi
    return cfg

def codeTester():
    try:
        cfg = firstRunROIConfig()
        print(cfg)
    except KeyboardInterrupt:
        pass
    finally:
        capture.release()
        cv2.destroyAllWindows()

codeTester()