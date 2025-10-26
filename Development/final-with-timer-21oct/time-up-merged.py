# We acknowledge using ChatGPT and Claude AI in developing this code to have task rotation, camera tracking, sound recognition and simulated fallbacks.
# We confirm that we fully understood all suggested changes and adjusted the code where needed.
# we maintained control over the functionality and how the code priorities and arduino connections should be done at all times.

# python3 time-up-merged.py --trig-db -17.0 --rel-db -21.0 --print-audio

import cv2
import cv2.aruco as aruco
import serial
import os
import time
import threading
import sys
import select
import queue
import argparse, shlex, subprocess
import math
import numpy as np
import sounddevice as sd
import json


# CLI args for audio device selection
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
    """Find audio input device whose name contains the given substring."""
    if not sub:
        return None
    for i, d in enumerate(sd.query_devices()):
        if d.get("max_input_channels", 0) > 0 and sub.lower() in d.get("name","").lower():
            return i
    return None


def resolve_input_device():
    """Figure out which audio input to use: explicit index, name match, or system default."""
    if args.in_dev is not None:
        return args.in_dev
    idx = find_input_by_name_substring(args.in_name) if args.in_name else None
    if idx is not None:
        return idx
    di = sd.default.device
    return di[0] if isinstance(di, (list, tuple)) else di


def _hp1(x, sr, fc=100.0, _state={'a':None,'xn1':0.0,'yn1':0.0}):
    """Simple high-pass filter to cut out low-frequency rumble."""
    if _state['a'] is None:
        dt = 1.0/sr
        RC = 1.0/(2*math.pi*fc)
        _state['a'] = RC/(RC+dt)
    a = _state['a']
    xn1 = _state['xn1']
    yn1 = _state['yn1']
    y = np.empty_like(x)
    for i, xn in enumerate(x):
        yn = a*(yn1 + xn - xn1)
        y[i] = yn
        yn1, xn1 = yn, xn
    _state['xn1'], _state['yn1'] = xn1, yn1
    return y


def _block_db(buf):
    """Convert RMS of audio block to dBFS (0 dBFS = full scale)."""
    rms = np.sqrt(np.mean(buf**2) + 1e-12)
    return 20.0 * math.log10(rms + 1e-12)


# Audio config
AUDIO_SR = 48000
HP_CUTOFF = 100.0

HOLD_SEC  = args.hold_sec
TRIG_DB   = args.trig_db
REL_DB    = args.rel_db
PRINT_AUDIO = bool(args.print_audio)

# Ring buffer for moving average over HOLD_SEC
_block_dur   = 1024.0 / AUDIO_SR
_blocks_need = max(1, int(HOLD_SEC / _block_dur))
_audio_ring  = [REL_DB - 20.0] * _blocks_need
_audio_rp    = 0

volume_loud = False
last_avg_db = REL_DB - 20


def _load_station_polys():
    """Load polygon definitions for stations from zones.json if available."""
    for zp in ("zones.json", os.path.join("config", "zones.json")):
        if os.path.exists(zp):
            try:
                with open(zp, "r", encoding="utf-8") as f:
                    data = json.load(f)
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
    """Ray casting algorithm to check if point is inside polygon."""
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i+1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1):
            inside = not inside
    return inside


# Arduino connection
ser = serial.Serial('/dev/cu.usbmodem11101', 9600)
time.sleep(2)
print("✅ Arduino connected.")

# Camera setup
cam = cv2.VideoCapture(1, cv2.CAP_AVFOUNDATION)
if not cam.isOpened():
    raise Exception("⚠ Could not open camera 0")

# ArUco marker detection
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()
aruco_detector = aruco.ArucoDetector(aruco_dict, parameters) if hasattr(aruco, "ArucoDetector") else None

# Station definitions (fallback rectangles if no polygons)
stations = {
    "station1": (50, 100, 200, 200),
    "station2": (300, 100, 200, 200),
    "station3": (550, 100, 200, 200)
}

marker_to_station = {1: "station1", 2: "station2", 3: "station3"}
camera_markers = [1, 2, 3]

# State tracking
marker_state = {1: False, 2: False, 3: False}
marker_out = False
marker_blinking = False
blink_active = False
led_state = "GREEN"

last_speech_time = 0
speech_interval = 1
last_task_switch = time.time()
task_interval = 45

simulated_queue = []

# Alert priority levels
PRIO_SOUND     = 1
PRIO_MARKER    = 2
PRIO_COUNTDOWN = 3

current_priority = 0
blink_token = 0

# TTS queue setup
speech_queue = queue.Queue()
speech_proc = None
speech_token = 0
current_speech_tag = None

# Volume alarm throttling
last_volume_tts_ts = 0.0
VOLUME_TTS_COOLDOWN = 4.0
prev_volume_loud = False

# Voice settings
ap2 = argparse.ArgumentParser(add_help=False)
ap2.add_argument("--voice",
                 default="Samantha",
                 choices=["Samantha"],
                 help="macOS say voice: Samantha")
ap2.add_argument("--rate", type=int, default=170, help="Speaking rate (wpm), typically 150–210.")
args2, _ = ap2.parse_known_args()
for k, v in vars(args2).items():
    setattr(args, k, v)


def clear_speech_queue():
    """Empty the TTS queue without blocking."""
    while not speech_queue.empty():
        try:
            speech_queue.get_nowait()
            speech_queue.task_done()
        except Exception:
            break


def cancel_speech():
    """Stop any currently playing or queued speech."""
    global speech_token, speech_proc, current_speech_tag
    speech_token += 1
    clear_speech_queue()
    if speech_proc and speech_proc.poll() is None:
        try: 
            speech_proc.terminate()
        except Exception: 
            pass
    current_speech_tag = None


def speech_worker():
    """Background thread that plays queued TTS messages."""
    global speech_proc, current_speech_tag
    while True:
        item = speech_queue.get()
        try:
            msg, tag, my_token = item
        except Exception:
            msg, tag, my_token = str(item), None, speech_token

        if my_token != speech_token:
            speech_queue.task_done()
            continue

        current_speech_tag = tag
        try:
            cmd = ["/usr/bin/say", "-v", str(args.voice), "-r", str(args.rate), str(msg)]
            speech_proc = subprocess.Popen(cmd)
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
    """Add a message to the speech queue."""
    speech_queue.put((message, tag, speech_token))


def is_in_tray(center, tray_rect, station_key=None):
    """Check if marker center is inside station (polygon or rectangle)."""
    cx, cy = center
    if station_key and station_key in _STATION_POLYS:
        return _point_in_poly(cx, cy, _STATION_POLYS[station_key])
    x, y, w, h = tray_rect
    return x <= cx <= x + w and y <= cy <= y + h


def process_frame(frame):
    """Detect ArUco markers in the frame."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if aruco_detector is not None:
        corners, ids, _ = aruco_detector.detectMarkers(gray)
    elif hasattr(aruco, "detectMarkers"):
        corners, ids, _ = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
    else:
        raise AttributeError("cv2.aruco does not expose detectMarkers or ArucoDetector")
    return corners, ids


def send_led_state(state):
    """Send LED command to Arduino if state changed."""
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
    """Set Arduino LED mode and hold for a duration unless cancelled."""
    global blink_active, current_priority
    if my_token is None:
        return

    hold_secs = max(0.2, times * (delay * 2.0))

    def run():
        global blink_active, current_priority
        blink_active = True
        send_led_state(led_command)
        t0 = time.time()
        while time.time() - t0 < hold_secs:
            if my_token != blink_token:
                break
            time.sleep(0.05)

        if my_token == blink_token:
            blink_active = False
            current_priority = 0

    threading.Thread(target=run, daemon=True).start()


def speak_and_blink(message, led_command, times=5, delay=0.35, priority=PRIO_SOUND, tag=None):
    """Trigger an alert with TTS and LED blink at given priority level.
    Higher priority cancels lower; lower won't interrupt higher."""
    global current_priority, blink_token

    if priority < current_priority:
        return

    cancel_speech()

    blink_token += 1
    current_priority = priority
    my_token = blink_token

    speak(message, tag=tag)
    blink_led(led_command, times=times, delay=delay, my_token=my_token)


def simulator_input():
    """Background thread for keyboard simulation of events."""
    print("Simulator ready: enter 1=marker out, 2=too loud, 3=too quiet, 4=recipe")
    while True:
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.readline().strip()
            simulated_queue.append(key)
        time.sleep(0.05)

threading.Thread(target=simulator_input, daemon=True).start()


def countdown_task_switch():
    """Run the task switch countdown with TTS and blue LED blink."""
    global current_priority, blink_token
    cancel_speech()
    current_priority = PRIO_COUNTDOWN

    blink_token += 1
    my_token = blink_token

    send_led_state("BLUE_BLINK")

    speak("Please find a new stations soon", tag="countdown")
    for n in range(5, 0, -1):
        if my_token != blink_token:
            return
        speak(str(n), tag="countdown")

    if my_token != blink_token:
        return
    speak("Go to a new station now", tag="countdown")

    # Wait for all countdown TTS to finish
    while my_token == blink_token and (current_speech_tag is not None or not speech_queue.empty()):
        time.sleep(0.05)

    if my_token == blink_token:
        current_priority = 0
        send_led_state("GREEN")


# Set up audio input device
in_dev = resolve_input_device()
try:
    dev_info = sd.query_devices(in_dev)
    AUDIO_SR = int(args.sr or dev_info["default_samplerate"])
except Exception:
    pass

sd.default.device = (in_dev, None)

IN_CHANNEL = args.in_ch
print(f"🎤 Using input device: {dev_info.get('name', 'Unknown')} @ {AUDIO_SR} Hz")

# Recalculate ring buffer size with actual sample rate
_block_dur   = 1024.0 / AUDIO_SR
_blocks_need = max(1, int(HOLD_SEC / _block_dur))
_audio_ring  = [REL_DB - 20.0] * _blocks_need
_audio_rp    = 0


def _audio_in_cb(indata, frames, time_info, status):
    """Audio callback - processes blocks and updates volume state."""
    global _audio_rp, volume_loud, last_avg_db
    if status and PRINT_AUDIO:
        print(status)

    # Handle both mono and stereo inputs
    if indata.ndim == 1:
        mono = indata
    else:
        mono = indata[:, IN_CHANNEL]

    if HP_CUTOFF > 0:
        mono = _hp1(mono, AUDIO_SR, HP_CUTOFF)

    db = _block_db(mono)
    _audio_ring[_audio_rp] = db
    _audio_rp = (_audio_rp + 1) % len(_audio_ring)
    avg = sum(_audio_ring) / len(_audio_ring)

    last_avg_db = avg

    # Hysteresis-based state switching
    if avg >= TRIG_DB:
        volume_loud = True
    elif avg <= REL_DB:
        volume_loud = False

    if PRINT_AUDIO and _audio_rp == 0:
        state = "LOUD" if volume_loud else "quiet"
        print(f"audio avg dBFS={avg:6.1f} ({state})")

_audio_stream = sd.InputStream(
    samplerate=AUDIO_SR,
    channels=1,
    blocksize=1024,
    device=(in_dev, None),
    callback=_audio_in_cb,
    dtype="float32",
)

_audio_stream.start()
print("🎙️  Mic monitor running…")


def final_timeout_sequence():
    """After 5 minutes, shut down with final warning."""
    global blink_token, audio_active, aruco_active, trigger_active

    time.sleep(300)
    print("⏰ Final timeout reached – entering shutdown mode")

    audio_active = False
    aruco_active = False
    trigger_active = False

    cancel_speech()
    blink_token += 1

    send_led_state("OFF")
    time.sleep(0.5)

    speak_and_blink(
        "You have been too slow. Please speed up.",
        "WHITE_BLINK",
        times=8,
        delay=0.3
    )

    time.sleep(8 * 0.6 + 3)

    send_led_state("OFF")
    print("🔚 Session complete. Exiting.")
    os._exit(0)

threading.Thread(target=final_timeout_sequence, daemon=True).start()


# Main loop
while True:
    ret, frame = cam.read()
    if not ret:
        continue

    current_out = set()
    corners, ids = process_frame(frame)

    # Detect markers outside their stations
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            if marker_id not in camera_markers:
                continue
            pts = corners[i][0].astype(int)
            cx, cy = int(pts[:, 0].mean()), int(pts[:, 1].mean())
            assigned_station = marker_to_station[marker_id]
            in_tray = is_in_tray((cx, cy), stations[assigned_station], station_key=assigned_station)

            if not in_tray:
                current_out.add(marker_id)
            color = (255, 0, 0) if not in_tray else (0, 255, 0)
            cv2.polylines(frame, [pts], True, color, 2)
            cv2.putText(frame, f"Marker {marker_id}: {'OUT!' if not in_tray else 'In tray'}",
                        (cx, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # Draw station zones on frame
    for s_name, rect in stations.items():
        if s_name in _STATION_POLYS:
            pts = np.array(_STATION_POLYS[s_name], np.int32)
            cv2.polylines(frame, [pts], True, (0, 0, 255), 2)
            M = pts.mean(axis=0).astype(int)
            cv2.putText(frame, s_name, (int(M[0]), int(M[1]) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        else:
            x, y, w, h = rect
            cv2.rectangle(frame, (x, y, x + w, y + h), (0, 0, 255), 2)
            cv2.putText(frame, s_name, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # Priority-based alert handling
    now = time.time()
    task_due  = (now - last_task_switch) >= (task_interval - 5)
    aruco_out = bool(current_out)
    sound_loud = volume_loud

    # Handle volume going from loud to quiet
    if prev_volume_loud and not sound_loud:
        if current_speech_tag == "sound":
            cancel_speech()
        if current_priority == PRIO_SOUND:
            blink_token += 1
            blink_active = False
            current_priority = 0
            if not task_due and not aruco_out:
                send_led_state("GREEN")
    prev_volume_loud = sound_loud

    if task_due and PRIO_COUNTDOWN >= current_priority:
        last_task_switch = now
        countdown_task_switch()

    elif aruco_out and PRIO_MARKER > current_priority:
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
        # Idle state - return to green if no alerts
        if current_priority == 0 and not blink_active and not task_due and not aruco_out and not volume_loud:
            send_led_state("GREEN")

    # Process simulator input when no high-priority events
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

    # Track marker state changes
    for marker_id in camera_markers:
        if marker_id in current_out and not marker_state[marker_id]:
            print(f"⚠ Marker {marker_id} out!")
            marker_state[marker_id] = True
        elif marker_id not in current_out and marker_state[marker_id]:
            print(f"✅ Marker {marker_id} back")
            marker_state[marker_id] = False

    # Draw audio level bar on frame
    lo, hi = -60.0, 0.0
    pct = 0.0 if last_avg_db <= lo else (1.0 if last_avg_db >= hi else (last_avg_db - lo) / (hi - lo))
    bar_w, bar_h = 200, 14
    x0, y0 = 20, 20
    cv2.rectangle(frame, (x0, y0), (x0 + bar_w, y0 + bar_h), (60, 60, 60), 1)
    cv2.rectangle(frame, (x0, y0), (x0 + int(bar_w * pct), y0 + bar_h), 
                  (0, 200, 0) if not volume_loud else (0, 140, 255), -1)
    cv2.putText(frame, f"avg {last_avg_db:5.1f} dBFS  trig {TRIG_DB:.1f}  rel {REL_DB:.1f}",
                (x0, y0 + bar_h + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)

    cv2.imshow("Utensil Monitor", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()