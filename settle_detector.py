import cv2

def frame_detection():
    prev = None
    capture = cv2.VideoCapture(0, apiPreference=cv2.CAP_ANY)
    while True:
        ret, frame = capture.read()
        if ret is False:
            break
        bw = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev is not None:
            diff = cv2.absdiff(bw, prev)
            result = cv2.mean(diff, mask=None)
            cv2.imshow("dice came", bw)
            if cv2.waitKey(1) & 0xFF == ord('q'): 
                break
            print(result[0])
        prev = bw
    capture.release()
    cv2.destroyAllWindows()


frame_detection()

