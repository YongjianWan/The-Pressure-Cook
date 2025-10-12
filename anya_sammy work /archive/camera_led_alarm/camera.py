import cv2
import cv2.aruco as aruco
import serial
import serial.tools.list_ports
import os
import time


# --- Arduino setup (cross-platform) ---
def find_arduino_port():
    """自动检测 Arduino 串口"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # Arduino Uno 的 VID:PID 是 2341:0043 或 2341:0001
        if "2341" in port.hwid or "Arduino" in port.description:
            return port.device
    # 如果找不到，返回 None
    return None


arduino_port = find_arduino_port()
if arduino_port is None:
    print("ERROR: Arduino not found. Please connect Arduino and try again.")
    print("Available ports:")
    for p in serial.tools.list_ports.comports():
        print(f"  {p.device}: {p.description}")
    exit()

ser = serial.Serial(arduino_port, 9600)
time.sleep(2)
print(f"Arduino connected on {arduino_port}.")

# --- Camera setup ---
cams = [
    cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION),  # Camera 1
    cv2.VideoCapture(1, cv2.CAP_AVFOUNDATION)   # Camera 2
]
for i, cam in enumerate(cams):
    if not cam.isOpened():
        print(f"⚠️ Warning: Could not open camera {i}")

# --- ArUco setup ---
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()
tray_bounds = (100, 200, 300, 200)

def is_in_tray(center, tray_rect):
    x, y, w, h = tray_rect
    cx, cy = center
    return x <= cx <= x + w and y <= cy <= y + h

# --- Global state ---
marker_out = False
stop_speech = threading.Event()

def say_out_of_tray():
    """Repeats 'Out of tray' until stopped"""
    while not stop_speech.is_set():
        os.system('say "Out of tray"')
        time.sleep(2)

# --- Main loop ---
while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera read failed.")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
    return corners, ids

def check_speech():
    global last_speech_time
    if marker_out:
        now = time.time()
        if now - last_speech_time > speech_interval:
            os.system('say "Counter is messy"')
            last_speech_time = now

# --- Main loop ---
while True:
    frames = []
    for i, cam in enumerate(cams):
        ret, frame = cam.read()
        if not ret or frame is None:
            continue
        frames.append(frame)

    if not frames:
        continue

    # Resize all frames to same height
    min_height = min([f.shape[0] for f in frames])
    frames = [cv2.resize(f, (int(f.shape[1]*min_height/f.shape[0]), min_height)) for f in frames]

    current_out = set()

    # Process each camera separately
    for cam_idx, frame in enumerate(frames):
        stations_this_frame = stations_cam1 if cam_idx == 0 else stations_cam2

        corners, ids = process_frame(frame)
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                # Skip markers not assigned to this camera
                if marker_id not in camera_markers[cam_idx]:
                    continue

                pts = corners[i][0].astype(int)
                cx, cy = int(pts[:,0].mean()), int(pts[:,1].mean())
                assigned_station = marker_to_station[marker_id]

                in_tray = is_in_tray((cx, cy), stations_this_frame[assigned_station])

            color = (0, 255, 0) if in_tray else (0, 0, 255)
            text = "In tray" if in_tray else "OUT OF TRAY!"
            cv2.polylines(frame, [pts], True, color, 2)
            cv2.putText(frame, text, (cx, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                if not in_tray:
                    current_out.add(marker_id)

        # Draw station boxes
        for s_name, (x, y, w, h) in stations_this_frame.items():
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
            cv2.putText(frame, s_name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

    # Combine frames side by side
    try:
        combined = cv2.hconcat(frames)
    except cv2.error:
        combined = frames[0]

    # --- Handle alarms ---
    any_marker_out = bool(current_out)
    if any_marker_out and not marker_out:
        # Some marker went out, send ALARM_ON
        ser.write(b"ALARM_ON\n")
        marker_out = True
    elif not any_marker_out and marker_out:
        # All markers back, send ALARM_OFF
        ser.write(b"ALARM_OFF\n")
        marker_out = False

    # Update individual marker states for logging
    for marker_id in camera_markers[0] + camera_markers[1]:
        if marker_id in current_out and not marker_state[marker_id]:
            print(f"⚠️ Marker {marker_id} out!")
            marker_state[marker_id] = True
        elif marker_id not in current_out and marker_state[marker_id]:
            print(f"✅ Marker {marker_id} back")
            marker_state[marker_id] = False

    # Non-blocking speech
    check_speech()

    cv2.imshow("Tray Monitor", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        stop_speech.set()
        break

# Cleanup
for cam in cams:
    cam.release()
cv2.destroyAllWindows()
