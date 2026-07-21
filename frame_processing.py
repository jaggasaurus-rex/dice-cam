import cv2
import math

def getFrame():
    feed = cv2.VideoCapture(0)
    ret, frame = feed.read()
    feed.release()
    return frame
    
def processedFrame():
    frame = getFrame()
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
    return bw

def findPips():
    max = 55
    min = 20
    params = cv2.SimpleBlobDetector_Params()
    params.filterByCircularity = True
    params.minCircularity = 0.8
    params.blobColor = 255
    params.filterByColor = False
    params.maxArea = math.pi * ((max/2) ** 2)
    params.minArea = math.pi * ((min/2) ** 2)
    detector = cv2.SimpleBlobDetector_create(params)
    frame = processedFrame()
    keypoints = detector.detect(frame)
    return keypoints

def pipCount():
    pips = findPips()
    return len(pips)

def printPipLoop():
    last_count = 0
    active = True
    while active == True :
        pips = findPips()
        dice = len(pips)        
        if last_count != dice & dice != 0:
            last_count = dice
            print(dice)