import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULTS = {
  "roi_points": None,
  "camera_mount": "overhead",
  "webhook_url": None,
  "noise_threshold": None,
  "focus_value": None,
}

def loadConfig():
    if not os.path.isfile(CONFIG_PATH):
        saveConfig(DEFAULTS)

    cfg = DEFAULTS.copy()
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg.update(json.load(f))
    except json.JSONDecodeError:
        pass
    return cfg

def saveConfig(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=4, sort_keys=True)

def writeEntryToConfig(entry_name, entry_value):
    cfg = loadConfig()
    if cfg.get(entry_name) is not None:
        while True:
            answer = input("Will overwrite previous value [Continue (Y/N)]: ")
            if answer.strip().lower() == "y":
                break
            elif answer.strip().lower() == "n":
                return cfg
            else:
                print("Answer must be a Y or an N")
    cfg[entry_name] = entry_value
    saveConfig(cfg)
    return cfg

def forceWriteToConfig(entry_name, entry_value):
    cfg = loadConfig()
    cfg[entry_name] = entry_value
    saveConfig(cfg)
    return cfg

def firstRunReset():
    forceWriteToConfig("roi_points", None)
    forceWriteToConfig("focus_value", None)