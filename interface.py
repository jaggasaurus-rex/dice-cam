from live_frame import pipCount
from tkinter import*
from tkinter import ttk 
from discord import fireMessage

def userWindow():
    root = Tk()
    root.geometry("800x600")
    frm = ttk.Frame(root, padding=10)
    frm.grid()

    pip_text = StringVar()
    pip_text.set("")

    root.columnconfigure(0, weight=1)

    ttk.Label(frm, textvariable=pip_text, font=("Helvetica",120,"bold")).grid(column=0, row=0,columnspan=3,sticky="",padx=10)
    ttk.Button(frm, text="Quit", command=root.destroy).grid(column=3, row=1,sticky="e")
   
    def refresh():
        pips_check = pipCount()
        if pips_check:
            pip_text.set(pips_check)
            fireMessage(pips_check)
        root.after(500, refresh)

    root.after(500, refresh)
    root.mainloop()