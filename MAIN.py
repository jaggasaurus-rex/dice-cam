import cv2

def getFrame():
    feed = cv2.VideoCapture(0)
    ret, frame = feed.read()
    feed.release()
    return frame
    
def processedFrame():
    frame = getFrame()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    _, bw = cv2.threshold(blur, 127, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return bw

def findPips():
    params = cv2.SimpleBlobDetector_Params()
    params.filterByCircularity = True
    params.minCircularity = 0.8
    params.blobColor = 255
    params.filterByColor = False
    detector = cv2.SimpleBlobDetector_create(params)
    frame = processedFrame()
    keypoints = detector.detect(frame)
    return keypoints

def main():
    last_count = 0
    active = True
    while active == True :
        frame = processedFrame()
        pips = findPips()
        dice = len(pips)
        cv2.imshow("Dice Cam", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            active = False
        elif last_count != dice:
            last_count = dice
            print(dice)
    cv2.destroyAllWindows()

    print(dice)


    ## Frame Print Code
    #active = True
    #while active == True:
    #    cv2.imshow("Dice Cam", frame)
    #    if cv2.waitKey(1) & 0xFF == ord('q'):
    #        active = False
    #cv2.destroyAllWindows()

main()