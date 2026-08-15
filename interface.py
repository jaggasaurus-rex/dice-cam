from tkinter import*
from tkinter import ttk 
from discord_webhook import fireMessage
from quick_functions import *
from ui_vars import *
import queue

from settle_detector import cameraCalibration, dieRollDetection, cropToRoi
from frame_initialization import firstRunROIConfig, occupancyCount, buildTrayGeometry, grabProcessedFrame, validCapture
from capture_generator import  saveSingleFrame, sharpestFrame, focusFineSweep, saveLabeledFrame, tests_directory
from llm_gemini import readDie
from general_variables import *
from config import *
from camera import capture, cameraInitialization
import cv2

result_queue = queue.Queue()

def detectionWorker(threshold, roi, poly_mask, background):
    for event in dieRollDetection(threshold, roi, poly_mask):
        frame, score = sharpestFrame(roi)
        frame_copy = frame.copy()
        roi_crop = cropToRoi(frame_copy, roi)
        processed_frame = grabProcessedFrame(frame, roi)
        mask, occupancy_count = occupancyCount(processed_frame, background, poly_mask)
        masked = cv2.bitwise_and(roi_crop, roi_crop, mask=poly_mask)
        if occupancy_count > partial_occupancy_min and occupancy_count < occupancy_threshold:
            result_queue.put(("status", "Roll not fully in frame. Roll again."))
        elif occupancy_count >= occupancy_threshold and occupancy_count < outlier_occupancy:
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
            die = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(die)
            ok, reason = validCapture(x ,y ,w, h, occupancy_count, masked.shape)
            if not ok:
                result_queue.put(("status", f"rejected for {reason}"))
                continue
            y1 = max(0, y-crop_pad)
            x1 = max(0, x-crop_pad)
            y2 = min(masked.shape[0], y + h + crop_pad)
            x2 = min(masked.shape[1], x + w + crop_pad)
            die_crop = masked[y1:y2, x1:x2]
            meta = {
                "bbox": [int(x), int(y), int(w), int(h)],
                "occupancy": int(occupancy_count),
                "sharpness": float(score),
                "die": die_id,
                "value": None,
                "reject_reason": None,
                "light_on": False,
            }
            file_location = saveLabeledFrame(masked, meta, "captures")
            ### Comment these fields out for debugging without calling AI
            response = readDie(file_location)
            result_queue.put(("value", response.value))
        elif occupancy_count >= outlier_occupancy :
            result_queue.put(("status", "Object obscuring camera. Roll again."))

def userWindow():
    root = Tk()
    root.geometry("800x600")
    frm = ttk.Frame(root, padding=10)
    frm.grid()

    die_value = StringVar()
    die_value.set("")

    root.columnconfigure(0, weight=1)

    input_url = StringVar()
    saved_url = StringVar()
    saved_url.set("Discord not integrated")

    #Result Display
    ttk.Label(frm, textvariable=die_value, font=("Helvetica",120,"bold")).grid(column=result_label_column, row=result_label_row,columnspan=3,sticky="",padx=10)

    #Discord Server Settings
    ttk.Label(frm, text="Discord Channel URL").grid(column=dsc_url_label_column,row=dsc_url_label_row)
    ttk.Entry(frm, textvariable=input_url, width=40).grid(column=dsc_url_entry_column, row=dsc_url_entry_row)
    def save():
        saved_url.set(input_url.get())
        forceWriteToConfig("webhook_url", saved_url.get())
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

    def refresh():
        try:
            kind, payload = result_queue.get_nowait()
            if kind == "value":
                die_value.set(str(payload))
                if discord_state.get() == "On":
                    fireMessage(die_value.get())

        except queue.Empty:
            pass

        root.after(500, refresh)

    root.after(100, refresh)
    root.mainloop()