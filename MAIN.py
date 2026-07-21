from frame_processing import pipCount
from tkinter import*
from tkinter import ttk

def main():
    root = Tk()
    frm = ttk.Frame(root, padding=10)
    frm.grid()
    pips = pipCount()
    ttk.Label(frm, text=pips).grid(column=0, row=0)
    ttk.Button(frm, text="Quit", command=root.destroy).grid(column=0, row=3)
    root.mainloop()

    #printPipLoop()


    ## Frame Print Code
    #active = True
    #while active == True:
    #    cv2.imshow("Dice Cam", frame)
    #    if cv2.waitKey(1) & 0xFF == ord('q'):
    #        active = False
    #cv2.destroyAllWindows()

main()