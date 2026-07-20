import cv2

def main():
    feed = cv2.VideoCapture(0)
    ret, frame = feed.read()
    active = True
    while active == True:
        cv2.imshow("Dice Cam", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            active = False
    feed.release()
    cv2.destroyAllWindows()

main()