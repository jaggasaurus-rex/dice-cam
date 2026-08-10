import cv2
import time
from general_variables import max_focus_value

capture = cv2.VideoCapture(0, apiPreference=cv2.CAP_DSHOW)
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
capture.set(cv2.CAP_PROP_AUTOFOCUS, 1)
if capture.get(cv2.CAP_PROP_AUTOFOCUS) != 1.0:
    print(F'WARNING: autofocus not honoured (readback {capture.get(cv2.CAP_PROP_AUTOFOCUS)})')

def cameraInitialization():
    print("Initializing Camera")
    capture_count = 0
    while capture_count <=30:
        capture.read()
        capture_count+=1
    print("Camera Initialized")

def setFocusAndSettle(value):
    if not 0 <= value <= max_focus_value:
        print(f"Potential focus value error: {value}")
    value = max(0, min(max_focus_value, value))
    capture.set(cv2.CAP_PROP_FOCUS, value)
    time.sleep(0.3)
    capture_count = 0
    while capture_count <= 5:
        capture.read()
        capture_count+=1
