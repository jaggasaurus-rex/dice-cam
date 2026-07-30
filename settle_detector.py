import cv2
import statistics
from general_variables import *
import time


capture = cv2.VideoCapture(0, apiPreference=cv2.CAP_ANY)

def frameConversion(frame):
    bw = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(bw, (5,5), 0)
    return blur

def frameDiff(active, prev):
    diff = cv2.absdiff(active,prev)
    result = cv2.mean(diff, mask=None)
    return result[0]

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


def dieRollDetection():
    print("Calibrating camera environment")
    threshhold = frameNoise()
    print("Calibration complete, waiting for roll")
    prev = None
    result = 0.0
    moving = False
    quiet_since = None
    while True:
        ret, frame = capture.read()
        if ret is False:
            raise Exception("Camera read error")
        cv2.imshow("dice came", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
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
                        print("SETTLE")
                        moving = False
                        quiet_since = None

        prev = current_frame


