# The-Pressure-Cook

##  Critical Limitations

**Platform**: macOS ONLY (serial ports hardcoded)  
**Calibration**: REQUIRED before every session (config not persistent)  

---

## Quick Start

### Prerequisites
- **macOS** (serial communication Mac-only)
- Python 3.11+
- Arduino Uno/Nano + WS2812B LED strip
- iPhone camera
- Microphone and speakers

### Installation
```bash
cd Development/final-with-timer-21oct
```
```bash
pip install opencv-python opencv-contrib-python numpy pyserial sounddevice
```

### Hardware Setup
1. Connect Arduino via USB
2. Upload `merged-arduino/merged-arduino.ino` via Arduino IDE
3. **Important**: Check serial port with `ls /dev/tty.*` and update line 47 in main script


**Hardware Requirements**:
- Arduino Uno/Nano (tested on Uno)
- WS2812B LED strip connected to **pin D6**
- 5V power supply for LED strip (USB power may be insufficient for full brightness)

**Serial Communication**:
- Baud rate: **9600**
- Protocol: Newline-terminated commands
- Supported commands:
  - `DEFAULT_GREEN` - Steady green (system ready)
  - `SWITCH_TASK` - Blue blink (task rotation prompt)
  - `ALARM_ON` - Red blink (counter too messy)
  - `YELLOW_BLINK` - Yellow blink (noise alert)
  - `PINK_BLINK` - Pink blink (follow recipe)
  - `WHITE_BLINK` - White blink (timer up)
  - `OFF` - Turn off LEDs

---

## Running (3-Step Calibration Process)

### Step 1: Audio Calibration (REQUIRED)
```bash
# Example: calibrate input device 2 for 20 seconds
python sound-calibrate.py --in 2 --sr 44100 --seconds 20 --hp 100
```

**Output** (example):
```
Room dB (HPF 100 Hz): avg=-42.3 dBFS, p95=-38.1 dBFS
Suggested thresholds:
  trigger ~ -32.1 dBFS  (when to start alarm)
  release ~ -36.1 dBFS  (when to stop alarm)
```

### Step 2: Camera Zone Calibration
```bash
# Live camera mode (pause with SPACE, then draw zones)
python camera_calibrator.py
```

**Instructions**:
1. Press SPACE to pause live feed
2. Left-click to draw polygon points around each zone (TABLE, TRAY, PLATE)
3. Right-click or Enter to finish one zone (system prompts for name)
4. Press 'S' to save, ESC to quit

**Output**: `config/zones.json` with pixel coordinates  
** Camera-specific**: Recalibrate if camera position/angle changes

### Step 3: Run Main Program
```bash
python time-up-merged.py --trig-db -17.4 --rel-db -21.4 --print-audio
```

---

## Project Structure
```
Development/
├── final-working-code/              # Current working version
│   ├── no-quiet-only-loud-merged.py # Main application (Mac-only)
│   ├── merged-arduino/              # Arduino firmware (LED control)
│   │   └── merged-arduino.ino
│   ├── sound-calibrate.py           # Audio threshold calibration
│   └── camera_calibrator.py         # Zone boundary setup (ROI tool)
│
├── code-archive/                    # Historical code (DO NOT USE)
│   ├── 1510_merged_code_simulation/ # Early multi-sensor prototype
│   ├── Sound Detection/             # Standalone audio detection
│   ├── anya_sammy work/             # Experimental branches
│   └── ...                          # Multiple parallel attempts
│
└── config/
    └── zones.json                   # Camera zone definitions (output of calibrator)
```

---

## Known Issues

### Platform Dependency (Showstopper)
- **Serial ports hardcoded** (`/dev/tty.usbserial-*` in main script)
- Only works on MacOS

### Calibration Workflow Issues
- **Room-specific**: Audio calibration invalid if demo moved to different room
- **Camera-specific**: Zone calibration invalid if camera moved/rotated
- **No persistence**: Closing program = lose all runtime adjustments

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Serial port not found` | Check `ls /dev/tty.*` and update line 47 in `no-quiet-only-loud-merged.py` |
| `Camera not detecting markers` | Recalibrate with `camera_calibrator.py`; check lighting/marker size |
| `Audio triggers constantly` | Re-run `sound-calibrate.py` in actual demo room; update thresholds in code |
| `LED strip not responding` | Verify Arduino upload; check USB connection; try different serial port |
| `ImportError: cv2` | `pip install opencv-python opencv-contrib-python` |
| `Zones in wrong places` | Delete old `zones.json`; recalibrate with current camera setup |

---

*This was a functional prototype for academic demonstration.  
Production use would require significant architectural changes.*
