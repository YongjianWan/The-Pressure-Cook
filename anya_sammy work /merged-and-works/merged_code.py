import cv2
import cv2.aruco as aruco
import serial
import os
import time
import threading
import sys
import select
import queue

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

# ---------------- Stations (from your clicks) ----------------

stations = {
    "station1": (645, 292, 177, 200),  
    "station2": (20, 350, 300, 250),  
    "station3": (947, 460, 121, 169)
}


marker_to_station = {1: "station1", 2: "station2", 3: "station3"}
camera_markers = [1, 2, 3]

# ---------------- State Tracking ----------------
marker_state = {1: False, 2: False, 3: False}
marker_out = False
blink_active = False
led_state = "GREEN"
last_task_switch = time.time()
task_interval = 45
simulated_queue = []

# ---------------- Speech Queue ----------------
speech_queue = queue.Queue(maxsize=1)
speech_lock = threading.Lock()
last_spoken = ""

def speech_worker():
    global last_spoken
    while True:
        message = speech_queue.get()
        with speech_lock:
            if message != last_spoken:
                os.system(f'say "{message}"')
                last_spoken = message
        speech_queue.task_done()

threading.Thread(target=speech_worker, daemon=True).start()

def speak(message):
    with speech_lock:
        while not speech_queue.empty():
            try:
                speech_queue.get_nowait()
                speech_queue.task_done()
            except queue.Empty:
                break
        try:
            speech_queue.put_nowait(message)
        except queue.Full:
            pass

# ---------------- Utility Functions ----------------
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

        speak("Switching tasks soon")

        while time.time() - start_time < total_blink_time:
            send_led_state("BLUE_BLINK")
            time.sleep(blink_interval)
            send_led_state("OFF")
            time.sleep(blink_interval)

        time.sleep(max(0, 5 - (time.time() - start_time)))
        speak("Switch tasks now")

        blink_active = False
        send_led_state("GREEN")

    threading.Thread(target=thread_func, daemon=True).start()

# ---------------- Mouse Click Callback ----------------
def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"📍 Clicked coordinates: ({x}, {y})")

cv2.namedWindow("Utensil Monitor")
cv2.setMouseCallback("Utensil Monitor", mouse_callback)

# ---------------- Main Loop ----------------
while True:
    ret, frame = cam.read()
    if not ret:
        continue

    current_out = set()
    corners, ids = process_frame(frame)

    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            if marker_id not in camera_markers:
                continue
            pts = corners[i][0].astype(int)
            cx, cy = int(pts[:, 0].mean()), int(pts[:, 1].mean())
            assigned_station = marker_to_station[marker_id]
            in_tray = is_in_tray((cx, cy), stations[assigned_station])
            if not in_tray:
                current_out.add(marker_id)
            color = (255, 0, 0) if not in_tray else (0, 255, 0)
            cv2.polylines(frame, [pts], True, color, 2)
            cv2.putText(frame, f"Marker {marker_id}", (cx, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    for s_name, (x, y, w, h) in stations.items():
        cv2.rectangle(frame, (x, y, w, h), (0, 0, 255), 2)
        cv2.putText(frame, s_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    now = time.time()
    task_due = now - last_task_switch >= task_interval - 5

    if task_due and not blink_active:
        countdown_task_switch()
        last_task_switch = now
        marker_out = False
    elif current_out:
        marker_out = True
        if not blink_active:
            speak_and_blink("Counter too messy.", "RED_BLINK")
    else:
        marker_out = False
        if not blink_active:
            send_led_state("GREEN")

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

    cv2.imshow("Utensil Monitor", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
