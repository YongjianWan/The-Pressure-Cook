# Project Wiki Home

- [User Flow & Task Structure (EN)](User-Flow-and-Task-Structure.en)
- [Core Logic & Implementation (EN)](Core-Logic-and-Implementation.en)

> Non-conflict rule: **only the Hub (`ledstrip_countdown.py`) opens the Arduino serial port**; the camera `camera.py` publishes events to the Hub over UDP (127.0.0.1:8787).



# Fruit Salad Collaboration System (Mac / Windows Compatible)

Single board (UNO R3 compatible) + LED strip (white-light rhythms) + camera marker tracking (ArUco) + sound level gating.  
Non-conflict principle: only the Hub (ledstrip_countdown.py / launched via run_hub.py) opens the Arduino serial port; every other program (camera, etc.) stays off Serial and sends events to the Hub through UDP (127.0.0.1:8787).

## Table of Contents
- Hardware requirements & wiring (single board)
- Installation (Arduino / Python)
- Project structure & file overview
- Configure markers & ROI (allow.json / zones.json)
- Launch steps (non-conflict mode | interactive port picker)
- Quick acceptance test (5 minutes)
- Troubleshooting
- Event reference (PC ↔ Arduino)

## 1) Hardware Requirements & Wiring (Single Board)

- Arduino UNO R3-compatible board ×1 (Little Bird)
- LED strip (pick one)
  - NeoPixel (WS2812B / SK6812, 5V): D6 → Data (with 330 Ω in series), 5V, GND (share ground with Arduino)
  - 12V single-color strip + N-channel MOSFET: D6 → 1 kΩ → Gate; LED(+) → 12V; LED(−) → Drain; Source → GND; share ground between 12V supply and Arduino
- Buzzer: D8 → +, GND → −
- (Optional) RFID MFRC522: SDA/SS = D10, SCK = D13, MOSI = D11, MISO = D12, RST = D9, 3.3V/GND
- (Optional) Microphone module: AO → A0 (5V/GND)
- USB camera: plug into the computer (macOS / Windows)
- A single Arduino handles LED/buzzer (display layer); if you integrate RFID/microphone they can run on the same board. The camera is USB to the computer.

## 2) Installation (Arduino / Python)

### 2.1 Arduino

- Install Arduino IDE: https://www.arduino.cc/en/software
- Board: Arduino/Genuino Uno
- Port:
  - macOS: /dev/cu.usbmodemXXXX (or /dev/cu.usbserial…)
  - Windows: COMx (CH340 clones need the CH340 driver first)
- Upload `arduino/ledstrip.ino`
- Default NeoPixel: data pin D6, `DEFAULT_PIX = 30`
- For 12V strip: set `#define USE_NEOPIXEL 1` to `0` (D6 drives PWM → MOSFET)

### 2.2 Python (macOS / Windows)

```bash
cd ANN_0910/mac
# macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
# py -3.11 -m venv .venv
# . .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install opencv-contrib-python pyserial numpy
# Windows needs the TTS package
# python -m pip install pyttsx3
```

TTS: macOS uses the built-in `say`; Windows uses `pyttsx3` (SAPI).

## 3) Project Structure & Files

```
0910/
├─ arduino/
│  └─ ledstrip.ino            # LED/buzzer switch-case (white-light rhythms; works for NeoPixel/12V)
├─ mac/
│  ├─ camera.py               # ArUco + multi-ROI + debouncing → UDP events (no Serial)
│  ├─ camera_works_fam.py     # Viewer (draws ROI & marker IDs; no events)
│  ├─ ledstrip_countdown.py   # Hub: only Serial client + TTS + 70 s rounds + UDP hub (interactive port picker)
│  ├─ run_hub.py              # One-click Hub launcher (interactive by default; supports --port / --no-timer)
│  ├─ roi_calibrator.py       # Mouse annotation → zones.json
│  ├─ allow.json              # Marker ID → allowed zones (TRAY / PLATE / P1 / P2 / P3 …)
│  └─ zones.json              # ROI polygons (TABLE / TRAY / PLATE …)
└─ mac/tools/
   ├─ detect_dict.py          # Detect marker dictionaries (4x4_50 / 5x5_100 / 6x6_250)
   └─ scale_zones.py          # Scale zones.json proportionally when resolution changes
```

`camera.py` reads `allow.json` (ID → allowed zones) and `zones.json` (ROI polygons), evaluates TABLE → SECTION each frame, and sends `HARD_OUT` / `MESSY_ON` / `MESSY_OFF` to the Hub via UDP after debouncing.  
`ledstrip_countdown.py` is the sole Serial gateway: it handles TTS, 70 s rounds, UDP aggregation, and voice arbitration, then forwards events to Arduino (LED/buzzer patterns).

## 4) Configure Markers & ROI (allow.json / zones.json)

### 4.1 Confirm marker dictionary

```bash
cd ANN_0910/mac/tools
python detect_dict.py
```

Hold any marker at the camera; the top-left overlay shows: Dict (4x4_50 / 5x5_100 / 6x6_250) and ID: xx.  
If you see 4x4_50, change `DICT = aruco.DICT_5X5_100` in `mac/camera.py` to `aruco.DICT_4X4_50`.

### 4.2 Capture marker IDs and fill allow.json

```bash
cd ANN_0910/mac
python camera_works_fam.py
```

The window draws polygons and red IDs; map each object → ID and fill `allow.json` (zone names must match `zones.json` exactly):

```json
{
  "10": ["TRAY"],
  "11": ["TRAY"],
  "20": ["PLATE"],
  "21": ["PLATE"],
  "30": ["TRAY", "PLATE"],
  "31": ["TRAY", "PLATE"],
  "32": ["TRAY"],
  "33": ["TRAY"],
  "40": ["P2"],
  "50": ["P3", "TRAY"]
}
```

### 4.3 Produce / adjust zones.json

- Re-annotate (most reliable)

  ```bash
  python roi_calibrator.py      # Left click to place vertices, right click / Enter to finish and name (TABLE / TRAY / PLATE …)
  python camera_works_fam.py    # Check ROI outlines and IDs
  ```

- Scale proportionally (when resolution changes)

  ```bash
  cd ANN_0910/mac/tools
  python scale_zones.py ../zones.json 1280 720 1920 1080 > ../zones.json
  ```

1280 720 = old width & height; 1920 1080 = new width & height. The script scales every vertex proportionally.

## 5) Launch Steps (Non-conflict Mode | Interactive Port Picker)

Principle: only the Hub (`ledstrip_countdown.py`) opens the Arduino serial port; `camera.py` avoids Serial and publishes UDP events (`HARD_OUT` / `MESSY_*` / `NOISY_*` / `QUIET_ON` / `ALARM_*`).

- Window A: Hub (TTS + 70 s rounds + UDP aggregation | interactive port picker)

  ```bash
  cd ANN_0910/mac
  # Activate virtualenv (macOS: source .venv/bin/activate; Windows: .\.venv\Scripts\Activate.ps1)
  python run_hub.py
  # Lists /dev/cu.usbmodem* / usbserial* (mac) or COMx (Windows)
  # Type the index; press Enter to pick 0
  ```

  Parameters:
  - `--port COM6` or `--port /dev/cu.usbmodem1101`: skip interaction and pin the port
  - `--no-timer`: disable the 70 s timer and use it as a pure TTS / event hub

- Window B: Camera (ArUco → UDP)

  ```bash
  cd ANN_0910/mac
  python camera.py
  ```

Do **not** start any other script that opens the same Serial port (e.g. legacy `arduino_led_beep.py`).

## 6) Quick Acceptance Test (5 Minutes)

- 55 s → TTS counts 5→1 (1 beat per second), LED flashes twice, buzzer beeps twice
- 60 s → TTS “Now”, LED lights for 800 ms, buzzer long beep; swap roles within ≤10 s
- Messy: move any marked bowl out of allowed area ≥1 s → TTS prompt + LED triple flash; return for ~0.8 s → LED off (silent)
- Hard Out: move object outside TABLE ≥0.5 s → TTS “Object left the work area” + fast double flash
- Noisy: shout ≥1 s → TTS noise call + LED 0.5 s pulse (normal speech should not trigger)
- Finish: done → round-specific voice line + LED/buzzer three-stage celebration

## 7) Troubleshooting

- Camera cannot detect markers / IDs flicker
  - Check the dictionary (tools/detect_dict.py) matches the print (4x4_50 / 5x5_100 / 6x6_250)
  - Resolution 1280×720; even lighting; marker edge length ≥40–60 px
  - Print matte stickers and keep ≥5 mm white border (quiet zone) to avoid glare
- Messy false positives / stays alert after returning
  - Expand ROI polygons by +10–20 px on each edge
  - Debounce thresholds: leave ≥1.2 s, return 0.8 s
  - Zone names in allow.json must match zones.json exactly (case-sensitive)
  - Treat points on the boundary as inside
- No audio or LED does not light
  - Verify the Hub picked the correct Serial port (interactive or `--port`)
  - Ensure only the Hub opens Serial; close any other Python using the port
  - Confirm `ledstrip.ino` uploaded and LED strip configuration matches constants (NeoPixel / 12V)
- UDP no response
  - Allow Python through the firewall (Windows prompts on first run)
  - Both Hub and camera.py must target localhost 127.0.0.1:8787
  - Event strings should be `HARD_OUT` / `MESSY_ON` / `MESSY_OFF` / `NOISY_ON` / `NOISY_OFF` / `QUIET_ON` / `ALARM_WARNING` / `ALARM_ON`

## 8) Event Reference (PC ↔ Arduino)

```
+--------+---------------+-------------------------------------------------------+-------------------------------+-------------+
| Type   | Event         | TTS (Voice)                                           | LED (white light)             | Buzzer      |
+--------+---------------+-------------------------------------------------------+-------------------------------+-------------+
| Task   | ALARM_WARNING | Switching tasks soon + 5 → 1                          | Flash twice (150/150 ×2)      | Short ×2    |
| Task   | ALARM_ON      | Switch tasks now                                      | On 800 ms                     | Long        |
| Camera | HARD_OUT      | Object left the work area                             | Fast flash twice (100/100 ×2) | Short ×2    |
| Camera | MESSY_ON      | Please return items to the shared tray or final plate | Flash 3× (120/120 ×3)         | Short ×2    |
| Camera | MESSY_OFF     | (silent)                                              | Off                           | (silent)    |
| Sound  | NOISY_ON      | Too noisy… pause and take turns                       | Pulse once (500 ms)           | Optional    |
| Sound  | NOISY_OFF     | (silent)                                              | Off                           | (silent)    |
| Sound  | QUIET_ON      | Too quiet, say the next step together                 | Light flash (150 ms)          | (silent)    |
| Task   | END           | Task finished! (round-based remark)                   | Three-stage pulse             | Three-stage |
+--------+---------------+-------------------------------------------------------+-------------------------------+-------------+

+----------------------------------------------------+--------------------------------------------------------------------+
| Voice priority order                               | Notes                                                              |
+----------------------------------------------------+--------------------------------------------------------------------+
| NOISY_ON > HARD_OUT > MESSY_ON > QUIET_ON > NORMAL | Task ALARM_WARNING / ALARM_ON follow schedule; when overlapping    |
|                                                    | NOISY_ON, the voice may delay, but LED/buzzer still follow their   |
|                                                    | atterns.                                                           |
+----------------------------------------------------+--------------------------------------------------------------------+
```
