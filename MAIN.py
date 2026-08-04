from settle_detector import cameraCalibration, dieRollDetection, cropToRoi
from frame_initialization import firstRunROIConfig, occupancyCount, buildTrayGeometry
from capture_generator import grabProcessedFrame, saveSingleFrame
from general_variables import *
from config import *
from camera import capture
import cv2

def main():
    cfg = firstRunROIConfig()
    roi, poly_mask = buildTrayGeometry(cfg)
    threshold, background = cameraCalibration(roi, poly_mask)
    #saveSingleFrame(background)

    for event in dieRollDetection(threshold, roi, poly_mask):
        ret, frame = capture.read()
        if ret is False:
            raise Exception("Camera read error")
        processed_frame = grabProcessedFrame(frame, roi)
        mask, occupancy_count = occupancyCount(processed_frame, background, poly_mask)
        if occupancy_count > partial_occupancy_min and occupancy_count < occupancy_threshold:
            print("Roll not fully in frame. Roll again.")
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
            saveSingleFrame(die_crop)
        elif occupancy_count >= outlier_occupancy:
            print("Object obscuring camera. Roll again.")


main()