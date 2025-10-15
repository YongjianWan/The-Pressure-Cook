### technical doc ver0.3

### Chicken Chaos - Technical Implementation Document ver0.2

### 0. Core Logic

1. **Camera counts red objects on table** → more than 10 → PC sends `M:1` to Arduino → red LED blinks
2. **Arduino monitors sound** → exceeds threshold for 0.5 s → red LED stays on for 10 s
3. **Priority:** Noisy > Messy > Normal → ignore Messy switch when Noisy

### 1. System Architecture

PC (Python) with OpenCV → serial command via USB link (M1/M0) → Arduino (C++)
Arduino reads sound sensor, controls LED, runs finite state machine

### Hardware Deployment

**Key setup:**

```python
# Use ROI (Region of Interest) to exclude resource area
# Assume the middle 60% is the Station area
height, width = frame.shape[:2]
roi = frame[int(height*0.2):int(height*0.8), int(width*0.2):int(width*0.8)]
# Detect red objects only within ROI
```

#### 2. Microphone (Sound Sensor)

**Position:** Center
**Coverage:** 3 Station areas
**Sensitivity:** Adjust potentiometer so that ambient noise < threshold, yelling > threshold

**Calibration:**

1. Place at center of Stations
2. Normal talking < 750
3. Shouting > 750
4. Adjust potentiometer if inaccurate

#### 3. Speaker (Buzzer)

**Position:** Near Arduino
**Function:**

- Messy → short beep (500 ms interval)
- Noisy → continuous alarm (10 s)

**Volume Control:** Add 100Ω resistor in series with Pin 8 if too loud

#### 4. LED Strip (Status Indicator)

**Position:** Yellow boundary line
**Option:**

- Simple mode: Arduino directly drives RGB LED

---

### Monitoring Strategy

| Area          | Monitored | Reason                               |
| ------------- | --------- | ------------------------------------ |
| Station 1–3   | Yes       | Main work zone, core chaos indicator |
| Resource Zone | No (?)    | Legal item pickup, not chaos         |
| Grey Zone     | No (?)    | Outside camera view, irrelevant      |

**Implementation:**

```python
# Crop ROI to include only Station area
x1, y1 = int(width*0.2), int(height*0.2)
x2, y2 = int(width*0.8), int(height*0.8)
roi = frame[y1:y2, x1:x2]
# Detect red objects only within ROI
```

### 3. PC-side Code (Python)

**Dependencies:**

```bash
pip install opencv-python==4.8.0.74 pyserial==3.5 numpy==1.24.0
```

**Parameter tuning:**

- **ROI wrong?** Adjust `0.2` and `0.8`

  - smaller → larger monitored area
  - ensure blue frame covers only Stations

- **Red range wrong?** Adjust `(0,100,100),(10,255,255)`
- **Too many noise points?** Increase `cv2.contourArea(c) > 500` threshold
- **Threshold too strict?** Modify `MESS_THRESHOLD`

**To find real HSV values:**

```python
def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        if x1 <= x <= x2 and y1 <= y <= y2:
            roi_x, roi_y = x - x1, y - y1
            print(f"HSV: {hsv[roi_y, roi_x]}")
cv2.setMouseCallback("Desk Monitor", mouse_callback)
```

**Adjust ROI (first-time setup):**

1. Run program, check if blue frame covers only Station 1–3
2. Too large → change 0.2→0.3, 0.8→0.7
3. Too small → change 0.2→0.1, 0.8→0.9
4. Adjust until blue frame fits white desktop area

### 4. Arduino-side Code (C++)

```cpp
const int SOUND_PIN = A0;
const int LED_R = 9, LED_G = 10, LED_B = 11;
const int BUZZER_PIN = 8;

const int SOUND_THRESHOLD = 750;
const int TRIGGER_COUNT = 5;
const int NOISY_DURATION = 10000;
const int SAMPLE_INTERVAL = 100;
const int BLINK_INTERVAL = 500;
const int BUZZER_FREQ = 2000;

enum State { NORMAL, MESSY, NOISY };
State currentState = NORMAL;

bool isMessy = false;
int noisyCount = 0;
unsigned long noisyStart = 0;
unsigned long lastBlink = 0;
bool blinkOn = false;
```

### 5. Communication Protocol

| Direction    | Command | Meaning       | LED            | Buzzer               |
| ------------ | ------- | ------------- | -------------- | -------------------- |
| PC → Arduino | `M:1\n` | Table messy   | Red blink      | short beep           |
| PC → Arduino | `M:0\n` | Table clean   | Green steady   | silent               |
| Arduino → PC | `S:1\n` | Loud detected | Red steady 10s | continuous alarm 10s |

### 6. Circuit Wiring

```
Arduino UNO
├─ Pin 9  → [220Ω] → LED Red
├─ Pin 10 → [220Ω] → LED Green
├─ Pin 11 → [220Ω] → LED Blue
├─ Pin 8  → Buzzer +
├─ A0     → Sound Sensor A0
├─ 5V     → Sound Sensor VCC
├─ GND    → Common GND (LED, Buzzer, Sensor)
```

**Camera:** USB to PC, 50–80 cm above desk, top-down view

---

### FAQ

**Q: Sound sensor always triggers?**
A: Turn potentiometer clockwise (less sensitive) or raise `SOUND_THRESHOLD`

**Q: Camera fails to detect red?**
A: Print HSV values to find correct range

```python
print(hsv[240, 320])
```

**Q: Resource zone also detected?**
A: Adjust ROI parameters (e.g., change 0.2→0.3), ensure blue box covers only Station area

**Q: Sound sensor detects only one Station?**
A:

1. Place sensor in center of 3 Stations
2. Turn potentiometer counterclockwise (more sensitive)
3. Or use one sensor per Station

### 11. Performance Optimization

### Target improvements

- OpenCV 30 fps (real-time)
- Arduino sampling every 100 ms
- Continuous detection to avoid false triggers
- Send serial only when state changes

### Optional enhancements

- ArUco marker instead of color detection
- Log data with timestamp to CSV
- Real-time web display (Flask)
- PWM control for buzzer volume
