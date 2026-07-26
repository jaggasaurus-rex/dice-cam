from tkinter import *
from tkinter import ttk

def demo():
    root = Tk()
    frm = ttk.Frame(root, padding=10)
    frm.grid()

    url_var = StringVar()            # live draft — updates every keystroke
    saved_url_var = StringVar()      # committed value — only updates on Save
    saved_url_var.set("(nothing saved yet)")

    ttk.Entry(frm, textvariable=url_var, width=40).grid(column=0, row=0, padx=5)

    def save():
        saved_url_var.set(url_var.get())

    ttk.Button(frm, text="Save", command=save).grid(column=1, row=0)

    ttk.Label(frm, text="Currently saved:").grid(column=0, row=1, sticky="w", pady=(10,0))
    ttk.Label(frm, textvariable=saved_url_var, foreground="blue").grid(column=0, row=2, columnspan=2, sticky="w")

    root.mainloop()

demo()


##### Unused cleanup area:

#define blob size (diameter in pixels)
max_dia = 55
min_dia = 20

#set parameters for blob detector
params = cv2.SimpleBlobDetector_Params()
params.filterByCircularity = True
params.minCircularity = 0.8
params.blobColor = 255
params.filterByColor = False
params.maxArea = math.pi * ((max_dia/2) ** 2)
params.minArea = math.pi * ((min_dia/2) ** 2)

#generates detector
detector = cv2.SimpleBlobDetector_create(params)


def pipCount():
    ret, frame = feed.read()

    if ret == False:
        return

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

    #keypoints = detector.detect(bw)

    #return len(keypoints)

    success, buffer = cv2.imencode('.jpg', bw)

    image_jpg = buffer.tobytes()

    dice_count = ollamaCall(image_jpg)

    print(dice_count)

    #return dice_count
