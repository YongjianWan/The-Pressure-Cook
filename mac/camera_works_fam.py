# camera_works_fam.py — ROI/Marker 檢視器（跨平台相機後端，不送事件）
# 功能：顯示 zones.json 的多邊形（TABLE/TRAY/PLATE…）與每張 ArUco 的 ID 位置
# 用途：量 Marker ID、檢查 ROI 是否貼合現場

# ROI/Marker Viewer (Cross-platform camera backend, no event sending)
# Function: Display polygons from zones.json (TABLE/TRAY/PLATE...) and each ArUco marker's ID position
# Purpose: Measure Marker ID, check if ROI fits the scene

import json, sys
import numpy as np
import cv2
from cv2 import aruco

# ===== Read zones.json =====
with open("zones.json", "r", encoding="utf-8") as f:
    Z = json.load(f)
POLY = {z["name"]: np.array(z["pts"], np.int32) for z in Z}

# ===== Camera backend (cross-platform) =====
def open_cam(index=0, w=1280, h=720, fps=30):
    if sys.platform.startswith("win"):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    cap.set(cv2.CAP_PROP_FPS,          fps)
    return cap

cap = open_cam(0, 1280, 720, 30)

# ===== Dictionary (change according to your sticker type) =====
DICT = aruco.DICT_5X5_100     # 4x4_50 / 5x5_100 / 6x6_250
adict  = aruco.getPredefinedDictionary(DICT)
params = aruco.DetectorParameters()

print("[viewer] DICT =", DICT, "| ESC ")  # ESC to exit

while True:
    ok, frame = cap.read()
    if not ok:
        print("[viewer] read fail"); break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = aruco.detectMarkers(gray, adict, parameters=params)

    # Draw ROI
    for name, poly in POLY.items():
        cv2.polylines(frame, [poly], True, (0, 255, 0) if name != "TABLE" else (255, 0, 0), 2)
        center = poly.mean(axis=0).astype(int)
        cv2.putText(frame, name, tuple(center), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

    # Draw Marker and ID
    if ids is not None:
        aruco.drawDetectedMarkers(frame, corners, ids)
        for i, mid in enumerate(ids.flatten()):
            c  = corners[i][0]
            cx = int(c[:, 0].mean())
            cy = int(c[:, 1].mean())
            cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
            cv2.putText(frame, f"ID:{mid}", (cx+6, cy-6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

    cv2.imshow("ROI / Marker Viewer", frame)
    if cv2.waitKey(1) == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()
