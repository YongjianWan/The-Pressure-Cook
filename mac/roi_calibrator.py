import cv2, json, numpy as np

# 区域坐标标采集工具
# ROI (Region of Interest) Calibrator Tool
# 用法：运行后在摄像头画面上左键点击添加多边形顶点，右键点击结束并命名该区域
# Usage: Run and left-click to add polygon vertices, right-click to finish and name the ROI
# 按 U 撤销当前多边形的最后一个点，按 Z 删除最后一个已保存区域
# Press U to undo last point of current polygon, Z to delete last saved ROI
# 按 S 保存到 zones.json，按 Q 或 ESC 退出
# Press S to save to zones.json, Q or ESC to quit
WIN = "ROI Calibrator"
zones = []
current = []
snap = None


def draw():
    img = snap.copy()
    for z in zones:
        pts = np.array(z["pts"], np.int32)
        cv2.polylines(img, [pts], True, (0, 255, 0), 2)
        M = pts.mean(axis=0).astype(int)
        cv2.putText(
            img, z["name"], tuple(M), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
        )
    if current:
        pts = np.array(current, np.int32)
        cv2.polylines(img, [pts], False, (0, 200, 255), 2)
    cv2.imshow(WIN, img)


def on_mouse(e, x, y, flags, param):
    if e == cv2.EVENT_LBUTTONDOWN:
        current.append((x, y))
        draw()
    elif e == cv2.EVENT_RBUTTONDOWN and len(current) >= 3:
        name = (
            input("ROI name (TABLE/TRAY/PLATE/...): ").strip() or f"ROI{len(zones)+1}"
        )
        zones.append({"name": name, "pts": current.copy()})
        current.clear()
        draw()


cap = cv2.VideoCapture(0)
ok, frame = cap.read()
cap.release()
if not ok:
    raise RuntimeError("Failed to read from camera")
snap = frame.copy()
cv2.namedWindow(WIN)
cv2.setMouseCallback(WIN, on_mouse)
draw()
print(
    "Controls: left-click to add points, right-click/Enter to name ROI; U undo point; Z remove last ROI; S save; Q quit."
)
while True:
    k = cv2.waitKey(20) & 0xFF
    if k in (27, ord("q")):
        break
    if k == ord("u") and current:
        current.pop()
        draw()
    if k == ord("z") and zones:
        zones.pop()
        draw()
    if k == ord("s"):
        with open("zones.json", "w", encoding="utf-8") as f:
            json.dump(zones, f, ensure_ascii=False, indent=2)
        print("Saved zones.json")
cv2.destroyAllWindows()
