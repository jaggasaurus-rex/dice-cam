import cv2
import os
import datetime
import statistics
import json
from settle_detector import *
from config import *
from camera import capture, setFocusAndSettle
from general_variables import fine_sweep_step_size, coarse_sweep_step_size

capture_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures")
os.makedirs(capture_directory, exist_ok=True)
tests_directory = os.path.join(os.path.dirname(__file__), "test_images")
os.makedirs(tests_directory, exist_ok=True)


def saveSingleFrame(frame):
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    file_name = f"roll_{stamp}.png"
    file_location = os.path.join(capture_directory, file_name)
    if not cv2.imwrite(file_location, frame):
        raise IOError(f"Failed to write capture: {file_location}")
    return file_location

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

def focusScore(frame, roi, poly_mask):
    crop = cropToRoi(frame, roi)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    _, std = cv2.meanStdDev(lap, mask=poly_mask)
    return float(std[0][0] ** 2)

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

def focusSweep(roi, poly_mask):
    input("Place a die in the tray. Press ENTER when done.")
    value = 0
    score_tracker = []
    while value <= max_focus_value:
        setFocusAndSettle(value)
        _, frame = capture.read()
        score = focusScore(frame, roi, poly_mask)
        score_tracker.append([value,score])
        value+=coarse_sweep_step_size

    best_score = max(score_tracker, key=lambda p: p[1])

    return best_score[0]

def focusFineSweep(roi, poly_mask, cfg):
    if cfg["focus_value"] is None:
        center = focusSweep(roi, poly_mask)
        low_bound = center - 20
        high_bound = center + 20
        value = low_bound
        score_tracker = []
        while value <= high_bound:
            counter = 0
            average_score_tracker = []
            setFocusAndSettle(value)
            while counter <= 4:
                _, frame = capture.read()
                score = focusScore(frame, roi, poly_mask)
                average_score_tracker.append(score)
                counter+=1
            float_avg = statistics.fmean(average_score_tracker)
            score_tracker.append([value, float_avg])
            value += fine_sweep_step_size

        best_score = max(score_tracker, key=lambda p: p[1])

        cfg = forceWriteToConfig("focus_value", best_score[0])

        return cfg

    else:
        return cfg

def saveLabeledFrame(frame, meta, directory):
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    base = os.path.join(directory, f"roll_{stamp}")
    if not cv2.imwrite(base + ".png", frame):
        raise IOError(f"Failed to write capture: {base}.png")
    with open(base + ".json", "w") as f:
        json.dump(meta, f, indent=4)
    return base + ".png"