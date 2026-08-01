from settle_detector import *
from capture_generator import *
from config import *

def main():
    cfg = firstRunROIConfig()
    roi = cfg["roi"]
    threshhold = cameraCalibration(roi)
    while True:
        for event in dieRollDetection(threshhold, roi):
            saveCapture(roi)
    

main()