import cv2
import cv2.aruco as aruco
import serial
import os
import time
import threading
import sys
import select
import queue
# ---- TTS Setup ----
import argparse, os, shlex, threading


# ---- Load station polygons from zones.json / config/zones.json (optional) ----
import json, numpy as np, os

def _load_station_polys():
    for zp in ("zones.json", os.path.join("config", "zones.json")):
        if os.path.exists(zp):
            try:
                with open(zp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Expected format: {"zones":[{"name":"STATION1","pts":[[x,y],...]}, ...]}
                name_map = {"STATION1":"station1", "STATION2":"station2", "STATION3":"station3"}
                out = {}
                for z in data.get("zones", []):
                    name = str(z.get("name","")).strip().upper()
                    pts  = z.get("pts") or []
                    if name in name_map and len(pts) >= 3:
                        out[name_map[name]] = [(int(x), int(y)) for x, y in pts]
                return out
            except Exception:
                pass
    return {}

_STATION_POLYS = _load_station_polys()

def _point_in_poly(x, y, poly):
    # ray casting
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i+1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1):
            inside = not inside
    return inside

# ---------------- Arduino Setup ----------------
ser = serial.Serial('/dev/cu.usbmodem1101', 9600)  # adjust port
time.sleep(2)
print("✅ Arduino connected.")

# ---------------- Camera Setup ----------------
cam = cv2.VideoCapture(1, cv2.CAP_AVFOUNDATION)
if not cam.isOpened():
    raise Exception("⚠ Could not open camera 0")

# ---------------- ArUco Setup ----------------
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()
aruco_detector = aruco.ArucoDetector(aruco_dict, parameters) if hasattr(aruco, "ArucoDetector") else None

# ---------------- Stations ----------------
# Still keeping rectangular stations for fallback
# Format: (x, y, w, h)
stations = {
    "station1": (50, 100, 200, 200),
    "station2": (300, 100, 200, 200),
    "station3": (550, 100, 200, 200)
}

marker_to_station = {1: "station1", 2: "station2", 3: "station3"}
camera_markers = [1, 2, 3]

# ---------------- State Tracking ----------------
marker_state = {1: False, 2: False, 3: False}
marker_out = False
marker_blinking = False
blink_active = False
led_state = "GREEN"

last_speech_time = 0
speech_interval = 1  # seconds
last_task_switch = time.time()
task_interval = 45  # seconds

simulated_queue = []

# ---------------- Speech Queue ----------------
speech_queue = queue.Queue()

ap = argparse.ArgumentParser()
# ap.add_argument("--voice",
#                 default="Sandy",
#                 choices=["Sandy"],  # Only allow Samantha
#                 help="macOS say voice: Sandy")
ap.add_argument("--rate", type=int, default=170, help="Speaking rate (wpm), typically 150–210.")
args, _ = ap.parse_known_args()

def speech_worker():
    while True:
        message = speech_queue.get()
        cmd = f'say -r {args.rate} {shlex.quote(str(message))}'
        os.system(cmd)
        speech_queue.task_done()

# def speech_worker():
#     while True:
#         message = speech_queue.get()
#         os.system(f'say "{message}"')
#         speech_queue.task_done()

threading.Thread(target=speech_worker, daemon=True).start()

def speak(message):
    speech_queue.put(message)

# ---------------- Utility Functions ----------------
# def is_in_tray(center, tray_rect):
#     x, y, w, h = tray_rect
#     cx, cy = center
#     return x <= cx <= x + w and y <= cy <= y + h

def is_in_tray(center, tray_rect, station_key=None):
    cx, cy = center
    if station_key and station_key in _STATION_POLYS:
        return _point_in_poly(cx, cy, _STATION_POLYS[station_key])
    x, y, w, h = tray_rect
    return x <= cx <= x + w and y <= cy <= y + h


def process_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if aruco_detector is not None:
        corners, ids, _ = aruco_detector.detectMarkers(gray)
    elif hasattr(aruco, "detectMarkers"):
        corners, ids, _ = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
    else:
        raise AttributeError("cv2.aruco does not expose detectMarkers or ArucoDetector")
    return corners, ids

def send_led_state(state):
    global led_state
    if state != led_state:
        command_map = {
            "GREEN": b"DEFAULT_GREEN\n",
            "RED_BLINK": b"ALARM_ON\n",
            "BLUE_BLINK": b"SWITCH_TASK\n",
            "YELLOW_BLINK": b"YELLOW_BLINK\n",
            "PINK_BLINK": b"PINK_BLINK\n",
            "OFF": b"OFF\n"
        }
        ser.write(command_map.get(state, b"OFF\n"))
        led_state = state

def blink_led(led_command, times=5, delay=0.35):
    global blink_active
    if blink_active:
        return
    def thread_func():
        global blink_active
        blink_active = True
        for _ in range(times):
            send_led_state(led_command)
            time.sleep(delay)
            send_led_state("OFF")
            time.sleep(delay)
        blink_active = False
    threading.Thread(target=thread_func, daemon=True).start()

def speak_and_blink(message, led_command, times=5, delay=0.35):
    speak(message)
    blink_led(led_command, times, delay)

# ---------------- Simulator Input ----------------
def simulator_input():
    print("Simulator ready: enter 1=marker out, 2=too loud, 3=too quiet, 4=recipe")
    while True:
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.readline().strip()
            simulated_queue.append(key)
        time.sleep(0.05)

threading.Thread(target=simulator_input, daemon=True).start()

# ---------------- Task Countdown ----------------
def countdown_task_switch():
    global blink_active
    if blink_active:
        return

    def thread_func():
        global blink_active
        blink_active = True

        total_blink_time = 7
        blink_interval = 0.4
        start_time = time.time()

        # Start speaking right away (parallel to blinking)
        speak("Switching tasks soon")

        # Blink for total_blink_time seconds
        while time.time() - start_time < total_blink_time:
            send_led_state("BLUE_BLINK")
            time.sleep(blink_interval)
            send_led_state("OFF")
            time.sleep(blink_interval)

        # After 5 seconds, say "Switch tasks now"
        time.sleep(max(0, 5 - (time.time() - start_time)))
        speak("Switch tasks now")

        blink_active = False
        send_led_state("GREEN")

    threading.Thread(target=thread_func, daemon=True).start()


# ---------------- Main Loop ----------------
while True:
    ret, frame = cam.read()
    if not ret:
        continue

    current_out = set()
    corners, ids = process_frame(frame)

    # --- Detect marker out ---
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            if marker_id not in camera_markers:
                continue
            pts = corners[i][0].astype(int)
            cx, cy = int(pts[:, 0].mean()), int(pts[:, 1].mean())
            # assigned_station = marker_to_station[marker_id]
            # in_tray = is_in_tray((cx, cy), stations[assigned_station])
            assigned_station = marker_to_station[marker_id]
            in_tray = is_in_tray((cx, cy), stations[assigned_station], station_key=assigned_station)


            if not in_tray:
                current_out.add(marker_id)
            color = (255, 0, 0) if not in_tray else (0, 255, 0)
            cv2.polylines(frame, [pts], True, color, 2)
            cv2.putText(frame, f"Marker {marker_id}: {'OUT!' if not in_tray else 'In tray'}",
                        (cx, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # --- Draw stations ---
    # for s_name, (x, y, w, h) in stations.items():
    #     cv2.rectangle(frame, (x, y, w, h), (0, 0, 255), 2)
    #     cv2.putText(frame, s_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # --- Draw stations (polygon first, else rectangle) ---
    for s_name, rect in stations.items():
        if s_name in _STATION_POLYS:
            pts = np.array(_STATION_POLYS[s_name], np.int32)
            cv2.polylines(frame, [pts], True, (0, 0, 255), 2)
            M = pts.mean(axis=0).astype(int)
            cv2.putText(frame, s_name, (int(M[0]), int(M[1]) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        else:
            x, y, w, h = rect
            cv2.rectangle(frame, (x, y, w, h), (0, 0, 255), 2)
            cv2.putText(frame, s_name, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)


    # --- Priority Handling ---
    now = time.time()
    task_due = now - last_task_switch >= task_interval - 5

    if task_due and not blink_active:
        countdown_task_switch()
        last_task_switch = now
        marker_out = False  # temporarily ignore marker out during task switch
    elif current_out:
        if not marker_out:
            marker_out = True
        if not blink_active:
            speak_and_blink("Counter too messy.", "RED_BLINK")
    else:
        marker_out = False
        if not blink_active:
            send_led_state("GREEN")

    # --- Process simulated queue only if no high-priority events ---
    if not marker_out and not task_due:
        while simulated_queue:
            key = simulated_queue.pop(0)
            if key == "1":
                speak_and_blink("Counter too messy", "RED_BLINK")
            elif key == "2":
                speak_and_blink("Volume is too loud. Calm down", "YELLOW_BLINK")
            elif key == "3":
                speak_and_blink("Too quiet. Not enough socialising", "YELLOW_BLINK")
            elif key == "4":
                speak_and_blink("Please follow the recipe carefully", "PINK_BLINK")

    # --- Marker state print ---
    for marker_id in camera_markers:
        if marker_id in current_out and not marker_state[marker_id]:
            print(f"⚠ Marker {marker_id} out!")
            marker_state[marker_id] = True
        elif marker_id not in current_out and marker_state[marker_id]:
            print(f"✅ Marker {marker_id} back")
            marker_state[marker_id] = False

    cv2.imshow("Utensil Monitor", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
