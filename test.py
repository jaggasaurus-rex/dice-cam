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
