# We acknowledge using ChatGPT and Claude AI in developing this code to calibrate the system's sound levels.
# We confirm that we fully understood all suggested changes and adjusted the code where needed.
# we maintained control over the functionality and logic of the code at all times.

# Usage: python3 calibrate.py --in <input_device> --sr 44100 --seconds 20 --hp 100
# Example: python3 calibrate.py --in 2 --sr 44100

import json, time, math, numpy as np, sounddevice as sd
import argparse, statistics as stats

# Show all available audio devices
print(json.dumps(sd.query_devices(), indent=2))
print("\nDefault devices (in, out):", sd.default.device)
print("Default samplerate:", sd.query_devices(sd.default.device[0])["default_samplerate"])


def hp1(x, sr, fc=100.0, z=[0.0], xprev=[0.0]):
    """Single-pole high-pass filter to remove low-frequency noise.
    Uses difference equation: y[n] = a*(y[n-1] + x[n] - x[n-1])
    where a = RC/(RC+dt) and RC = 1/(2*pi*fc)"""
    dt = 1.0/sr
    RC = 1.0/(2*math.pi*fc)
    a = RC/(RC+dt)
    y = np.empty_like(x)
    xn1 = xprev[0]
    yn1 = z[0]
    for i, xn in enumerate(x):
        yn = a*(yn1 + xn - xn1)
        y[i] = yn
        yn1, xn1 = yn, xn
    z[0], xprev[0] = yn1, xn1
    return y


def block_db(buf):
    """Calculate RMS level in dBFS for an audio buffer.
    0 dBFS is full scale (peak = 1.0)"""
    rms = np.sqrt(np.mean(buf**2) + 1e-12)
    return 20*math.log10(rms + 1e-12)


p = argparse.ArgumentParser()
p.add_argument("--in", dest="in_dev", type=int, required=True, help="Input device index")
p.add_argument("--sr", dest="sr", type=int, default=48000, help="Sample rate (Hz)")
p.add_argument("--seconds", type=int, default=20, help="Calibration duration")
p.add_argument("--hp", type=float, default=100.0, help="High-pass cutoff (Hz), 0 to disable")
args = p.parse_args()

sd.default.device = (args.in_dev, None)
sr = args.sr
vals = []


def cb(indata, frames, time_info, status):
    """Audio callback - processes each block and records dB levels."""
    if status:
        print(status)
    mono = indata[:,0]
    if args.hp > 0:
        mono = hp1(mono, sr, args.hp)
    vals.append(block_db(mono))


with sd.InputStream(samplerate=sr, channels=1, callback=cb, blocksize=1024):
    print(f"Calibrating for {args.seconds}s… talk at your normal level.")
    t0 = time.time()
    while time.time() - t0 < args.seconds:
        time.sleep(0.1)

avg = stats.fmean(vals)
p95 = np.percentile(vals, 95)

print(f"\nRoom dB (HPF {args.hp} Hz): avg={avg:.1f} dBFS, p95={p95:.1f} dBFS")
print("Suggested thresholds:")
print(f" trigger ~ {p95+6:.1f} dBFS")
print(f" release ~ {p95+2:.1f} dBFS (4 dB below trigger)")