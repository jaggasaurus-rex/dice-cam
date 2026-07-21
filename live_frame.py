import cv2
import math

#initialize camera feed
feed = cv2.VideoCapture(0)

#define blob size (diameter in pixels)
max = 55
min = 20

#set parameters for blob detector
params = cv2.SimpleBlobDetector_Params()
params.filterByCircularity = True
params.minCircularity = 0.8
params.blobColor = 255
params.filterByColor = False
params.maxArea = math.pi * ((max/2) ** 2)
params.minArea = math.pi * ((min/2) ** 2)

#generates detector
detector = cv2.SimpleBlobDetector_create(params)


def pipCount():
    ret, frame = feed.read()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    
    #_, bw = cv2.adaptiveThreshold(blur, 127, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    bw = cv2.adaptiveThreshold(
        blur, 
        255, 
        cv2.ADAPTIVE_THRESH_MEAN_C, 
        cv2.THRESH_BINARY_INV,
        31,
        9)

    
    

    keypoints = detector.detect(bw)
 
    return len(keypoints)

