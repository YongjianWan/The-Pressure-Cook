import sounddevice as sd
import numpy as np
import math
import argparse

# ---------------- CLI ----------------
ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="in_dev", type=int, default=1,
                help="Input device index (MacBook Pro Mic = 1)")
ap.add_argument("--trig-db", dest="trig_db", type=float, default=-114.0,
                help="Trigger threshold in dBFS")
ap.add_argument("--rel-db", dest="rel_db", type=float, default=-118.0,
                help="Release threshold in dBFS")
ap.add_argument("--hold-sec", dest="hold_sec", type=float, default=0.8,
                help="How long avg must stay loud to trigger (seconds)")
ap.add_argument("--print-audio", action="store_true", help="Print avg dBFS")
args = ap.parse_args()

# ---------------- Helpers ----------------
def _block_db(buf):
    rms = np.sqrt(np.mean(buf**2) + 1e-12)
    return 20.0 * math.log10(rms + 1e-12)

# ---------------- Config ----------------
AUDIO_SR = 48000
HOLD_SEC  = args.hold_sec
TRIG_DB   = args.trig_db
REL_DB    = args.rel_db
PRINT_AUDIO = True

_block_dur   = 1024.0 / AUDIO_SR
_blocks_need = max(1, int(HOLD_SEC / _block_dur))
_audio_ring  = [REL_DB - 20.0] * _blocks_need
_audio_rp    = 0
volume_loud  = False
last_avg_db  = REL_DB - 20

# ---------------- Audio Callback ----------------
def audio_callback(indata, frames, time_info, status):
    global _audio_rp, volume_loud, last_avg_db
    if status:
        print(status)

    mono = indata[:, 0] if indata.ndim > 1 else indata
    db = _block_db(mono)

    _audio_ring[_audio_rp] = db
    _audio_rp = (_audio_rp + 1) % len(_audio_ring)
    avg = sum(_audio_ring) / len(_audio_ring)
    last_avg_db = avg

    if avg >= TRIG_DB:
        volume_loud = True
    elif avg <= REL_DB:
        volume_loud = False

    if PRINT_AUDIO and _audio_rp == 0:
        state = "LOUD" if volume_loud else "quiet"
        print(f"audio avg dBFS={avg:6.1f} ({state})")

# ---------------- Main ----------------
try:
    dev_info = sd.query_devices(args.in_dev)
    AUDIO_SR = int(dev_info["default_samplerate"])
except Exception:
    pass

sd.default.device = (args.in_dev, None)

with sd.InputStream(
    samplerate=AUDIO_SR,
    channels=1,
    blocksize=1024,
    device=(args.in_dev, None),
    callback=audio_callback,
    dtype="float32"
):
    print(f"🎤 Using input device #{args.in_dev}: {dev_info['name']} @ {AUDIO_SR} Hz")
    print("Monitoring audio... Press Ctrl+C to quit.")
    try:
        while True:
            sd.sleep(1000)
    except KeyboardInterrupt:
        print("Exiting...")
