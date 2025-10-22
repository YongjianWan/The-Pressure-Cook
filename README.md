# The-Pressure-Cook

Interactive cooking timer using computer vision (ArUco markers) and audio detection.

##  Critical Limitations

**Platform**: macOS ONLY (serial ports hardcoded)  
**Calibration**: REQUIRED before every session (config not persistent)  
**Status**: Demo build for course presentation  

### Why Manual Calibration Every Time?
1. **Audio thresholds** vary by room noise and microphone position
2. **Camera zones** change if camera angle/distance shifts  
3. **Configuration not saved** - thresholds hardcoded after calibration

This design prioritized demo reliability over production usability.

---

## Quick Start

### Prerequisites
- **macOS** (serial communication Mac-only)
- Python 3.11+
- Arduino Uno/Nano + WS2812B LED strip
- USB camera (tested: Logitech C920, built-in MacBook cam)
- USB microphone (tested: Blue Yeti, M-Audio FastTrack)

### Installation
```bash
cd Development/final-working-code
pip install -r requirements.txt
```

**Expected dependencies** (if `requirements.txt` missing):
```bash
pip install opencv-python opencv-contrib-python numpy pyserial sounddevice
```

### Hardware Setup
1. Connect Arduino via USB
2. Upload `merged-arduino/merged-arduino.ino` via Arduino IDE
3. **Important**: Check serial port with `ls /dev/tty.*` and update line 47 in main script

### Arduino Firmware Details

**File**: `merged-arduino/merged-arduino.ino`

**Hardware Requirements**:
- Arduino Uno/Nano (tested on Uno)
- WS2812B LED strip (30 pixels) connected to **pin D6**
- 5V power supply for LED strip (USB power may be insufficient for full brightness)

**Serial Communication**:
- Baud rate: **9600**
- Protocol: Newline-terminated commands
- Supported commands:
  - `DEFAULT_GREEN` - Steady green (system ready)
  - `SWITCH_TASK` - Blue blink (task rotation prompt)
  - `ALARM_ON` - Red blink (noise/violation alert)
  - `YELLOW_BLINK` - Yellow blink (marker out of zone)
  - `PINK_BLINK` - Pink blink (reserved)
  - `OFF` - Turn off LEDs

**LED Behavior**:
- Non-blocking state machine (no `delay()` calls)
- Blink rates: 200-400ms per color (tuned for visibility)

**⚠️ Hardcoded Values**:
- LED count: 30 (change `NUMPIXELS` if using different strip)
- Pin: D6 (change `PIN` if wiring differs)
- Serial baud: 9600 (must match Python script line 47)

---

## Running (3-Step Calibration Process)

### Step 1: Audio Calibration (REQUIRED)
```bash
# List audio devices
python sound-calibrate.py --help

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

**⚠️ Manual Step**: Copy these numbers into `no-quiet-only-loud-merged.py` lines 89-91  
**Why not auto-save?** Time constraints during development (see Known Issues).

### Step 2: Camera Zone Calibration (REQUIRED if camera moved)
```bash
# Live camera mode (pause with SPACE, then draw zones)
python camera_calibrator.py --live --cam 0 --out config/zones.json

# Or use a static photo first
python camera_calibrator.py --cam 0 --out config/zones.json
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
python no-quiet-only-loud-merged.py
```

**Expected behavior**:
- LED strip shows system status
- Audio triggers voice prompts when noise exceeds threshold
- Camera tracks ArUco markers (IDs 10-50) across defined zones

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
- Windows users: Must manually find port (`COM3`, `COM4`, etc.) and update code
- No auto-detection implemented

### Configuration Management (Design Flaw)
- **Audio thresholds**: Must copy-paste from calibrator output into code (lines 89-91)
- **Camera zones**: Saved to JSON but path may be wrong (`config/zones.json` vs. `zones.json`)
- **No validation**: Program silently uses wrong thresholds if calibration skipped

### Calibration Workflow Issues
- **Room-specific**: Audio calibration invalid if demo moved to different room
- **Camera-specific**: Zone calibration invalid if camera moved/rotated
- **No persistence**: Closing program = lose all runtime adjustments

### Code Quality
- Magic numbers in multiple files (delays, LED colors, timeout values)
- Error handling incomplete (device disconnect = crash)
- No logging system

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

## Documentation

- [WIKI.md](WIKI.md) - System architecture, calibration internals, development history
- [User-Flow-and-Task-Structure.en.md](docs/User-Flow-and-Task-Structure.en.md) - Game rules for demo
- [Core-Logic-and-Implementation.en.md](docs/Core-Logic-and-Implementation.en.md) - Technical design (may be outdated)

---

## Development Notes

This is a **course project** with acknowledged technical debt:

**Time Constraints Led To**:
- Manual calibration instead of persistent config
- Platform-specific code (macOS serial paths)
- Config scattered across files (JSON + hardcoded values)

**What Should Be Fixed For Production**:
1. **Persistent calibration** - Save thresholds to `config.json`, load on startup
2. **Cross-platform serial** - Use `pyserial.tools.list_ports` auto-detection
3. **Unified config** - Single source of truth for all parameters
4. **Error recovery** - Handle device disconnect gracefully

**Estimated refactoring time**: 2-3 weeks for one developer.

---

## Credits

**Calibration Tools**: camera_calibrator.py, sound-calibrate.py  
**Hardware Integration**: Arduino firmware  
**Computer Vision**: OpenCV ArUco module  
**Audio Detection**: sounddevice library  

---

*This was a functional prototype for academic demonstration.  
Production use would require significant architectural changes.*
