import cv2
import math
from ollama_func import ollamaCall

#initialize camera feed
feed = cv2.VideoCapture(0)

def cropFrame():
    ret, frame = feed.read()
    
    if ret == False:
        raise Exception("Camera Problem")
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    _, rough = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(rough, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    die = max(contours, key=cv2.contourArea)

    x, y, w, h = cv2.boundingRect(die)

    die_crop = gray[y:y+h, x:x+w]

    return die_crop

def normalizeFrame(cropped_die):
    used_thresh, bw = cv2.threshold(cropped_die, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    white_pixels = cv2.countNonZero(bw)
    total_pixels = bw.size

    if white_pixels > total_pixels / 2:
        bw = cv2.bitwise_not(bw)

    return bw

def findTop(bw_image):
    parts, _ = cv2.findContours(bw_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    crop_h, crop_w = bw_image.shape
    center_x, center_y = crop_w / 2, crop_h / 2

    kept = []
    for c in parts:
        M = cv2.moments(c)
        if M["m00"] == 0:
            continue

        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]

        dist = ((cx - center_x)**2 + (cy - center_y)**2) ** 0.5

        if dist < crop_w * 0.25 and cv2.contourArea(c) > 50:
            kept.append(c)

    print("blobs kept:", len(kept))

    vis = cv2.cvtColor(bw_image, cv2.COLOR_GRAY2BGR)
    cv2.drawContours(vis, kept, -1, (0, 255, 0), 2)
    imgDisplay(vis)
        


def imgDisplay(image):
    active = True
    while active == True:
        cv2.imshow("Display Test", image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            active = False


def liveFeed():
    active = True
    while active == True:
        _, frame = feed.read()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        
        #_, bw = cv2.adaptiveThreshold(blur, 127, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        bw = cv2.adaptiveThreshold(
            blur, 
            255, 
            cv2.ADAPTIVE_THRESH_MEAN_C, 
            cv2.THRESH_BINARY_INV,
            11,
            3)
        cv2.imshow("Dice Cam", bw)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            active = False


def newRollDetector():
    pips_1 = pipCount()
    pips_2 = 0
    while True:
        if pips_1 != pips_2:
            if pips_1 != 0 and pips_2 == 0:
                print(pips_1)
            pips_2 = pips_1
            
        else:
            pips_1 = pipCount()
