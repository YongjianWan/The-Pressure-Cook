import cv2
import cv2.aruco as aruco
import serial
import os
import time
import threading
import sys
import select
import queue
# ---- TTS Setup ----
import argparse, os, shlex, threading, subprocess

import argparse, time, math, threading
import numpy as np, sounddevice as sd, queue

# ---- Load station polygons from zones.json / config/zones.json (optional) ----
import json, numpy as np, os


# ---- CLI for audio device selection (copy below your other config) ----
ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="in_dev", type=int, default=None,
                help="Input device index (e.g., your FastTrack)")
ap.add_argument("--in-name", dest="in_name", type=str, default=None,
                help='Match input device by name substring (e.g., "Fast Track", "FastTrack", "M-Audio")')
ap.add_argument("--sr", dest="sr", type=int, default=None,
                help="Sample rate. If not set, use device default.")
ap.add_argument("--in-channel", dest="in_ch", type=int, default=0,
                help="Which channel to read if the device is stereo (0=Left, 1=Right).")
ap.add_argument("--trig-db", dest="trig_db", type=float, default=-28.0,
                help="Trigger threshold in dBFS (avg >= trig -> loud)")
ap.add_argument("--rel-db", dest="rel_db", type=float, default=-32.0,
                help="Release threshold in dBFS (avg <= rel -> quiet)")
ap.add_argument("--hold-sec", dest="hold_sec", type=float, default=0.8,
                help="How long the avg must stay loud to trigger (seconds)")
ap.add_argument("--print-audio", action="store_true",
                help="Print avg dBFS and state to console once per ring")


args, _ = ap.parse_known_args() 

def find_input_by_name_substring(sub):
    """Return the first input device index whose name contains `sub` (case-insensitive)."""
    if not sub:
        return None
    for i, d in enumerate(sd.query_devices()):
        if d.get("max_input_channels", 0) > 0 and sub.lower() in d.get("name","").lower():
            return i
    return None

def resolve_input_device():
    # Priority: explicit index -> name match -> default input
    if args.in_dev is not None:
        return args.in_dev
    idx = find_input_by_name_substring(args.in_name) if args.in_name else None
    if idx is not None:
        return idx
    # fallback: whatever the system default input is
    di = sd.default.device
    return di[0] if isinstance(di, (list, tuple)) else di

# ---------- Audio helpers ----------
def _hp1(x, sr, fc=100.0, _state={'a':None,'xn1':0.0,'yn1':0.0}):
    """1st-order high-pass to remove rumble."""
    if _state['a'] is None:
        dt = 1.0/sr
        RC = 1.0/(2*math.pi*fc)
        _state['a'] = RC/(RC+dt)
    a = _state['a']; xn1 = _state['xn1']; yn1 = _state['yn1']
    y = np.empty_like(x)
    for i, xn in enumerate(x):
        yn = a*(yn1 + xn - xn1)
        y[i] = yn
        yn1, xn1 = yn, xn
    _state['xn1'], _state['yn1'] = xn1, yn1
    return y

def _block_db(buf):
    """Return dBFS of a block (0 dBFS = full-scale)."""
    rms = np.sqrt(np.mean(buf**2) + 1e-12)
    return 20.0 * math.log10(rms + 1e-12)

# ---------- Audio config/state ----------
AUDIO_SR = 48000          # sample rate (may be overridden by device default)
HP_CUTOFF = 100.0         # high-pass cutoff (Hz). 0 to disable

# thresholds (overridden by CLI)
HOLD_SEC  = args.hold_sec
TRIG_DB   = args.trig_db
REL_DB    = args.rel_db
PRINT_AUDIO = bool(args.print_audio)

# moving-average ring buffer sized to HOLD_SEC
_block_dur   = 1024.0 / AUDIO_SR
_blocks_need = max(1, int(HOLD_SEC / _block_dur))
_audio_ring  = [REL_DB - 20.0] * _blocks_need
_audio_rp    = 0

volume_loud = False       # updated by the audio callback
last_avg_db = REL_DB - 20 # for UI overlay / debug

def _load_station_polys():
    for zp in ("zones.json", os.path.join("config", "zones.json")):
        if os.path.exists(zp):
            try:
                with open(zp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Expected format: {"zones":[{"name":"STATION1","pts":[[x,y],...]}, ...]}
                name_map = {"STATION1":"station1", "STATION2":"station2", "STATION3":"station3"}
                out = {}
                for z in data.get("zones", []):
                    name = str(z.get("name","")).strip().upper()
                    pts  = z.get("pts") or []
                    if name in name_map and len(pts) >= 3:
                        out[name_map[name]] = [(int(x), int(y)) for x, y in pts]
                return out
            except Exception:
                pass
    return {}

_STATION_POLYS = _load_station_polys()

def _point_in_poly(x, y, poly):
    # ray casting
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i+1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1):
            inside = not inside
    return inside

# ---------------- Arduino Setup ----------------
ser = serial.Serial('/dev/cu.usbmodem11101', 9600)  # adjust port
time.sleep(2)
print("✅ Arduino connected.")

# ---------------- Camera Setup ----------------
cam = cv2.VideoCapture(1, cv2.CAP_AVFOUNDATION)
if not cam.isOpened():
    raise Exception("⚠ Could not open camera 0")

# ---------------- ArUco Setup ----------------
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()
aruco_detector = aruco.ArucoDetector(aruco_dict, parameters) if hasattr(aruco, "ArucoDetector") else None

# ---------------- Stations ----------------
# Still keeping rectangular stations for fallback
# Format: (x, y, w, h)
stations = {
    "station1": (50, 100, 200, 200),
    "station2": (300, 100, 200, 200),
    "station3": (550, 100, 200, 200)
}

marker_to_station = {1: "station1", 2: "station2", 3: "station3"}
camera_markers = [1, 2, 3]

# ---------------- State Tracking ----------------
marker_state = {1: False, 2: False, 3: False}
marker_out = False
marker_blinking = False
blink_active = False
led_state = "GREEN"

last_speech_time = 0
speech_interval = 1  # seconds
last_task_switch = time.time()
task_interval = 45  # seconds

simulated_queue = []

# ---- Alert priority (higher number = higher priority) ----
PRIO_SOUND     = 1
PRIO_MARKER    = 2
PRIO_COUNTDOWN = 3

current_priority = 0   # 0 = idle
blink_token = 0        # increments to cancel any in-flight blink

# ---------------- Speech Queue ----------------
speech_queue = queue.Queue()
speech_proc = None
speech_token = 0          # cancels in-flight TTS
current_speech_tag = None # "countdown" | "marker" | "sound" | None

# For volume alarm throttling
last_volume_tts_ts = 0.0
VOLUME_TTS_COOLDOWN = 4.0  # speak at most once every 4s while loud
prev_volume_loud = False   # to detect quiet→loud / loud→quiet edges

ap2 = argparse.ArgumentParser(add_help=False)
ap2.add_argument("--voice",
                 default="Samantha",
                 choices=["Samantha"],
                 help="macOS say voice: Samantha")
ap2.add_argument("--rate", type=int, default=170, help="Speaking rate (wpm), typically 150–210.")
args2, _ = ap2.parse_known_args()
# merge into the already-parsed args without overwriting its attributes
for k, v in vars(args2).items():
    setattr(args, k, v)

def clear_speech_queue():
    while not speech_queue.empty():
        try:
            speech_queue.get_nowait()
            speech_queue.task_done()
        except Exception:
            break

def cancel_speech():
    """Cancel any in-flight or queued speech immediately."""
    global speech_token, speech_proc, current_speech_tag
    speech_token += 1
    clear_speech_queue()
    if speech_proc and speech_proc.poll() is None:
        try: speech_proc.terminate()
        except Exception: pass
    current_speech_tag = None

def speech_worker():
    """Plays items from the queue; each item is (message, tag, token)."""
    global speech_proc, current_speech_tag
    while True:
        item = speech_queue.get()
        try:
            msg, tag, my_token = item
        except Exception:
            # backwards compat if only a string ended up in the queue
            msg, tag, my_token = str(item), None, speech_token

        # dropped if a newer token superseded us
        if my_token != speech_token:
            speech_queue.task_done()
            continue

        current_speech_tag = tag
        try:
            cmd = ["/usr/bin/say", "-v", str(args.voice), "-r", str(args.rate), str(msg)]
            speech_proc = subprocess.Popen(cmd)
            # poll so we can cancel early
            while True:
                if my_token != speech_token:
                    if speech_proc and speech_proc.poll() is None:
                        speech_proc.terminate()
                    break
                if speech_proc.poll() is not None:
                    break
                time.sleep(0.05)
        finally:
            speech_proc = None
            current_speech_tag = None
            speech_queue.task_done()

threading.Thread(target=speech_worker, daemon=True).start()

def speak(message, tag=None):
    """Queue a line to speak with the current speech_token."""
    speech_queue.put((message, tag, speech_token))

# ---------------- Utility Functions ----------------
# def is_in_tray(center, tray_rect):
#     x, y, w, h = tray_rect
#     cx, cy = center
#     return x <= cx <= x + w and y <= cy <= y + h

def is_in_tray(center, tray_rect, station_key=None):
    cx, cy = center
    if station_key and station_key in _STATION_POLYS:
        return _point_in_poly(cx, cy, _STATION_POLYS[station_key])
    x, y, w, h = tray_rect
    return x <= cx <= x + w and y <= cy <= y + h


def process_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if aruco_detector is not None:
        corners, ids, _ = aruco_detector.detectMarkers(gray)
    elif hasattr(aruco, "detectMarkers"):
        corners, ids, _ = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
    else:
        raise AttributeError("cv2.aruco does not expose detectMarkers or ArucoDetector")
    return corners, ids

def send_led_state(state):
    global led_state
    if state != led_state:
        command_map = {
            "GREEN": b"DEFAULT_GREEN\n",
            "RED_BLINK": b"ALARM_ON\n",
            "BLUE_BLINK": b"SWITCH_TASK\n",
            "YELLOW_BLINK": b"YELLOW_BLINK\n",
            "PINK_BLINK": b"PINK_BLINK\n",
            "WHITE_BLINK": b"WHITE_BLINK\n",
            "OFF": b"OFF\n"
        }
        ser.write(command_map.get(state, b"OFF\n"))
        led_state = state

def blink_led(led_command, times=5, delay=0.35, my_token=None):
    """
    Set an Arduino blink mode once and hold it for a computed duration,
    unless cancelled by a newer alert (blink_token changes).
    """
    global blink_active, current_priority
    if my_token is None:
        return

    # Convert the old "times+delay" into a hold duration (~ two phases per cycle)
    hold_secs = max(0.2, times * (delay * 2.0))

    def run():
        global blink_active, current_priority
        blink_active = True
        # Put Arduino into its own non-blocking blink mode
        send_led_state(led_command)
        t0 = time.time()
        while time.time() - t0 < hold_secs:
            if my_token != blink_token:   # cancelled/pre-empted
                break
            time.sleep(0.05)

        # Only the still-current alert clears state
        if my_token == blink_token:
            blink_active = False
            current_priority = 0
            # send_led_state("GREEN") - Do NOT force GREEN here; let the main loop decide the next state.

    threading.Thread(target=run, daemon=True).start()


def speak_and_blink(message, led_command, times=5, delay=0.35, priority=PRIO_SOUND, tag=None):
    """
    Start (or replace with) an alert at a given priority.
    Higher priority cancels lower immediately; lower won't interrupt higher.
    """
    global current_priority, blink_token

    if priority < current_priority:
        return  # a higher alert is already active

    # Cancel any ongoing speech (so we don't overlap) and claim alert priority
    cancel_speech()

    blink_token += 1         # cancels any in-flight blink
    current_priority = priority
    my_token = blink_token

    # speak in parallel (cancellable by future cancel_speech())
    speak(message, tag=tag)

    # start the cancellable blink
    blink_led(led_command, times=times, delay=delay, my_token=my_token)


# ---------------- Simulator Input ----------------
def simulator_input():
    print("Simulator ready: enter 1=marker out, 2=too loud, 3=too quiet, 4=recipe")
    while True:
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.readline().strip()
            simulated_queue.append(key)
        time.sleep(0.05)

threading.Thread(target=simulator_input, daemon=True).start()

# ---------------- Task Countdown ----------------
def countdown_task_switch():
    global current_priority, blink_token
    # pre-empt anything lower and stop ongoing speech
    cancel_speech()
    current_priority = PRIO_COUNTDOWN

    # take a fresh cancellation token for this countdown
    blink_token += 1
    my_token = blink_token

    # put Arduino into BLUE once; the UNO will blink on its own
    send_led_state("BLUE_BLINK")

    # stage 1 + numbers + final line (all tagged as countdown)
    speak("Please find a new stations soon", tag="countdown")
    for n in range(5, 0, -1):
        if my_token != blink_token:     # cancelled (shouldn’t happen: highest prio)
            return
        speak(str(n), tag="countdown")

    if my_token != blink_token:
        return
    speak("Go to a new station now", tag="countdown")

    # wait until all the above countdown lines have been spoken
    while my_token == blink_token and (current_speech_tag is not None or not speech_queue.empty()):
        time.sleep(0.05)

    # release only after the last phrase has finished
    if my_token == blink_token:
        current_priority = 0
        send_led_state("GREEN")

# Choose input device (CLI: --in or --in-name) and samplerate
in_dev = resolve_input_device()
try:
    dev_info = sd.query_devices(in_dev)
    AUDIO_SR = int(args.sr or dev_info["default_samplerate"])
except Exception:
    pass  # fall back to whatever AUDIO_SR was set to earlier

# set default INPUT device only (output remains system default)
sd.default.device = (in_dev, None)

# which channel to read if device is stereo (CLI: --in-channel)
IN_CHANNEL = args.in_ch
print(f"🎤 Using input device: {dev_info.get('name', 'Unknown')} @ {AUDIO_SR} Hz")
# Recompute ring size now that AUDIO_SR may have changed
_block_dur   = 1024.0 / AUDIO_SR
_blocks_need = max(1, int(HOLD_SEC / _block_dur))
_audio_ring  = [REL_DB - 20.0] * _blocks_need
_audio_rp    = 0

# ---------- Start audio stream ----------
def _audio_in_cb(indata, frames, time_info, status):
    global _audio_rp, volume_loud
    if status:
        # print only once in a while to avoid spam
        if PRINT_AUDIO:
            print(status)

    # robust mono extraction: handle 1-ch or 2-ch devices explicitly
    if indata.ndim == 1:
        mono = indata
    else:
        mono = indata[:, IN_CHANNEL]    # 0 = left, 1 = right

    if HP_CUTOFF > 0:
        mono = _hp1(mono, AUDIO_SR, HP_CUTOFF)

    db = _block_db(mono)
    _audio_ring[_audio_rp] = db
    _audio_rp = (_audio_rp + 1) % len(_audio_ring)
    avg = sum(_audio_ring) / len(_audio_ring)

    global last_avg_db
    last_avg_db = avg

    # hysteresis: cross 'TRIG_DB' to go loud, 'REL_DB' to go quiet
    if avg >= TRIG_DB:
        volume_loud = True
    elif avg <= REL_DB:
        volume_loud = False

    if PRINT_AUDIO and _audio_rp == 0:
        state = "LOUD" if volume_loud else "quiet"
        print(f"audio avg dBFS={avg:6.1f} ({state})")

_audio_stream = sd.InputStream(
    samplerate=AUDIO_SR,
    channels=1,              # if your FastTrack refuses 1-ch, change to 2
    blocksize=1024,
    device=(in_dev, None),   # <-- use the resolved input device
    callback=_audio_in_cb,
    dtype="float32",
)

_audio_stream.start()
print("🎙️  Mic monitor running…")

# ---------------- Final Timeout Sequence (after 5 mins) ----------------
def final_timeout_sequence():
    global blink_token, audio_active, aruco_active, trigger_active

    # Wait 5 minutes from script start
    time.sleep(300)
    print("⏰ Final timeout reached – entering shutdown mode")

    # ----- STOP ALL OTHER THREADS -----
    # Turn off sound detection, TTS queue, and marker logic
    audio_active = False
    aruco_active = False
    trigger_active = False

    # Cancel anything currently speaking or blinking
    cancel_speech()
    blink_token += 1

    # Stop any active LEDs
    send_led_state("OFF")

    # Small pause to make sure everything clears
    time.sleep(0.5)

    # ----- Final announcement -----
    speak_and_blink(
        "You have been too slow. Please speed up.",
        "WHITE_BLINK",
        times=8,
        delay=0.3
    )

    # Wait enough time for TTS + blink to finish
    time.sleep(8 * 0.6 + 3)

    # Turn lights off and end
    send_led_state("OFF")
    print("🔚 Session complete. Exiting.")
    os._exit(0)


# Run timeout thread
threading.Thread(target=final_timeout_sequence, daemon=True).start()



# ---------------- Main Loop ----------------
while True:
    ret, frame = cam.read()
    if not ret:
        continue

    current_out = set()
    corners, ids = process_frame(frame)

    # --- Detect marker out ---
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            if marker_id not in camera_markers:
                continue
            pts = corners[i][0].astype(int)
            cx, cy = int(pts[:, 0].mean()), int(pts[:, 1].mean())
            # assigned_station = marker_to_station[marker_id]
            # in_tray = is_in_tray((cx, cy), stations[assigned_station])
            assigned_station = marker_to_station[marker_id]
            in_tray = is_in_tray((cx, cy), stations[assigned_station], station_key=assigned_station)


            if not in_tray:
                current_out.add(marker_id)
            color = (255, 0, 0) if not in_tray else (0, 255, 0)
            cv2.polylines(frame, [pts], True, color, 2)
            cv2.putText(frame, f"Marker {marker_id}: {'OUT!' if not in_tray else 'In tray'}",
                        (cx, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # --- Draw stations ---
    # for s_name, (x, y, w, h) in stations.items():
    #     cv2.rectangle(frame, (x, y, w, h), (0, 0, 255), 2)
    #     cv2.putText(frame, s_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # --- Draw stations (polygon first, else rectangle) ---
    for s_name, rect in stations.items():
        if s_name in _STATION_POLYS:
            pts = np.array(_STATION_POLYS[s_name], np.int32)
            cv2.polylines(frame, [pts], True, (0, 0, 255), 2)
            M = pts.mean(axis=0).astype(int)
            cv2.putText(frame, s_name, (int(M[0]), int(M[1]) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        else:
            x, y, w, h = rect
            cv2.rectangle(frame, (x, y, w, h), (0, 0, 255), 2)
            cv2.putText(frame, s_name, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)


    # --- Priority Handling ---
    now = time.time()
    task_due  = (now - last_task_switch) >= (task_interval - 5)
    aruco_out = bool(current_out)
    sound_loud = volume_loud

    # --- handle loud -> quiet edge: stop volume TTS immediately ---
    if prev_volume_loud and not sound_loud:
        if current_speech_tag == "sound":
            cancel_speech()
        if current_priority == PRIO_SOUND:
            blink_token += 1           # cancel the sound blink hold thread
            blink_active = False        # allow other branches / idle to drive LEDs
            current_priority = 0
            # If nothing higher is active, immediately leave yellow on the UNO:
            if not task_due and not aruco_out:
                send_led_state("GREEN")
    prev_volume_loud = sound_loud

    if task_due and PRIO_COUNTDOWN >= current_priority:
        last_task_switch = now
        countdown_task_switch()  # Runs two-stage TTS with blue blink

    elif aruco_out and PRIO_MARKER > current_priority:
        # 2) MARKER OUT — pre-empt sound
        # marker branch
        speak_and_blink("Counter too messy. Please clean up.", "RED_BLINK", times=6, delay=0.35,
                        priority=PRIO_MARKER, tag="marker")

    elif (not task_due) and (not aruco_out) and sound_loud and PRIO_SOUND >= current_priority:
        now_ts = time.time()
        if now_ts - last_volume_tts_ts >= VOLUME_TTS_COOLDOWN:
            last_volume_tts_ts = now_ts
            speak_and_blink("Volume is too loud. Calm down",
                            "YELLOW_BLINK", times=5, delay=0.35,
                            priority=PRIO_SOUND, tag="sound")

    else:
        # idle (don’t fight with an active blink or pending events)
        if current_priority == 0 and not blink_active and not task_due and not aruco_out and not volume_loud:
            send_led_state("GREEN")

    # --- Process simulated queue only if no high-priority events ---
    if not marker_out and not task_due:
        while simulated_queue:
            key = simulated_queue.pop(0)
            if key == "1":
                speak_and_blink("Counter too messy. Please clean up.", "RED_BLINK")
            elif key == "2":
                speak_and_blink("Volume is too loud. Calm down", "YELLOW_BLINK")
            elif key == "3":
                speak_and_blink("Too quiet. Not enough socialising", "YELLOW_BLINK")
            elif key == "4":
                speak_and_blink("Please follow the recipe carefully", "PINK_BLINK")

    # --- Marker state print ---
    for marker_id in camera_markers:
        if marker_id in current_out and not marker_state[marker_id]:
            print(f"⚠ Marker {marker_id} out!")
            marker_state[marker_id] = True
        elif marker_id not in current_out and marker_state[marker_id]:
            print(f"✅ Marker {marker_id} back")
            marker_state[marker_id] = False

        # --- dB overlay (visual debug) ---
        
    # Map dBFS from [-60 .. 0] to a 0..1 bar
    lo, hi = -60.0, 0.0
    pct = 0.0 if last_avg_db <= lo else (1.0 if last_avg_db >= hi else (last_avg_db - lo) / (hi - lo))
    bar_w, bar_h = 200, 14
    x0, y0 = 20, 20
    cv2.rectangle(frame, (x0, y0), (x0 + bar_w, y0 + bar_h), (60, 60, 60), 1)
    cv2.rectangle(frame, (x0, y0), (x0 + int(bar_w * pct), y0 + bar_h), (0, 200, 0) if not volume_loud else (0, 140, 255), -1)
    cv2.putText(frame, f"avg {last_avg_db:5.1f} dBFS  trig {TRIG_DB:.1f}  rel {REL_DB:.1f}",
                (x0, y0 + bar_h + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)


    cv2.imshow("Utensil Monitor", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()