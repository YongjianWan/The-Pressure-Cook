# Sound Detection Alarm (Python-only)
Monitors room loudness from an audio interface mic and plays an alarm on laptop speakers.

# Setup

```bash
cd Stir-Wars/Sound Detection/sound_detection
python -m venv .venv && source .venv/bin/activate  
# Windows: venv\Scripts\activate. 
# Essentially create your own virtual environment. Replace .venv with your preferred environment name
# then activate the virtual environment with source .venv/bin/activate as you see above. Again remember to replace .venv with your name.
pip install -r requirements.txt
```

## ------- Starting Here for Camera

# Utensil Monitor

A camera-based, ArUco-driven workstation assistant. It watches whether each utensil (with a marker) stays inside its assigned **polygonal ROI**, speaks prompts via **macOS TTS**, and controls **Arduino LEDs** for visual cues. It also runs a periodic **“Switch tasks”** prompt with a short countdown.

## Features

- **Markers:** ArUco `DICT_4X4_50`, **IDs 1, 2, 3 → station1/2/3**  
- **ROIs:** Polygon regions from `zones.json` (`STATION1/2/3`); fall back to rectangles if missing  
- **Voice (macOS):** background TTS via `say -v Samantha -r 190`  
- **Arduino LEDs:** green default; red/blue/yellow/pink blink for events  
- **Task switch:** every round (e.g., 45 s) → “Switching tasks soon” → “Switch tasks now” + blue blink  
- **Marker sheets:** A4 **duplex** PDF with **identical front/back** and mm-level back-page offset compensation

---

## Requirements

- **OS:** macOS (uses the built-in `say` TTS)  
- **Python:** 3.9+ (virtual env recommended)  
- **Camera:** built-in or USB webcam  
- **Arduino:** connected via USB serial

**Python packages**
```txt
opencv-contrib-python>=4.8
numpy>=1.24
pyserial>=3.5
reportlab>=4.0   # only for the PDF marker generator
```

---

## Quick Start

```bash
# 1) Create & activate venv
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\activate
python -m pip install --upgrade pip

# 2) Install deps (or use requirements.txt)
python -m pip install opencv-contrib-python numpy pyserial reportlab
# python -m pip install -r requirements.txt

# 3) Generate duplex A4 markers (IDs 1/2/3 @ 50 mm)
python make_aruco_duplex.py
# Print A4, 100% (Actual Size), Duplex Long-edge, no auto-scale/auto-rotate.

# 4) Calibrate polygon ROIs (label them STATION1/2/3)
python roi_calibrator.py --live --cam 0 --out config/zones.json --set-size 1920x1080
# (Or from a photo: --img table.jpg --set-size 1920x1080)
# Using --set-size fixes the JSON coordinates and frame_size so runtime matches calibration.

# 5) Run the app (pick serial automatically, or pass --port)
python merged_code_cam.py              # auto-picks first /dev/cu.*
# or
python merged_code_cam.py --port /dev/cu.usbmodem31101

# Optional: adjust speaking rate (150–210 typical)
python merged_code_cam.py --rate 180
```

Press `q` to quit the app window.

---

## ArUco Marker Printing

- Use `make_aruco_duplex.py` to create an A4 **two-page** PDF where **both pages are identical**.  
- Printing tips: **A4**, **100%/Actual Size**, **Duplex Long-edge**, **no scaling/auto-rotate**.  
- If back/front don’t align perfectly, tweak the script’s back-page offsets:
  ```python
  BACK_ROTATE_180 = False   # Long-edge duplex → keep False
  BACK_OFFSET_MM_X = 1.0    # move back page right (+) / left (-)
  BACK_OFFSET_MM_Y = 2.0    # move back page up (+) / down (-)
  ```
- PNG-only? Use `make_aruco_pngs.py`.

**Size guidance:** 30–50 mm per side is robust. 20 mm is marginal; 10 mm is generally too small unless the marker covers ≥60 px per side in the live image.

---

## ROI Annotation (polygons)

Use `roi_calibrator.py` to draw **STATION1/2/3** polygons and save JSON with a fixed `frame_size`:

```bash
python roi_calibrator.py --live --cam 0 --out config/zones.json --set-size 1920x1080
```

**`zones.json` structure**
```json
{
  "frame_size": { "width": 1920, "height": 1080 },
  "zones": [
    { "name": "STATION1", "pts": [[x,y], ...] },
    { "name": "STATION2", "pts": [[x,y], ...] },
    { "name": "STATION3", "pts": [[x,y], ...] }
  ]
}
```

The runtime loads `./zones.json` or `./config/zones.json` and uses polygons first; it falls back to rectangles only if a station polygon is missing.

---

## CLI Options (main app)

| Option            | Default        | Description                                      |
|-------------------|----------------|--------------------------------------------------|
| `--port`          | auto-pick      | Serial device (e.g., `/dev/cu.usbmodem31101`)   |
| `--rate`          | `190`          | Speaking rate (wpm), typically 150–210          |

> Voice is fixed to **Samantha** in the current build.

---

## Simulator Keys (in terminal)

- `1` → “Counter too messy” (red blink)  
- `2` → “Volume is too loud. Calm down” (yellow blink)  
- `3` → “Too quiet. Not enough socialising” (yellow blink)  
- `4` → “Please follow the recipe carefully” (pink blink)

The system also announces **marker OUT** and runs periodic **task switch** countdowns (blue blink).

---

## Troubleshooting

**Serial: `SerialException: could not open port`**  
- Check device: `python -m serial.tools.list_ports -v`  
- Close Arduino Serial Monitor; unplug/replug; try another cable/adapter  
- Run with an explicit port:  
  ```bash
  python merged_code_cam.py --port /dev/cu.usbmodem31101
  ```

**Marker not detected**  
- Must be `DICT_4X4_50`, IDs **1/2/3**  
- Print 100% with **quiet zone** intact; matte paper; avoid reflections  
- Ensure the marker covers ≥**60 px per side** in the live image (≥100 px is rock-solid)  
- Increase camera resolution or move closer

**ROI mismatch**  
- Ensure `frame_size` in `zones.json` matches the runtime image size/orientation  
- Best: annotate with `--set-size 1920x1080`, and run/resize the camera to the same size  
- Names must be exactly `STATION1/2/3`

**TTS sounds bad/no voice**  
- Test: `say -v Samantha "Hi, I'm Samantha."`  
- (Optional) Download **Samantha (Enhanced)** in macOS Settings → Accessibility → Spoken Content → Manage Voices…  
- Adjust with `--rate 150–210`

**Duplex front/back misalignment**  
- Long-edge duplex → `BACK_ROTATE_180 = False`  
- Tune `BACK_OFFSET_MM_X/Y` by ±0.5–2.0 mm until the crop marks line up

---

## Project Structure

```
.
├─ merged_code_cam.py          # main runtime (ArUco, polygon ROIs, TTS, Arduino LEDs)
├─ roi_calibrator.py           # draw polygon ROIs and save zones.json
├─ make_aruco_duplex.py        # generate PNG markers (IDs 1/2/3) and A4 duplex PDF (identical front/back) + mm offsets
├─ config/
│  └─ zones.json               # recommended location for ROI polygons
└─ requirements.txt
```

---

## License

For coursework/internal use. If you plan to redistribute, add a license and check third-party dependencies.
