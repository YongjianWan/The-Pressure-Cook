# camera.py — ArUco + 多 ROI + 去抖（跨平台相機後端）→ 以 UDP 丟事件給 Hub
# camera.py — ArUco + multi-ROI + debouncing (cross-platform camera backend) → emit events to Hub via UDP
# 需要：allow.json（Marker ID → 允許區），zones.json（TABLE/TRAY/PLATE… 多邊形）
# Requires: allow.json (marker ID → allowed zones), zones.json (TABLE/TRAY/PLATE... polygons)
# 事件（UDP 送往 127.0.0.1:8787）：HARD_OUT / MESSY_ON / MESSY_OFF
# Events (UDP to 127.0.0.1:8787): HARD_OUT / MESSY_ON / MESSY_OFF

import json, time, socket, sys
import numpy as np
import cv2
from cv2 import aruco

UDP_HOST, UDP_PORT = "127.0.0.1", 8787
CAM_W, CAM_H, CAM_FPS = 1280, 720, 30

DICT = aruco.DICT_5X5_100  # aruco.DICT_4X4_50 / aruco.DICT_6X6_250

MISS_HIDE   = 0.5   # 短暫看不到 <0.5s 忽略 / ignore brief occlusion <0.5 s
HARD_OUT_ON = 0.4   # 桌外連續 ≥0.3~0.5s 才成立 / outside table ≥0.3–0.5 s triggers
MESSY_ON_S  = 1.0   # 離位連續 ≥1.0s → MESSY_ON / outside allowed zones ≥1.0 s triggers MESSY_ON
MESSY_OFF_S = 0.8   # 回位連續 ≥0.8s → MESSY_OFF / back in allowed zone ≥0.8 s triggers MESSY_OFF
MISSING_KILL = 5.0  # ★ 看不到超過 5s 視為「失蹤」→ 強制清狀態 / unseen >5 s considered missing → clear state

def load_allow(path="allow.json"):
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {int(k): v for k, v in raw.items()}

def load_zones(path="zones.json"):
    with open(path, "r", encoding="utf-8") as f:
        Z = json.load(f)
    poly = {z["name"]: np.array(z["pts"], np.int32) for z in Z}
    table = poly.get("TABLE")
    sections = {name: p for name, p in poly.items() if name != "TABLE"}
    return table, sections, poly

ALLOW = load_allow("allow.json")
TABLE, SECTIONS, POLY = load_zones("zones.json")

def open_cam(index=0, w=1280, h=720, fps=30):
    if sys.platform.startswith("win"):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(index)
    cap.set(3, w); cap.set(4, h); cap.set(5, fps)
    return cap

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
def emit(msg: str): sock.sendto(msg.encode(), (UDP_HOST, UDP_PORT))

def in_poly(pt, poly) -> bool: return cv2.pointPolygonTest(poly, pt, False) >= 0
def in_any(pt, names) -> bool:
    for n in names:
        if n in SECTIONS and in_poly(pt, SECTIONS[n]): return True
    return False

last_seen, bad_since, good_since = {}, {}, {}
messy_state, hard_state = {}, {}

def main():
    cap = open_cam(0, CAM_W, CAM_H, CAM_FPS)
    adict  = aruco.getPredefinedDictionary(DICT)
    params = aruco.DetectorParameters()
    print("[camera] start:", CAM_W, "x", CAM_H, "@", CAM_FPS, "DICT=", DICT)

    while True:
        ok, frame = cap.read()
        if not ok: print("[camera] read fail"); break
        now = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = aruco.detectMarkers(gray, adict, parameters=params)

        if ids is not None:
            ids = ids.flatten()
            for i, mid in enumerate(ids):
                c  = corners[i][0]
                cx = int(c[:,0].mean()); cy = int(c[:,1].mean())
                pt = (cx, cy)
                last_seen[mid] = now

                # 第 1 關：TABLE
                # Stage 1: TABLE containment
                if TABLE is not None and not in_poly(pt, TABLE):
                    key = ("HARD", mid)
                    if not hard_state.get(mid, False):
                        bad_since.setdefault(key, now)
                        if now - bad_since[key] >= HARD_OUT_ON:
                            hard_state[mid] = True; emit("HARD_OUT")
                    bad_since.pop(("MESSY", mid), None)
                    continue
                else:
                    if hard_state.get(mid, False):
                        hard_state[mid] = False
                        bad_since.pop(("HARD", mid), None)

                # 第 2 關：SECTION（Union）
                # Stage 2: allowed SECTION union
                allow = ALLOW.get(mid, ["TRAY","PLATE"])
                if in_any(pt, allow):
                    good_since.setdefault(mid, now)
                    if messy_state.get(mid, False) and (now - good_since[mid]) >= MESSY_OFF_S:
                        messy_state[mid] = False; emit("MESSY_OFF")
                    bad_since.pop(("MESSY", mid), None)
                else:
                    key = ("MESSY", mid)
                    bad_since.setdefault(key, now)
                    if not messy_state.get(mid, False) and (now - bad_since[key]) >= MESSY_ON_S:
                        messy_state[mid] = True; emit("MESSY_ON")
                    good_since.pop(mid, None)

        # ★ 失蹤超時清理：看不到超過 MISSING_KILL → 清狀態（送一次 MESSY_OFF 以防殘留）
        # ★ Missing timeout: unseen longer than MISSING_KILL → clear state (send MESSY_OFF once if needed)
        now2 = time.time()
        for mid, ts in list(last_seen.items()):
            if now2 - ts > MISSING_KILL:
                if messy_state.get(mid, False):
                    messy_state[mid] = False; emit("MESSY_OFF")
                if hard_state.get(mid, False):
                    hard_state[mid] = False
                bad_since.pop(('HARD', mid), None)
                bad_since.pop(('MESSY', mid), None)
                good_since.pop(mid, None)
                # 視覺提示可選：在這裡加上 LOST 畫面標記
                # Optional visual cue: draw LOST indicator here

        # ——（校正可留，用不到可註解）——
        # —— Calibration overlay (keep or comment out) ——
        for name, poly in POLY.items():
            cv2.polylines(frame, [poly], True, (0,255,0) if name!='TABLE' else (255,0,0), 2)
        if ids is not None:
            aruco.drawDetectedMarkers(frame, corners, ids)
        cv2.imshow("camera-messy", frame)
        if cv2.waitKey(1) == 27: break

    cap.release(); cv2.destroyAllWindows()

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: pass
