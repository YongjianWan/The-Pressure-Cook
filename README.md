# The-Pressure-Cook

The Pressure Cook connects Python (for sound and vision processing) with Arduino hardware to give real-time LED feedback based on user actions and environmental conditions.  
It was developed as part of a university project exploring ambient computing in shared kitchen environments.

---
## Documentation
For detailed concept, testing insights, and research notes, visit our [Project Wiki](https://github.com/YongjianWan/The-Pressure-Cook/wiki).

---

## Features
- Real-time camera tracking with ArUco markers  
- Audio monitoring for noise thresholds and ambient conditions  
- LED feedback for visual prompts (cleanliness, timing, and noise alerts)  
- Calibration system for adaptable performance across environments  
- Fallback Python simulations in case of hardware or communication failure  

---

## Critical Limitations

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
3. **Important**: Check serial port with:
   ```bash
   ls /dev/tty.*
   ```
   Then update line **135** in the main script.

**Hardware Requirements**
- Arduino Uno/Nano (tested on Uno)
- WS2812B LED strip connected to **pin D6**
- 5V power supply for LED strip (USB power may be insufficient)

**Serial Communication**
- **Baud rate**: 9600  
- **Protocol**: Newline-terminated commands  
- **Supported Commands**:
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

**Example Output**
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

**Instructions**
1. Press **SPACE** to pause live feed  
2. Left-click to draw polygon points around each zone (TABLE, TRAY, PLATE)  
3. Right-click or press **Enter** to finish a zone (system will prompt for name)  
4. Press **S** to save, **ESC** to quit  

**Output:** `config/zones.json` (contains pixel coordinates)  
**Camera-specific:** Recalibrate if the camera position or angle changes.

### Step 3: Run Main Program
```bash
python time-up-merged.py --trig-db -17.4 --rel-db -21.4 --print-audio
```

---

## Known Issues

### Platform Dependency
- Serial ports are **hardcoded** (`/dev/tty.usbserial-*`) in the main script  
- Only works on macOS

### Calibration Workflow
- **Room-specific**: Audio calibration invalid if demo is moved  
- **Camera-specific**: Zone calibration invalid if camera position changes  
- **No persistence**: Closing the program resets all runtime adjustments

---

## Troubleshooting

| Problem | Solution |
|----------|-----------|
| `Serial port not found` | Run `ls /dev/tty.*` and update line 135 in `time-up-merged.py` |
| `Camera not detecting markers` | Recalibrate with `camera_calibrator.py`; check lighting and marker size |
| `Audio triggers constantly` | Re-run `sound-calibrate.py` in demo room; update thresholds in code |
| `LED strip not responding` | Verify Arduino upload, check USB connection, or try another serial port |
| `ImportError: cv2` | Install again: `pip install opencv-python opencv-contrib-python` |
| `Zones in wrong places` | Delete old `zones.json` and recalibrate with current camera setup |

---

## Project Structure
```
The-Pressure-Cook/
│
├── Design/
│   ├── User Testing Insights/
│   ├── Interview Insights/
│   └── Figma/
│
├── Development/
│   ├── code-archive/
│   └── final-with-timer-21oct/
│
├── Tradeshow Materials/
│   ├── Main Poster.pdf
│   ├── Promo Poster.pdf
│   └── Research Poster.pdf
│
└── README.md
```

---

## Contributors
- **Ann Chang** – UX Researcher
- **Anya Goel** – UX Designer, Software and Hardware Developer
- **Hezekiah Owuor** - Software Developer
- **Sammmy Bugata** – UX Designer, Software and Hardware Developer
- **Yongjian Wan (Aiden)** - Github Manager
---

## License
This project is released for academic use for DECO3500 (Sem 2, 2025).  
If reused or modified, please credit the original authors.

---

## Contact
For installation or setup issues, contact:  
**anya.goel@uq.edu.au** or **s.bugata@student.uq.edu.au**
