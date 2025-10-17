import cv2
import cv2.aruco as aruco
import serial
import os
import time
import threading
import sys
import select

# --- Arduino setup ---
ser = serial.Serial('/dev/cu.usbmodem1101', 9600)  # adjust port
time.sleep(2)
print("✅ Arduino connected.")

# --- Camera setup ---
cams = [
    cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION),
    cv2.VideoCapture(1, cv2.CAP_AVFOUNDATION)
]
for i, cam in enumerate(cams):
    if not cam.isOpened():
        print(f"⚠ Could not open camera {i}")

# --- ArUco setup ---
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()

# --- Stations per camera ---
stations_cam1 = {"station1": (50, 100, 250, 250), "station2": (350, 100, 250, 250)}
stations_cam2 = {"station3": (50, 100, 250, 250), "station4": (350, 100, 250, 250)}

# --- Marker assignments ---
marker_to_station = {1: "station1", 2: "station2", 3: "station3", 4: "station4"}
camera_markers = {0: [1, 2], 1: [3, 4]}

# --- State tracking ---
marker_state = {1: False, 2: False, 3: False, 4: False}
marker_out = False
last_speech_time = 0
speech_interval = 2  # seconds

# --- Task switch timer ---
last_task_switch = time.time()
task_interval = 30  # seconds

# --- LED state tracking ---
led_state = "GREEN"

# --- Functions ---
def is_in_tray(center, tray_rect):
    x, y, w, h = tray_rect
    cx, cy = center
    return x <= cx <= x + w and y <= cy <= y + h

def process_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
    return corners, ids

def check_speech():
    global last_speech_time
    if marker_out:
        now = time.time()
        if now - last_speech_time > speech_interval:
            os.system('say "Marker out of tray"')
            last_speech_time = now

def send_led_state(state):
    global led_state
    if state != led_state:
        if state == "GREEN":
            ser.write(b"DEFAULT_GREEN\n")
        elif state == "RED_BLINK":
            ser.write(b"ALARM_ON\n")
        elif state == "BLUE_BLINK":
            ser.write(b"SWITCH_TASK\n")
        elif state == "YELLOW_BLINK":
            ser.write(b"YELLOW_BLINK\n")
        led_state = state

def countdown_task_switch():
    send_led_state("BLUE_BLINK")
    os.system('say "Switching tasks soon"')
    for i in range(5, 0, -1):
        os.system(f'say "{i}"')
        time.sleep(1)
    os.system('say "Switch Tasks Now"')
    time.sleep(0.5)
    send_led_state("GREEN")

# --- Simulator thread ---
def simulator_input():
    print("Simulator ready: enter 2=marker out, 3=too loud, 4=too quiet")
    while True:
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.readline().strip()
            # Only trigger if no real-time priority events are active
            if not marker_out and (time.time() - last_task_switch) < task_interval - 5:
                if key == "2":
                    print("🔴 Simulator: Marker out triggered")
                    os.system('say "Marker out of tray" &')
                    send_led_state("RED_BLINK")
                    time.sleep(0.5)
                    send_led_state("GREEN")
                elif key in ["3", "4"]:
                    msg = "Volume is too loud. Calm down" if key == "3" else "Too quiet. Not enough socialising"
                    print(f"🟡 Simulator: {msg}")
                    os.system(f'say "{msg}" &')
                    for _ in range(5):
                        send_led_state("YELLOW_BLINK")
                        time.sleep(0.7)  # blink duration
                    send_led_state("GREEN")  # revert once at the end

# Start simulator thread
threading.Thread(target=simulator_input, daemon=True).start()

# --- Main loop ---
while True:
    frames = []
    for i, cam in enumerate(cams):
        ret, frame = cam.read()
        if not ret: continue
        frames.append(frame)
    if not frames: continue

    min_height = min([f.shape[0] for f in frames])
    frames = [cv2.resize(f, (int(f.shape[1]*min_height/f.shape[0]), min_height)) for f in frames]

    current_out = set()
    for cam_idx, frame in enumerate(frames):
        stations_this_frame = stations_cam1 if cam_idx == 0 else stations_cam2
        corners, ids = process_frame(frame)
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                if marker_id not in camera_markers[cam_idx]: continue
                pts = corners[i][0].astype(int)
                cx, cy = int(pts[:, 0].mean()), int(pts[:, 1].mean())
                assigned_station = marker_to_station[marker_id]
                in_tray = is_in_tray((cx, cy), stations_this_frame[assigned_station])
                if not in_tray: current_out.add(marker_id)
                color = (255, 0, 0) if not in_tray else (0, 255, 0)
                cv2.polylines(frame, [pts], True, color, 2)
                cv2.putText(frame, f"Marker {marker_id}: {'OUT!' if not in_tray else 'In tray'}",
                            (cx, cy-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        for s_name, (x, y, w, h) in stations_this_frame.items():
            cv2.rectangle(frame, (x, y, w, h), (0, 0, 255), 2)
            cv2.putText(frame, s_name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

    try:
        combined = cv2.hconcat(frames)
    except cv2.error:
        combined = frames[0]

    any_marker_out = bool(current_out)
    if any_marker_out and not marker_out:
        marker_out = True
    elif not any_marker_out and marker_out:
        marker_out = False

    now = time.time()
    elapsed = now - last_task_switch

    if marker_out:
        send_led_state("RED_BLINK")
    elif elapsed >= task_interval - 5 and elapsed < task_interval:
        countdown_task_switch()
        last_task_switch = now
    else:
        send_led_state("GREEN")

    for marker_id in camera_markers[0] + camera_markers[1]:
        if marker_id in current_out and not marker_state[marker_id]:
            print(f"⚠ Marker {marker_id} out!")
            marker_state[marker_id] = True
        elif marker_id not in current_out and marker_state[marker_id]:
            print(f"✅ Marker {marker_id} back")
            marker_state[marker_id] = False

    check_speech()
    cv2.imshow("Utensil Monitor", combined)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

for cam in cams: cam.release()
cv2.destroyAllWindows()
