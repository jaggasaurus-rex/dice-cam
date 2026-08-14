from settle_detector import cameraCalibration, dieRollDetection, cropToRoi
from frame_initialization import firstRunROIConfig, occupancyCount, buildTrayGeometry, grabProcessedFrame, validCapture
from capture_generator import  saveSingleFrame, sharpestFrame, focusFineSweep, saveLabeledFrame, tests_directory
from llm_gemini import readDie
from general_variables import *
from config import *
from camera import capture, cameraInitialization
import cv2

def main():
    try:
        cfg = firstRunROIConfig()
        roi, poly_mask = buildTrayGeometry(cfg)
        threshold, background = cameraCalibration(roi, poly_mask)
        #saveSingleFrame(background)

        for event in dieRollDetection(threshold, roi, poly_mask):
            frame, score = sharpestFrame(roi)
            if score < sharpness_floor:
                print(f"Focus lost ({score:.0f}) - roll again")
                continue
            processed_frame = grabProcessedFrame(frame, roi)
            mask, occupancy_count = occupancyCount(processed_frame, background, poly_mask)
            if occupancy_count > partial_occupancy_min and occupancy_count < occupancy_threshold:
                print("Roll not fully in frame. Roll again.")
            elif occupancy_count >= outlier_occupancy:
                print("Object obscuring camera. Roll again.")
            elif occupancy_count >= occupancy_threshold and occupancy_count < outlier_occupancy:
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not contours:
                    continue
                die = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(die)
                roi_crop = cropToRoi(frame, roi)
                y1 = max(0, y-crop_pad)
                x1 = max(0, x-crop_pad)
                y2 = min(roi_crop.shape[0], y + h + crop_pad)
                x2 = min(roi_crop.shape[1], x + w + crop_pad)
                die_crop = roi_crop[y1:y2, x1:x2]
                file_location = saveSingleFrame(die_crop)

            #print(file_location)
            #value = readDie(file_location)
            #print(value)
    finally:
        cv2.destroyAllWindows()
        capture.release()


def mainALT():
    try:
        cameraInitialization()
        cfg = firstRunROIConfig()
        roi, poly_mask = buildTrayGeometry(cfg)
        cfg = focusFineSweep(roi, poly_mask, cfg)
        threshold, background = cameraCalibration(roi, poly_mask)
        capture.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        capture.set(cv2.CAP_PROP_FOCUS, cfg["focus_value"])
        #saveSingleFrame(background)

        for event in dieRollDetection(threshold, roi, poly_mask):
            frame, score = sharpestFrame(roi)
            frame_copy = frame.copy()
            roi_crop = cropToRoi(frame_copy, roi)
            masked = cv2.bitwise_and(roi_crop, roi_crop, mask=poly_mask)
            
            file_location = saveSingleFrame(masked)
            ### Comment these fields out for debugging without calling AI
            #value = readDie(file_location)
            #print(value)
    finally:
        #forceWriteToConfig("roi_points", None)
        cv2.destroyAllWindows()
        capture.release()

def mainALT2():
    try:
        cameraInitialization()
        cfg = firstRunROIConfig()
        roi, poly_mask = buildTrayGeometry(cfg)
        cfg = focusFineSweep(roi, poly_mask, cfg)
        capture.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        capture.set(cv2.CAP_PROP_FOCUS, cfg["focus_value"])
        threshold, background = cameraCalibration(roi, poly_mask)
        #saveSingleFrame(background)

        for event in dieRollDetection(threshold, roi, poly_mask):
            frame, score = sharpestFrame(roi)
            frame_copy = frame.copy()
            roi_crop = cropToRoi(frame_copy, roi)
            processed_frame = grabProcessedFrame(frame, roi)
            mask, occupancy_count = occupancyCount(processed_frame, background, poly_mask)
            masked = cv2.bitwise_and(roi_crop, roi_crop, mask=poly_mask)
            if occupancy_count > partial_occupancy_min and occupancy_count < occupancy_threshold:
                print("Roll not fully in frame. Roll again.")
            elif occupancy_count >= occupancy_threshold and occupancy_count < outlier_occupancy:
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not contours:
                    continue
                die = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(die)
                ok, reason = validCapture(x ,y ,w, h, occupancy_count, masked.shape)
                if not ok:
                    print("Rejected:", reason)
                    continue
                y1 = max(0, y-crop_pad)
                x1 = max(0, x-crop_pad)
                y2 = min(masked.shape[0], y + h + crop_pad)
                x2 = min(masked.shape[1], x + w + crop_pad)
                die_crop = masked[y1:y2, x1:x2]
                meta = {
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "occupancy": int(occupancy_count),
                    "sharpness": float(score),
                    "die": die_id,
                    "value": None,
                    "reject_reason": None,
                    "light_on": False,
                }
                file_location = saveLabeledFrame(masked, meta, tests_directory)
                ### Comment these fields out for debugging without calling AI
                response = readDie(file_location)
                print(response.value)
            elif occupancy_count >= outlier_occupancy :
                print("Object obscuring camera. Roll again.")
    finally:
        #firstRunReset()
        cv2.destroyAllWindows()
        capture.release()


mainALT2()
