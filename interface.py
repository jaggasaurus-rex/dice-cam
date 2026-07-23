from live_frame import pipCount, liveFeed, newRollDetector
from tkinter import*
from tkinter import ttk 
from discord import fireMessage
from quick_functions import *

def userWindow():
    root = Tk()
    root.geometry("800x600")
    frm = ttk.Frame(root, padding=10)
    frm.grid()

    pip_text = StringVar()
    pip_text.set("")

    root.columnconfigure(0, weight=1)

    input_url = StringVar()
    saved_url = StringVar()
    saved_url.set("Discord not integrated")

    #Result Display
    ttk.Label(frm, textvariable=pip_text, font=("Helvetica",120,"bold")).grid(column=0, row=0,columnspan=3,sticky="",padx=10)

    #Discord Server Settings
    ttk.Entry(frm, textvariable=input_url, width=40).grid(column=0, row=1)
    def save():
        saved_url.set(input_url.get())
    ttk.Button(frm, text="Save", command=save).grid(column=1, row=1)

    #Discord Toggle
    discord_state = StringVar()
    discord_state.set("Off")

    def discordToggle():
        if discord_state.get() == "Off":
            discord_state.set("On")
        elif discord_state.get() == "On":
            discord_state.set("Off")
        else:
            raise Exception("Issue with Discord Toggle")

    ttk.Button(frm,text="Discord On/OFF", command=discordToggle).grid(column=2, row=1)   


    #Quit Button
    ttk.Button(frm, text="Quit", command=root.destroy).grid(column=1, row=4,sticky="e")
   
    last_pips = 0

    def refresh():
        pips_check = pipCount()
        nonlocal last_pips
        if pips_check != last_pips and last_pips == 0:
            print(f"post checking for truthy: {pips_check}")
            pip_text.set(pips_check)
            
            ###uncomment to turn Discord notifications on
            if discord_state.get() == "On":
                fireMessage(pips_check, saved_url.get())
            
            last_pips = pips_check
        
        elif last_pips == 0:
            pip_text.set("Rolling")
            last_pips = pips_check

        else:
            last_pips = pips_check

        root.after(500, refresh)

    root.after(500, refresh)
    root.mainloop()