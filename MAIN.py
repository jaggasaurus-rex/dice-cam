from live_frame import pipCount
from tkinter import*
from tkinter import ttk

def main():
    root = Tk()
    frm = ttk.Frame(root, padding=10)
    frm.grid()

    pip_text = StringVar()
    pip_text.set(pipCount())

    ttk.Label(frm, textvariable=pip_text).grid(column=0, row=0)
    ttk.Button(frm, text="Quit", command=root.destroy).grid(column=0, row=3)
   
    def refresh():
        pip_text.set(pipCount())
        root.after(500, refresh)

    root.after(500, refresh)
    root.mainloop()

main()