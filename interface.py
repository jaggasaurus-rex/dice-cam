from live_frame import pipCount, liveFeed, newRollDetector
from tkinter import*
from tkinter import ttk 
from discord import fireMessage
from quick_functions import *
from ui_vars import *

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
    ttk.Label(frm, textvariable=pip_text, font=("Helvetica",120,"bold")).grid(column=result_label_column, row=result_label_row,columnspan=3,sticky="",padx=10)

    #Discord Server Settings
    ttk.Label(frm, text="Discord Channel URL").grid(column=dsc_url_label_column,row=dsc_url_label_row)
    ttk.Entry(frm, textvariable=input_url, width=40).grid(column=dsc_url_entry_column, row=dsc_url_entry_row)
    def save():
        saved_url.set(input_url.get())
    ttk.Button(frm, text="Save", command=save).grid(column=dsc_save_button_column, row=dsc_save_button_row)

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

    ttk.Label(frm, text="Discord Status: ").grid(column=dsc_status_label_column, row=dsc_status_label_row)
    ttk.Button(frm,textvariable=discord_state, command=discordToggle).grid(column=dsc_status_button_column, row=dsc_status_button_row)   


    #Quit Button
    ttk.Button(frm, text="Quit", command=root.destroy).grid(column=quit_button_column, row=quit_button_row,sticky="e")
   
    last_pips = 0

    def refresh():
        pips_check = pipCount()
        nonlocal last_pips
        if pips_check != last_pips and last_pips == 0:
            pip_text.set(pips_check)
            
            if discord_state.get() == "On":
                fireMessage(pips_check, saved_url.get())
            
            last_pips = pips_check
        
        elif last_pips == 0:
            pip_text.set("Roll")
            last_pips = pips_check

        else:
            last_pips = pips_check

        root.after(500, refresh)

    root.after(500, refresh)
    root.mainloop()