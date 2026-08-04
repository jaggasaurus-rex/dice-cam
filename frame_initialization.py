import cv2
from camera import capture
from config import *
from settle_detector import *
import numpy as np
from general_variables import *

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


def occupancyCount(processed_frame, background, poly_mask):
    diff = cv2.absdiff(processed_frame, background)
    _, changed = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    changed = cv2.bitwise_and(changed, poly_mask)
    return changed, cv2.countNonZero(changed)

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

def buildTrayGeometry(cfg):
    pts = np.array(cfg["roi_points"], dtype=np.int32)
    x, y, w, h = cv2.boundingRect(pts)
    poly_mask = np.zeroes((h, w), dtype=np.uint8)
    cv2.fillPoly(poly_mask, [pts - [x, y]], 255)
    return [x, y, w, h], poly_mask




