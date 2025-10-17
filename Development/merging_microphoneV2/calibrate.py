# To run calibrate run: python3 calibrate.py --in <input device index> --sr 44100 --seconds 20 --hp 100
# Example: python3 calibrate.py --in 2 --sr 44100

import json, time, math, numpy as np, sounddevice as sd
import argparse, statistics as stats

# list_devices
print(json.dumps(sd.query_devices(), indent=2))
print("\nDefault devices (in, out):", sd.default.device)
print("Default samplerate:", sd.query_devices(sd.default.device[0])["default_samplerate"])

# Get a read on the current noise level of the room that we are in


# High pass filter. Edit fc cutoff as needed. sr is the sample rate.
def hp1(x, sr, fc=100.0, z=[0.0], xprev=[0.0]):
    # 1st-order high-pass: y[n] = a*(y[n-1] + x[n] - x[n-1])
    # a = RC/(RC+dt), RC=1/(2*pi*fc)
    dt = 1.0/sr; RC = 1.0/(2*math.pi*fc); a = RC/(RC+dt)
    y = np.empty_like(x)
    xn1 = xprev[0]; yn1 = z[0]
    for i, xn in enumerate(x):
        yn = a*(yn1 + xn - xn1)
        y[i] = yn
        yn1, xn1 = yn, xn
    z[0], xprev[0] = yn1, xn1
    return y

# Computes RMS over the input block and returns dBFS (normalising input to 0 dBFS)
def block_db(buf):
    rms = np.sqrt(np.mean(buf**2) + 1e-12)
    return 20*math.log10(rms + 1e-12)


# Define CLI Arguments 

# --in: device index for your input (from device list).

# --sr: sample rate (44100 for FastTrack Pro).

# --seconds: how long to listen during calibration (default 20 s).

# --hp: HPF cutoff in Hz (0 disables HPF).

p = argparse.ArgumentParser()
p.add_argument("--in", dest="in_dev", type=int, required=True)
p.add_argument("--sr", dest="sr", type=int, default=48000)
p.add_argument("--seconds", type=int, default=20)
p.add_argument("--hp", type=float, default=100.0, help="High-pass Hz")
args = p.parse_args()

sd.default.device = (args.in_dev, None)
sr = args.sr
vals = []


# Apply HPF if enabled and convert to dBFS and append to vals
def cb(indata, frames, time_info, status):
    if status: print(status)
    mono = indata[:,0]
    if args.hp > 0: mono = hp1(mono, sr, args.hp)
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
print(f"  trigger ~ {p95+6:.1f} dBFS")
print(f"  release ~ {p95+2:.1f} dBFS (4 dB below trigger)")