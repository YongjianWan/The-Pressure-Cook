import cv2
import cv2.aruco as aruco
import serial
import os
import time
import threading

# --- Arduino setup ---
ser = serial.Serial('/dev/cu.usbmodem101', 9600)
time.sleep(2)
print("Arduino connected.")

# --- Camera + ArUco setup ---
cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
if not cap.isOpened():
    print("ERROR: Could not open camera.")
    exit()

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

    current_out = False

    if ids is not None:
        for corner in corners:
            pts = corner[0].astype(int)
            cx = int(pts[:, 0].mean())
            cy = int(pts[:, 1].mean())
            in_tray = is_in_tray((cx, cy), tray_bounds)

            color = (0, 255, 0) if in_tray else (0, 0, 255)
            text = "In tray" if in_tray else "OUT OF TRAY!"
            cv2.polylines(frame, [pts], True, color, 2)
            cv2.putText(frame, text, (cx, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            if not in_tray:
                current_out = True

    # Marker just went out
    if current_out and not marker_out:
        print("⚠️ Marker out of tray!")
        ser.write(b"ALARM_ON\n")
        stop_speech.clear()
        threading.Thread(target=say_out_of_tray, daemon=True).start()
        marker_out = True

    # Marker came back
    elif not current_out and marker_out:
        print("✅ Marker returned to tray.")
        ser.write(b"ALARM_OFF\n")
        stop_speech.set()
        marker_out = False

    # Draw tray rectangle
    x, y, w, h = tray_bounds
    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

    cv2.imshow("Tray Monitor", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        stop_speech.set()
        break

cap.release()
cv2.destroyAllWindows()
