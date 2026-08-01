import cv2
import statistics
from general_variables import *
import time
from config import *
from camera import capture
import numpy as np


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
    if cfg["roi_points"] is not None:
        return cfg
    while True:
        points = multiPoint()
        if points is not None:
            break    
        print("Tray outline required - please click at lest 3 points")  # user cancelled - re-prompting

    cfg = writeEntryToConfig("roi_points", points)
    cv2.destroyAllWindows()
    return cfg


def occupancyCount(processed_frame, background):
    diff = cv2.absdiff(processed_frame, background)
    _, mask = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    return mask, cv2.countNonZero(mask)

def grabProcessedFrame(frame, roi):
    cropped = cropToRoi(frame, roi)
    processed = frameConversion(cropped)
    return processed

def onMouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        param.append([x, y])

def multiPoint():
    ret, frame = capture.read()
    if ret is False:
        raise Exception("Camera read error")
    points = []
    cv2.namedWindow("dice cam")
    cv2.setMouseCallback("dice cam", onMouse, param=points)
    while True:
        display = frame.copy()

        for p in points:
            cv2.circle(display, tuple(p), 4, (0, 255, 0), -1)
        if len(points) >= 2:
            cv2.polylines(display, [np.array(points, dtype=np.int32)], False, (0, 255, 0), 2)
        if len(points) >= 2:
                    cv2.polylines(display, [np.array(points, dtype=np.int32)], True, (0, 255, 0), 2)
        

        cv2.imshow("dice cam", display)

        key = cv2.waitKey(1) & 0xFF    #Enter
        if key == 13 and len(points) >= 3:
            break
        elif key == ord('z') and points:  #undo
            points.pop()
        elif key == 27:       #esc
            cv2.destroyWindow("dice cam")
            return None

    cv2.destroyWindow("dice cam")
    return points


firstRunROIConfig()