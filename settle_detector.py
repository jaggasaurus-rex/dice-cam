import cv2
import statistics
from general_variables import *
import time


capture = cv2.VideoCapture(0, apiPreference=cv2.CAP_ANY)

def frameNoise():
    prev = None
    samples = []
    counter = 0
    active = True
    while active == True:
        ret, frame = capture.read()
        if ret is False:
            break
        bw = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(bw, (5,5), 0)
        if prev is not None:
            diff = cv2.absdiff(blur, prev)
            result = cv2.mean(diff, mask=None)
            cv2.imshow("dice came", blur)
            if cv2.waitKey(1) & 0xFF == ord('q'): 
                break
            if result[0] == 0:
                continue
            counter+=1
            if counter >= 30:
                samples.append(result[0])
            
        prev = blur

        if counter >= 60:
            mean_frame_noise = statistics.mean(samples) + 4 * statistics.stdev(samples)
            threshhold = mean_frame_noise * error_margin
            active = False
            return threshhold


def rollDetector():
    active = True
    moving = True
    quiet_since = None
    threshold = frameNoise()
    prev = None
    while active == True:
        ret, frame = capture.read()
        if ret is False:
            break
        bw = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(bw, (5,5), 0)
        if prev is not None:
            diff = cv2.absdiff(blur, prev)
            result = cv2.mean(diff, mask=None)
            cv2.imshow("dice came", blur)
            if cv2.waitKey(1) & 0xFF == ord('q'): 
                break
            if result[0] == 0:
                continue

            detection_variable = result[0] - threshold

            print(detection_variable)

            prev = blur



    capture.release()
    cv2.destroyAllWindows()


"""
    if result[0] > threshhold:
        moving = True
        print("MOVING")

    if moving:
        if quiet_since is None:
            quiet_since = time.monotonic()
        elif time.monotonic() - quiet_since >= 0.5:
            print("SETTLE")
            moving = False
            quiet_since = None
"""

rollDetector()

