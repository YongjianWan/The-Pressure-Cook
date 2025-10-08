import cv2
import cv2.aruco as aruco

cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)  # try 0, 1, 2
if cap.isOpened():
    print("Camera works!")


if not cap.isOpened():
    print("ERROR: Could not open camera. Make sure Terminal has camera access in macOS Privacy settings.")
    exit()

# --- ArUco dictionary & detector parameters ---
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

# Use this instead of DetectorParameters_create()
parameters = aruco.DetectorParameters()  

# --- Tray boundary (x, y, w, h) ---
tray_bounds = (100, 200, 300, 200)  # adjust these values for your setup

def is_in_tray(center, tray_rect):
    x, y, w, h = tray_rect
    cx, cy = center
    return x <= cx <= x + w and y <= cy <= y + h

# --- Main loop ---
while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame from camera")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # --- Detect markers ---
    corners, ids, rejected = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

    if ids is not None:
        for corner, marker_id in zip(corners, ids.flatten()):
            pts = corner[0].astype(int)
            cx = int(pts[:, 0].mean())
            cy = int(pts[:, 1].mean())

            # Draw marker boundary
            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
            cv2.putText(frame, f"ID {marker_id}", (cx, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

            # Check if marker is inside tray
            if is_in_tray((cx, cy), tray_bounds):
                cv2.putText(frame, "In tray", (cx, cy + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "OUT OF TRAY!", (cx, cy + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                print(f"⚠️ ALERT: Marker {marker_id} out of tray!")

    # --- Draw tray boundary ---
    x, y, w, h = tray_bounds
    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

    # --- Show camera feed ---
    cv2.imshow("Tray Monitor - ArUco", frame)

    # Quit on pressing 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
