import cv2

capture = cv2.VideoCapture(0, apiPreference=cv2.CAP_DSHOW)
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
capture.set(cv2.CAP_PROP_AUTOFOCUS, 1)
if capture.get(cv2.CAP_PROP_AUTOFOCUS) != 1.0:
    print(F'WARNING: autofocus not honoured (readback {capture.get(cv2.CAP_PROP_AUTOFOCUS)})')

def cameraInitialization():
    capture_count = 0
    while capture_count <=30:
        capture.read()
        capture_count+=1
    print("Camera Initialized")