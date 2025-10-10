import cv2
from cv2 import aruco


# Cross-platform camera opener
def open_cam(index=0, w=1280, h=720, fps=30):
    import sys
    if sys.platform.startswith("win"):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(index)
    cap.set(3, w); cap.set(4, h); cap.set(5, fps)
    return cap

cap = open_cam(0, 1280, 720, 30)

dicts = [
    (aruco.DICT_4X4_50,  "4x4_50"),
    (aruco.DICT_5X5_100, "5x5_100"),
    (aruco.DICT_6X6_250, "6x6_250"),
]
params = aruco.DetectorParameters()

print("[detect_dict] Point any marker at the camera; top-left shows dictionary & ID; press ESC to quit.")
while True:
    ok, frame = cap.read()
    if not ok: break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    shown = frame.copy()

    found = False
    for d, name in dicts:
        adict = aruco.getPredefinedDictionary(d)
        corners, ids, _ = aruco.detectMarkers(gray, adict, parameters=params)
        if ids is not None:
            aruco.drawDetectedMarkers(shown, corners, ids)
            cv2.putText(shown, f"Dict: {name}", (20,40), 0, 1.0, (0,255,0), 2)
            for i, mid in enumerate(ids.flatten()):
                c = corners[i][0]
                cx = int(c[:,0].mean()); cy = int(c[:,1].mean())
                cv2.putText(shown, f"ID:{mid}", (cx+6,cy-6), 0, 0.8, (0,0,255), 2)
            break

    cv2.imshow("Detect ArUco Dictionary", shown)
    if cv2.waitKey(1) == 27: break

cap.release(); cv2.destroyAllWindows()
