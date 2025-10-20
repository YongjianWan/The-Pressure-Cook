# Core Logic & Implementation (English)

> Translate the user flow into actionable, maintainable **technical specifications**.  
> Highlights: **Single board (UNO R3)**, **LED white-light rhythms**, **Camera ArUco + ROI**, **Sound level thresholds**, **Cross-platform Hub (Mac/Win)**, **No-conflict start-up**, **Hub variant (first 3 rounds 10 s, later 5 s)**.

---

## 0. Architecture

- **Hub / Event Center (`ledstrip_countdown.py`)**
  - Only process that opens the Arduino Serial port (9600 bps)
  - Aggregates UDP events from camera nodes (`127.0.0.1:8787`) and forwards structured commands to Arduino
  - Provides cross-platform TTS (macOS `say`, Windows `pyttsx3`) and 70 s round timer with event arbitration

- **Camera Node (`camera.py`)**
  - Tracks ArUco markers inside predefined ROIs (TABLE → SECTION)
  - Debounces Messy / Hard Out transitions and emits UDP events to the Hub
  - Runs entirely on the PC (no Serial usage) so multiple sensors avoid port conflicts

- **Arduino Display Layer (`ledstrip.ino`)**
  - Receives event strings from the Hub over Serial and drives LED/buzzer rhythms
  - Reports physical interactions back to the Hub (RFID `START` / `FINISH`, microphone noise states)
  - Supports both NeoPixel and 12 V single-color strips from the same firmware

**Signal Flow**

| Source | Transport | Destination | Purpose |
| --- | --- | --- | --- |
| `camera.py` | UDP 127.0.0.1:8787 | Hub | `HARD_OUT`, `MESSY_ON/OFF` events |
| Hub | Serial 9600 | Arduino | LED/buzzer commands (`ALARM_*`, `NOISY_*`, …) |
| Arduino | Serial 9600 | Hub | RFID + microphone events (`START`, `FINISH`, `NOISY_ON/OFF`, `QUIET_ON`) |

- **Sole Serial connection**: Hub (prevents conflicts)
- **Camera**: sends **UDP** events to the Hub only
- **Arduino**: display layer (LED / buzzer) and reports RFID / microphone events back to the Hub

---

## 1. Event Bus

### 1.1 PC → Arduino (display layer)
`ALARM_WARNING`, `ALARM_ON`, `HARD_OUT`, `MESSY_ON`, `MESSY_OFF`, `NOISY_ON`, `NOISY_OFF`, `QUIET_ON`, `END`, `RESET`

> LED / buzzer (white-light rhythms, no color semantics):  
> - `ALARM_WARNING`: flash twice (150 / 150), short beep ×2  
> - `ALARM_ON`: on 800 ms, long beep  
> - `HARD_OUT`: quick flash twice (100 / 100), short beep ×2  
> - `MESSY_ON`: flash three times (120 / 120), short beep ×2  
> - `MESSY_OFF`: turn off  
> - `NOISY_ON`: 500 ms pulse (buzzer optional)  
> - `QUIET_ON`: 150 ms pulse  
> - `END`: three-stage celebration

### 1.2 Arduino → PC (report)
`START`, `FINISH`, `NOISY_ON`, `NOISY_OFF`, `QUIET_ON`

### 1.3 Camera → Hub (UDP 127.0.0.1:8787)
`HARD_OUT`, `MESSY_ON`, `MESSY_OFF`

---

## 2. Hub (`ledstrip_countdown.py`)

### 2.1 Responsibilities
- **Only opens Serial**, handles **TTS**, **70 s timer** (Soon / 5→1 / Now), **UDP aggregation**
- **Voice priority**: `NOISY_ON > HARD_OUT > MESSY_ON > QUIET_ON > NORMAL`
  - **HARD_OUT never delayed** (even if `NOISY_ON`)
  - Task `ALARM_*` follow schedule; when overlapping with noise, the **voice can wait** but **events still forward** (LED / buzzer keep rhythm)

### 2.2 Variant: first 3 rounds 10 s, afterwards 5 s
- Hub keeps `CYCLE = 70`, `SWITCH = 60`
- **Rounds 0–2**: `WARN_AT = 50` (10 s prep)
- **Rounds ≥3**: `WARN_AT = 55` (5 s prep)
- In `tick_timer()` select `warn_at` by `self.round_idx`; after sending `ALARM_ON`, do `self.round_idx += 1`; on `START`, reset `self.round_idx = 0`.

**Sample implementation**

```python
# __init__
self.round_idx = 0  # rounds 0,1,2 use the 10-second prep window

# handle()
if msg == "START":
    self.round_idx = 0
    return

# tick_timer()
warn_at = 50.0 if self.round_idx < 3 else 55.0
...
if abs(t - warn_at) < 0.12 and now_i != self._last_warn:
    self.enqueue("ALARM_WARNING")
    self._last_warn = now_i
if abs(t - SWITCH) < 0.12 and now_i != self._last_on:
    self.enqueue("ALARM_ON")
    self._last_on = now_i
    self.round_idx += 1
```

---

## 3. Camera (`camera.py`)

### 3.1 Logic (TABLE → SECTION, debounce, missing timeout)
- **TABLE (safety)**: outside TABLE continuously ≥0.3–0.5 s → `HARD_OUT`
- **SECTION (order)**: inside any allowed zone → compliant; if previously Messy, continuous ≥0.8 s → `MESSY_OFF`
- **All zones missed**: continuous ≥1.0 s → `MESSY_ON`
- **Occlusion ignore**: `MISS_HIDE = 0.5 s`
- **Missing timeout**: `MISSING_KILL = 5 s` → auto-clear states (send `MESSY_OFF` first if currently Messy to avoid stale state)

### 3.2 Configuration (JSON)
- `zones.json`: TABLE / TRAY / PLATE … polygons (pixel coordinates; expand each edge by +10–20 px; use `scale_zones.py` to scale or `roi_calibrator.py` to re-label after resolution changes)
- `allow.json`: marker ID → list of allowed zone names (names must match `zones.json`)

### 3.3 Camera backends (cross-platform)
- mac/Linux: `cv2.VideoCapture(0)`
- Windows: `cv2.VideoCapture(0, cv2.CAP_DSHOW)`
- Resolution: 1280×720 @ 30 fps

---

## 4. Arduino (`ledstrip.ino`)

### 4.1 LED display layer (white-light rhythms)
- `USE_NEOPIXEL = 1`: NeoPixel (WS2812B / SK6812, data on D6)
- `USE_NEOPIXEL = 0`: 12V single-color strip (D6 PWM → MOSFET)
- `DEFAULT_PIX`: number of pixels on strip (e.g., 30)

### 4.2 RFID (START / FINISH)
- MFRC522 (SDA/SS = D10, SCK = D13, MOSI = D11, MISO = D12, RST = D9, 3.3V/GND)
- `UID_START_P3[]` / `UID_FINISH_P1[]` (fill with actual UIDs)

### 4.3 Microphone dB (NOISY / QUIET)
- Sample window: `MIC_N = 512`, `MIC_US = 80` (~40–50 ms)
- Thresholds / debounce: `NOISY_DB = 72.0`, `NOISY_ON_MS = 400`, `NOISY_OFF_MS = 600`, `QUIET_DB = 42.0`, `QUIET_WIN_MS = 25000`
- Report events: `NOISY_ON` / `NOISY_OFF` / `QUIET_ON`

### 4.4 Display-layer switch-case
- Follow the “Event Bus” table for LED / buzzer behaviors; white-light patterns only (no color semantics)

---

## 5. JSON Interfaces

### 5.1 `zones.json` (example)

```json
[
  {"name": "TABLE", "pts": [[60, 60], [1220, 60], [1220, 660], [60, 660]]},
  {"name": "TRAY",  "pts": [[420, 360], [720, 360], [720, 560], [420, 560]]},
  {"name": "PLATE", "pts": [[820, 380], [1100, 380], [1100, 580], [820, 580]]},
  {"name": "P2",    "pts": [[260, 380], [400, 380], [400, 560], [260, 560]]},
  {"name": "P3",    "pts": [[1120, 380], [1210, 380], [1210, 560], [1120, 560]]}
]
```

### 5.2 `allow.json` (example)

```json
{
  "10": ["TRAY"],         "11": ["TRAY"],
  "20": ["PLATE"],        "21": ["PLATE"],
  "30": ["TRAY", "PLATE"],"31": ["TRAY", "PLATE"],
  "32": ["TRAY"],         "33": ["TRAY"],
  "40": ["P2"],           "50": ["P3", "TRAY"]
}
```

---

## 6. Cross-platform Differences (built-in)

| Item | macOS | Windows |
| --- | --- | --- |
| TTS | `say` | `pyttsx3` (SAPI) |
| Camera backend | default | `cv2.CAP_DSHOW` |
| Serial port | `/dev/cu.usbmodem*` / `usbserial*` | `COMx` |
| Launch Hub | `python mac/run_hub.py` (interactive port picker; supports `--port` / `--no-timer`) | same command |

---

## 7. Acceptance Checklist (incl. Hub variant)
- **Round rhythm**: first 3 rounds `WARN_AT = 50` (10 s prep), then `WARN_AT = 55` (5 s prep); switch at 60 s; handoff ≤10 s
- **HARD_OUT never delayed**: during `NOISY_ON`, if outside TABLE ≥0.5 s play voice immediately
- **Missing Kill 5 s**: marker missing >5 s auto clears state (if Messy, send `MESSY_OFF` first to avoid leftovers)
- **RFID reporting**: P3 = START, P1 = FINISH
- **NOISY / QUIET**: ≥1 s loud ⇒ `NOISY_ON`; ~0.6 s quiet ⇒ `NOISY_OFF`; 25–30 s quiet ⇒ `QUIET_ON`
- **LED / buzzer**: white-light rhythms match the event table

---

## 8. Troubleshoot
- **Serial conflicts**: only the Hub opens Serial; camera uses UDP
- **Camera misses markers**: check dictionary `detect_dict.py`; resolution 1280×720; even lighting; marker edge length ≥40–60 px
- **Messy false alarms**: expand ROI edges by +10–20 px; `MESSY_ON_S = 1.2`; return 0.8; treat boundary as inside
- **Noise thresholds**: adjust `NOISY_DB` / `QUIET_DB`; tweak debounce values to fit the venue
- **ROI mismatch**: use `roi_calibrator.py` to re-label or `scale_zones.py` for proportional scaling
