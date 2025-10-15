# User Flow & Task Structure (English)

> Goal: **Three participants co-create a plate of fruit salad** (target cut size / quantities achieved).  
> Focus: **Social participation, verbal collaboration, fair rotation, order and safety**.  
> Rhythm cues: **LED (white-light patterns) + buzzer**; voice prompts: **TTS** (Soon / 5→1 / Now).

---

## 1) Roles & Positions (Clockwise Rotation)

| Role | Primary task | Handoff destination | Notes |
|---|---|---|---|
| **P1 \| Preparing** | Peel, trim, deseed | Place onto the central **shared tray** | Keep cutting board dry, knife edge facing inward |
| **P2 \| Cut** | Dice to **3 cm ± 0.5 cm** (or specified style) | Place on the tray **near P3** | Keep pieces consistent |
| **P3 \| Plate & Tidy & Agenda Keeper** | Plate directly from the tray **onto the shared plate**; tidy simultaneously | Final plating | At the **start** of each round draw one Agenda card (silent) and finish quietly within 60 s |

- Layout: `P1 (left board) | shared tray | P2 (right board); P3 has the final plate in front`  
- Rotation: `P1 → P2 → P3 → P1` (**clockwise**)

---

## 2) Setup (T = −30 s → 0 s)

1. **Read the TASK** (fruit list & cutting style)  
   Example: Apple **3 cm cubes ×16**, Banana **3 cm cubes ×16**, Grape **halves ×16 half-pieces**
2. **Decide starting positions** (according to the table above)
3. **Trigger (choose one)**  
   - **P3 RFID tap** → system receives **`START`**  
   - **Facilitator presses button** → system receives **`START`**

> **LED / buzzer (START)**: LED short-on **120 ms** + buzzer short beep **120 ms**.

---

## 3) Round Rhythm (**70 s / round**)

> `Work 0–60 s → Prepare to switch → Handoff 60–70 s`

### 3.1 T = 0 s | Round begins
- **P3 draws one Agenda card** (silent; complete within 60 s)
- Everyone works by station:
  - P1: preparation → **shared tray**
  - P2: dicing → **tray near P3**
  - P3: **plate** + tidy (add garnish if desired)

> **LED (T = 0)**: optionally keep off (quiet) or short-on 120 ms

### 3.2 T = 55–60 s | `ALARM_WARNING` (prepare to switch)
- **TTS**: “Switching tasks soon” → **5 4 3 2 1** (one beat per second)  
- **Buzzer**: short beep ×2  
- **LED**: **flash twice** (150 ms on / 150 ms off ×2)

### 3.3 T = 60 s | `ALARM_ON` (switch now)
- **TTS**: “Switch tasks now” → **clockwise rotation** (P1→P2, P2→P3, P3→P1)  
- **Buzzer**: long beep ~800 ms  
- **LED**: **steady on for 800 ms**

### 3.4 T = 60–70 s | Verbal handoff (≤10 / 5 s)
- Script: **What’s left → Next step → Risks** (slippery knife, wet board, rolling items)  
- LED: **off** (avoid distracting the handoff)

### 3.5 Preparation window rules (extra)
- **Rounds 1–3**: preparation window **10 s** (`ALARM_WARNING` at **T = 50**)  
- **Round 4 onward**: preparation window **5 s** (`ALARM_WARNING` at **T = 55**)

### 3.6 Round n+1
- **T = 0–70 s**: same flow (P3 draws another Agenda card)  
- Recommended session: **6–8 rounds** (6–8 minutes)  
- **Finish**: P1 RFID tap → send **`FINISH`**

> **LED / buzzer (FINISH)**: **three-stage celebration** (buzzer 1100→1200→1300 Hz; LED triple pulse with the same rhythm)

---

## 4) Post-completion TTS (per round count)

- **≤ 6 rounds (≤ 7:00)** — Highly efficient + high interaction  
  - Lightning fast and in sync; every handoff was crisp!  
  - Speedy teamwork: fair rotations, decisive handoffs!  
  - Outstanding rapport: one-person-one-line, zero friction!  
  - Rapid finish with clear roles and calm energy!
- **7–8 rounds (7:01–9:20)** — Steady delivery + solid social quality  
  - Finished on target; clear voices, attentive listening!  
  - On-time delivery; rotations orderly, support unbroken!  
  - Stable rhythm; the handoff formula works—what’s left, next step, risks!  
  - Smooth collaboration and positive vibe; ask for help when needed, offer help when timely!
- **9–10 rounds (9:21–11:40)** — Patient completion + order and safety intact  
  - Resilient pace; volume under control, quick boundary resets!  
  - Patience paid off; tidy as you go, clean movement paths, beautiful finish!  
  - Collaboration stayed online; every rotation snapped back into flow!  
  - Thorough execution; safety details and shared tray order all covered!
- **> 10 rounds (> 11:40)** — Task complete + elevate next round  
  - Mission accomplished! Next round aim for faster verbal handoffs!  
  - Great job! Use “What’s left → Next step → Risks” more often for extra smoothness!  
  - Done! Next time ask/offer help earlier to boost interaction!  
  - All wrapped up! Next round return to the shared tray faster for extra efficiency!

> **LED**: after the completion announcement, only three short pulses—no long hold—to support wrap-up and photos.

---

## 5) Three Mechanisms (Data Flow × Boundaries × LED)

### 5.1 ① Task Alarm (Soon / 5→1 / Now)
**Input**: `START` (P3 RFID / button), `FINISH` (P1 RFID)  
**Process (70 s)**: T = 0 `ALARM_DRAW` / T = 55 `ALARM_WARNING` / T = 60 `ALARM_ON` / T = 60–70 verbal handoff  
**Output**: TTS (Soon + countdown / Now), buzzer (short / long), LED (flash twice / on 800 ms / three-stage celebration)  
**Boundaries**: fixed tempo; complete handoff within ≤10 s after `ALARM_ON`; TTS speaks first, buzzer/LED are rhythmic cues only

### 5.2 ② Camera Messy (Marker + Allowed Zone ROI)
**Concept**: **Marker = item that must go home; ROI = parking slot**. **TABLE (safety) → SECTION (order)**.  
**Logic**:  
- TABLE: missing (continuous ≥0.3–0.5 s) → **`HARD_OUT`**  
- SECTION: inside any allowed zone → OK; if previously Messy and continuous ≥0.8 s → **`MESSY_OFF`**; fully outside all zones continuous ≥1.0 s → **`MESSY_ON`**  
- Occlusion <0.5 s ignored; **missing timeout >5 s** → auto-clear state (if Messy, send one `MESSY_OFF`)  
**LED / buzzer**: HARD_OUT fast flash twice + short beep ×2; MESSY_ON flash thrice + short beep ×2; MESSY_OFF lights off

### 5.3 ③ Sound Level (Noisy / Quiet)
**Input**: A0 microphone, short window 50–100 ms  
**Process**: RMS → relative dB; `NOISY_ON` (≥70–75 dB for ≥400 ms) / `NOISY_OFF` (falls below for ≥600 ms) / `QUIET_ON` (≤40–45 dB for ≥25–30 s, single shot)  
**Output**: NOISY_ON (TTS + LED 0.5 s pulse); NOISY_OFF (silent); QUIET_ON (TTS + LED 150 ms flash)  
**Arbitration**: `NOISY_ON > HARD_OUT > MESSY_ON > QUIET_ON > NORMAL` (**HARD_OUT never delayed**)

---

## 6) Hardware & Files (Single Board)

- **RFID (MFRC522)**: SDA/SS = D10, SCK = D13, MOSI = D11, MISO = D12, RST = D9, 3.3V/GND  
- **Button**: D2 (INPUT_PULLUP) ↔ GND  
- **Buzzer**: D8 → +, GND → −  
- **LED**: NeoPixel (D6 data) or 12V single-color (D6 PWM → MOSFET)  
- **Microphone**: AO → A0 (5V/GND)  
- **Camera**: USB → PC  
- **Files**: `run_hub.py` / `ledstrip_countdown.py` / `camera.py` / `camera_works_fam.py` / `roi_calibrator.py` / `allow.json` / `zones.json` / `ledstrip.ino`

---

## 7) On-site Checklist

- [ ] START: LED 120 ms + short beep; Hub receives `START`
- [ ] 55 s countdown: 1 beat per second, LED flashes twice, short beep ×2
- [ ] 60 s switch: LED on 800 ms, long beep; handoff ≤10 s
- [ ] Messy: out of zone ≥1 s → `MESSY_ON`; back for ~0.8 s → `MESSY_OFF`
- [ ] **Hard Out (voice triggers immediately even during NOISY)**  
- [ ] **Missing Kill 5 s: auto clear state** (sends one `MESSY_OFF` if currently Messy)
- [ ] Noisy / Quiet: ≥1 s loud ⇒ `NOISY_ON`; ~0.6 s calm ⇒ `NOISY_OFF`; 25–30 s quiet stretch ⇒ `QUIET_ON`
- [ ] Finish: round-based praise; LED / buzzer triple celebration
