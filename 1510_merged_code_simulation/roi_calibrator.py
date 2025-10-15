# !/usr/bin/env python3
# ROI Calibrator — usage examples
# Live (no photo first): press SPACE to pause, then draw
# python roi_calibrator.py --live --cam 0 --out zones.json

# Take a single snapshot first, then draw (your previous habit)
# python roi_calibrator.py --cam 0 --out zones.json

# Use an existing photo
# python roi_calibrator.py --img table.jpg --out zones.json


_view = {"scale":1.0, "ox":0, "oy":0, "vw":1280, "vh":720, "sw":1280, "sh":720, "mode":"fit"}
# mode can be "fit" (preserve aspect ratio, may leave borders) or "fill" (preserve aspect ratio, fills and crops)


import argparse, json, os, sys, time
from typing import List, Dict, Any, Tuple, Optional
import cv2, numpy as np

WIN = "ROI Calibrator"
zones: List[Dict[str, Any]] = []          # [{'name': str, 'pts': [(x,y), ...]}, ...]
current: List[Tuple[int,int]] = []        # current poly points in ORIGINAL image coords
snap: Optional[np.ndarray] = None         # frozen frame (original size) or loaded image
paused = False
frame_size: Optional[Tuple[int,int]] = None  # (w, h) in ORIGINAL pixels

# =========================
# Robust camera helpers
# =========================
def try_open_camera(index: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(index, cv2.CAP_ANY)
    if cap.isOpened():
        return cap
    if hasattr(cv2, "CAP_AVFOUNDATION"):  # macOS backend fallback
        cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
        if cap.isOpened():
            return cap
    for i in range(0, 4):
        if i == index: 
            continue
        for backend in (getattr(cv2, "CAP_ANY", 0), getattr(cv2, "CAP_AVFOUNDATION", 12000)):
            tmp = cv2.VideoCapture(i, backend)
            if tmp.isOpened():
                print(f"[OK] switched to camera index {i} (backend={backend})")
                return tmp
    return cv2.VideoCapture()  # unopened

def grab_one_frame(cap: cv2.VideoCapture, retries=15, delay=0.08):
    for _ in range(retries):
        ok, frame = cap.read()
        if ok and frame is not None:
            return frame
        time.sleep(delay)
    return None

# =========================
# Viewport scaling helpers
# =========================
# Keeps track of mapping between ORIGINAL image coords <-> VIEW (window) coords
_view = {"scale":1.0, "ox":0, "oy":0, "vw":1280, "vh":720, "sw":1280, "sh":720}

def get_window_size() -> Tuple[int,int]:
    # OpenCV cannot read the window size directly; reuse the last vw,vh captured by make_view
    return _view["vw"], _view["vh"]

def make_view(img: np.ndarray) -> np.ndarray:
    """Return a canvas fitted to current window size, updating _view (scale/offset)."""
    h, w = img.shape[:2]
    # Target window size. OpenCV does not report live window resizing, so we track the max seen so far.
    # If the user enlarged the window, keep that larger size; otherwise stay at least as big as the original baseline.
    vw = max(_view["vw"],  min(max(w, 640), 1920))
    vh = max(_view["vh"],  min(max(h, 360), 1080))
    _view["vw"], _view["vh"] = vw, vh

    # Scale by the smaller factor to maintain aspect ratio, leaving letterbox bars
    s = min(vw / float(w), vh / float(h))
    nw, nh = int(round(w * s)), int(round(h * s))
    ox, oy = (vw - nw) // 2, (vh - nh) // 2

    canvas = np.zeros((vh, vw, 3), dtype=np.uint8)
    if nw > 0 and nh > 0:
        canvas[oy:oy+nh, ox:ox+nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)

    _view.update({"scale": s, "ox": ox, "oy": oy, "sw": w, "sh": h})
    return canvas

def img_to_view_pts(pts: np.ndarray) -> np.ndarray:
    """Map ORIGINAL image points -> VIEW (window) points for drawing."""
    s, ox, oy = _view["scale"], _view["ox"], _view["oy"]
    q = pts.astype(np.float32).copy()
    q[:,0] = q[:,0]*s + ox
    q[:,1] = q[:,1]*s + oy
    return q.astype(np.int32)

def view_to_img_xy(x: int, y: int) -> Optional[Tuple[int,int]]:
    """Map VIEW coords -> ORIGINAL image coords; return None if in letterbox area."""
    s, ox, oy = _view["scale"], _view["ox"], _view["oy"]
    w, h = _view["sw"], _view["sh"]
    ix = (x - ox) / s
    iy = (y - oy) / s
    if ix < 0 or iy < 0 or ix >= w or iy >= h:
        return None
    return int(ix), int(iy)

# =========================
# Draw / UI
# =========================
def draw():
    base = np.zeros((720,1280,3), np.uint8) if snap is None else snap
    canvas = make_view(base)

    # draw finished ROIs (scale for display)
    for z in zones:
        pts_v = img_to_view_pts(np.array(z["pts"], np.int32))
        cv2.polylines(canvas, [pts_v], True, (0,255,0), 2)
        M = pts_v.mean(axis=0).astype(int)
        cv2.putText(canvas, z["name"], tuple(M), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

    # draw current poly
    if current:
        cur_v = img_to_view_pts(np.array(current, np.int32))
        cv2.polylines(canvas, [cur_v], False, (0,200,255), 2)

    # hints (ASCII only)
    hints = [
        "L-click: add point   R-click/Enter: commit ROI   U: undo point   Z: undo ROI",
        "S: save   ESC: quit   Live: SPACE to pause, then draw",
    ]
    y = 28
    for s in hints:
        cv2.putText(canvas, s, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2, cv2.LINE_AA)
        y += 24

    cv2.imshow(WIN, canvas)

def commit_roi():
    global current
    if len(current) >= 3:
        try:
            name = input("ROI name (ASCII only, e.g., TABLE/TRAY/PLATE): ").strip() or f"ROI{len(zones)+1}"
        except Exception:
            name = f"ROI{len(zones)+1}"
        zones.append({"name": name.upper(), "pts": current.copy()})
        current.clear()
    else:
        current.clear()
    draw()

def on_mouse(e, x, y, flags, param):
    if e == cv2.EVENT_LBUTTONDOWN:
        p = view_to_img_xy(x, y)
        if p:
            current.append(p)
            draw()
    elif e == cv2.EVENT_RBUTTONDOWN:
        commit_roi()

# =========================
# Save / error screen
# =========================
# =========================
# Save / error screen
# =========================
def save_zones(outpath: str, target_size=None):
    global frame_size
    if frame_size is None:
        print("[ERR] Cannot save: frame size unknown. Pause Live or load an image first.")
        return

    # Original drawing size
    cw, ch = int(frame_size[0]), int(frame_size[1])

    # If needed, scale points to the requested size (e.g., 1920x1080)
    scaled_zones = zones
    final_w, final_h = cw, ch
    if target_size and isinstance(target_size, tuple) and len(target_size) == 2:
        W, H = int(target_size[0]), int(target_size[1])
        if W > 0 and H > 0 and (W != cw or H != ch):
            sx, sy = (W / float(cw)), (H / float(ch))
            scaled_zones = []
            for z in zones:
                pts = [(int(round(x * sx)), int(round(y * sy))) for (x, y) in z["pts"]]
                scaled_zones.append({"name": z["name"], "pts": pts})
            final_w, final_h = W, H
            print(f"[OK] Scaled ROI from {cw}x{ch} -> {W}x{H}")
        else:
            print("[INFO] --set-size matches current frame; no scaling needed.")

    payload = {
        "frame_size": {"width": final_w, "height": final_h},
        "zones": scaled_zones
    }
    os.makedirs(os.path.dirname(outpath) or ".", exist_ok=True)
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved {outpath} (frame {final_w}x{final_h})")


# =========================
# Main
# =========================
def main():
    global snap, paused, frame_size

    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="Use camera; SPACE to pause, then draw")
    ap.add_argument("--img", type=str, help="Annotate on an existing image")
    ap.add_argument("--cam", type=int, default=1, help="Camera index (default: 0)")
    ap.add_argument("--out", type=str, default="config/zones.json", help="Output JSON (default: config/zones.json)")
    ap.add_argument("--cap-width", type=int, default=1920, help="Capture width (live)")
    ap.add_argument("--cap-height", type=int, default=1080, help="Capture height (live)")
    # ==== NEW: Force saved output to a specific pixel size (e.g., 1920x1080) ====
    ap.add_argument("--set-size", type=str, default=None,
                    help="Force saved ROI to this size (WxH), e.g., 1920x1080 for iPhone landscape")
    args = ap.parse_args()

    # Parse --set-size (store as tuple and apply on save)
    target_size = None
    if args.set_size:
        try:
            w_str, h_str = args.set_size.lower().split("x")
            target_size = (int(w_str), int(h_str))
        except Exception:
            print("[WARN] --set-size should look like 1920x1080; ignored.")
            target_size = None

    # Default to live if no mode specified
    if not args.img and not args.live:
        args.live = True

    # Use resizable window; we'll scale content ourselves
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WIN, on_mouse)

    # Mode: image
    if args.img:
        img = cv2.imread(args.img)
        if img is None:
            show_error_screen([f"Failed to read image: {args.img}", "Check the path/filename."])
            return
        snap = img
        frame_size = (snap.shape[1], snap.shape[0])
        draw()
        while True:
            k = cv2.waitKey(20) & 0xFF
            if k == 27: break
            if handle_edit_keys(k, args.out, target_size=target_size): break
        cv2.destroyAllWindows()
        return

    # Mode: live (pause to draw)
    if args.live:
        cap = try_open_camera(args.cam)
        if not cap.isOpened():
            show_error_screen([
                "Cannot open camera (permission/in-use/index).",
                "macOS: System Settings > Privacy & Security > Camera: allow Terminal/VSCode.",
                "Close apps locking the camera (Zoom/Meet/Browser).",
                "Try: --cam 1 or --cam 2.",
            ])
            return

        # Optional: request higher capture size (keeps 1:1 correctness)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  args.cap_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.cap_height)

        print("[Live] SPACE pause/resume; ESC quit; after pausing, draw ROIs then Enter/Right-click to commit.")
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                show_error_screen([
                    "Failed to read frames. Camera may be in use or permission missing.",
                    "Check system camera permission or close other apps."
                ])
                break

            if not paused:
                view = make_view(frame)
                cv2.putText(view, "LIVE (SPACE to pause and draw)", (18, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2, cv2.LINE_AA)
                cv2.imshow(WIN, view)
            else:
                if snap is None:
                    snap = frame.copy()
                    frame_size = (frame.shape[1], frame.shape[0])
                    draw()

            k = cv2.waitKey(1) & 0xFF
            if k == 27:  # ESC
                break
            if k == ord(' '):  # SPACE
                paused = not paused
                if paused:
                    snap = frame.copy()
                    frame_size = (frame.shape[1], frame.shape[0])
                    draw()
            if paused and handle_edit_keys(k, args.out, target_size=target_size):
                break

        cap.release()
        cv2.destroyAllWindows()
        return

def handle_edit_keys(k: int, outpath: str, target_size=None) -> bool:
    """Return True to exit the edit loop."""
    if k in (10, 13):       # Enter
        commit_roi()
    elif k == ord('u') and current:
        current.pop(); draw()
    elif k == ord('z') and zones:
        zones.pop(); draw()
    elif k == ord('s'):
        save_zones(outpath, target_size=target_size)   # <-- apply scaling here when requested
    return False

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[error] {exc}")
