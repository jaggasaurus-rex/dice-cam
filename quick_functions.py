def toggle(state):
    if state == "On":
        state = "Off"
    elif state == "Off":
        state = "On"
    else:
        raise Exception("invalid input detected")
    return state