import cv2

capture = cv2.VideoCapture(0, apiPreference=cv2.CAP_ANY)
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
capture.set(cv2.CAP_PROP_AUTOFOCUS, 1)
