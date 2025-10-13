import cv2
import cv2.aruco as aruco
import serial
import os
import time
import threading
import sys
import select

# ---------------- Arduino Setup ----------------
ser = serial.Serial('/dev/cu.usbmodem1101', 9600)  # adjust port
time.sleep(2)
print("✅ Arduino connected.")

# ---------------- Camera Setup ----------------
cam = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
if not cam.isOpened():
    raise Exception("⚠ Could not open camera 0")

# ---------------- ArUco Setup ----------------
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()

# ---------------- Stations ----------------
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

# ---------------- Functions ----------------
def is_in_tray(center, tray_rect):
    x, y, w, h = tray_rect
    cx, cy = center
    return x <= cx <= x + w and y <= cy <= y + h

def process_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
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

def speak(message):
    threading.Thread(target=lambda: os.system(f'say "{message}"'), daemon=True).start()

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
    total_countdown_time = 7  # seconds
    blink_interval = 0.4       # seconds per blink

    def blink_blue():
        global blink_active
        blink_active = True
        end_time = time.time() + total_countdown_time
        while time.time() < end_time:
            send_led_state("BLUE_BLINK")
            time.sleep(blink_interval)
            send_led_state("OFF")
            time.sleep(blink_interval)
        blink_active = False
        send_led_state("GREEN")

    threading.Thread(target=blink_blue, daemon=True).start()
    speak("Switching tasks soon")
    for i in range(5, 0, -1):
        speak(str(i))
        time.sleep(1)
    speak("Switch Tasks Now")
    time.sleep(0.5)
    send_led_state("GREEN")

# ---------------- Marker Out Speech ----------------
def check_marker_out_speech():
    global last_speech_time
    while True:
        if marker_out:
            now = time.time()
            if now - last_speech_time > speech_interval:
                speak("Marker out of tray")
                last_speech_time = now
        time.sleep(0.1)

threading.Thread(target=check_marker_out_speech, daemon=True).start()

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
            cx, cy = int(pts[:,0].mean()), int(pts[:,1].mean())
            assigned_station = marker_to_station[marker_id]
            in_tray = is_in_tray((cx, cy), stations[assigned_station])
            if not in_tray:
                current_out.add(marker_id)
            color = (255,0,0) if not in_tray else (0,255,0)
            cv2.polylines(frame, [pts], True, color, 2)
            cv2.putText(frame, f"Marker {marker_id}: {'OUT!' if not in_tray else 'In tray'}",
                        (cx, cy-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # --- Draw stations ---
    for s_name, (x,y,w,h) in stations.items():
        cv2.rectangle(frame, (x,y,w,h), (0,0,255), 2)
        cv2.putText(frame, s_name, (x,y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

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
            speak_and_blink("Marker out of tray", "RED_BLINK")
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
