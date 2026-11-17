"""
Arctis Nova Pro Wireless: power button -> Play/Pause.

Every press of the headset power button changes the ANC state, and the
headset reports it as `07 bd <state>`. Each state change is treated as a
button press and sends the system Play/Pause media key.

Install:  py -m pip install hidapi
Run:      py arctis_pause.py       (or pyw arctis_pause.py for no window)
"""
import ctypes
import threading
import time

import hid

VID = 0x1038
PID = 0x12E0  # Arctis Nova Pro Wireless
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002
IGNORE_AFTER_OPEN = 1.5  # seconds: skip the status dump right after connecting
DEBOUNCE = 0.25
MODE = "any"  # "sidetone": only double-click; "any": every state change
SIDETONE = 0x01

lock = threading.Lock()
last_state = None
last_trigger = 0.0
running = {}  # path -> thread


def press_play_pause():
    user32 = ctypes.windll.user32
    user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
    user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_KEYUP, 0)


def handle(data):
    global last_state, last_trigger
    if len(data) < 3 or data[0] != 0x07 or data[1] != 0xBD:
        return
    state = data[2]
    with lock:
        old = last_state
        changed = old is None or state != old
        if changed and MODE == "sidetone":
            changed = state == SIDETONE or old == SIDETONE
        last_state = state
        now = time.time()
        if changed and now - last_trigger > DEBOUNCE:
            last_trigger = now
            print(f"state={state:02x} -> Play/Pause")
            press_play_pause()


def listen(path):
    try:
        dev = hid.device()
        dev.open_path(path)
        dev.set_nonblocking(False)
        opened = time.time()
        while True:
            data = dev.read(64, 1000)
            if data and time.time() - opened > IGNORE_AFTER_OPEN:
                handle(data)
    except Exception as e:
        print(f"listener stopped: {e}")
    finally:
        running.pop(path, None)


def main():
    print("Running. Press the headset power button. Ctrl+C to stop.")
    while True:
        for d in hid.enumerate(VID, PID):
            path = d["path"]
            if path not in running:
                t = threading.Thread(target=listen, args=(path,), daemon=True)
                running[path] = t
                t.start()
        time.sleep(3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
