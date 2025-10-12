"""
Example running when Audio interface mic input level is inbetween 2-4 oclocks on the volume knob.

python alarm.py --in 2 --out 5 --sr 44100 --hp 100 \
  --trig -26.9 --rel -30.9 --hold 1.0 --cooldown 7 --print

"""

import argparse, time, math, threading
import numpy as np, sounddevice as sd, queue

# High pass filter. Edit fc cutoff as needed. sr is the sample rate.
def hp1(x, sr, fc=100.0, state={'a':None,'xn1':0.0,'yn1':0.0}):
    if state['a'] is None:
        dt = 1.0/sr; RC = 1.0/(2*math.pi*fc); state['a'] = RC/(RC+dt)
    a = state['a']; xn1 = state['xn1']; yn1 = state['yn1']
    y = np.empty_like(x)
    for i, xn in enumerate(x):
        yn = a*(yn1 + xn - xn1)
        y[i] = yn
        yn1, xn1 = yn, xn
    state['xn1'], state['yn1'] = xn1, yn1
    return y

# Computes RMS over the input block and returns dBFS (normalising input to 0 dBFS)
def block_db(buf):
    rms = np.sqrt(np.mean(buf**2) + 1e-12)
    return 20*math.log10(rms + 1e-12)

# Make a beep sound for alarm
def make_beep(sr, dur=1.5, freq=880.0):
    t = np.arange(int(sr*dur))/sr
    env = np.minimum(1.0, np.arange(len(t))/(0.02*sr)) * np.exp(-3*t)   # quick A/D
    wave = 0.25*np.sin(2*np.pi*freq*t)*env
    return np.column_stack([wave, wave])

# Runs on a separate thread so playing the alarm cannot stall the input callback.
# Sets the output device
# Plays them blocking (one alarm completes before the next can start).
def player_thread_fn(q, out_dev, sr):
    sd.default.device = (None, out_dev)
    while True:
        buf = q.get()
        if buf is None: break
        sd.play(buf, sr, blocking=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in",  dest="in_dev",  type=int, required=True, help="Input device index (RØDE/Fast Track Pro)")
    ap.add_argument("--out", dest="out_dev", type=int, required=True, help="Output device index (Mac speakers)")
    ap.add_argument("--sr",  type=int, default=48000)
    ap.add_argument("--hp",  type=float, default=100.0, help="High-pass cutoff Hz (0 = off)")
    ap.add_argument("--hold", type=float, default=1.0, help="Seconds above trigger before firing")
    ap.add_argument("--cooldown", type=float, default=8.0, help="Seconds after alarm before re-arm")
    ap.add_argument("--trig", type=float, default=-28.0, help="Trigger threshold in dBFS")
    ap.add_argument("--rel",  type=float, default=-32.0, help="Release threshold in dBFS")
    ap.add_argument("--print", action="store_true", help="Print live dB and state")
    args = ap.parse_args()


    sd.default.device = (args.in_dev, args.out_dev)
    sr = args.sr
    beep = make_beep(sr)

    # Starts the output thread that will play alarms posted to q
    q = queue.Queue()
    tplayer = threading.Thread(target=player_thread_fn, args=(q, args.out_dev, sr), daemon=True)
    tplayer.start()

    # rolling window for hold logic
    # We don’t trigger on a single loud block; we require the average over a short window (--hold) to exceed --trig.

    # Each block has duration 1024 / sr seconds (at 44.1 kHz ≈ 23.2 ms).

    # blocks_needed ≈ hold / block_duration (so for --hold 1.0, ~43 blocks).
    blocks_needed = max(1, int(args.hold / (1024/sr)))
    ring = [args.rel - 20.0]*blocks_needed
    rp = 0

    state = "armed"  # armed -> fired -> cooldown
    last_fire = 0.0

    # CORE DETECTION LOGIC
    # Read audio (indata), pick channel 0
    # Apply HPF if enabled
    # Compute block dB, write it into the ring buffer, compute the moving average over the last --hold seconds
    # If --print is on, we print once per full ring rotation (≈ every --hold seconds) to avoid spam.
    def in_cb(indata, frames, time_info, status):
        nonlocal rp, state, last_fire
        if status: print(status)
        mono = indata[:,0]
        if args.hp > 0: mono = hp1(mono, sr, args.hp)
        db = block_db(mono)
        ring[rp] = db; rp = (rp + 1) % len(ring)
        avg = sum(ring)/len(ring)

        now = time.time()
        if state == "armed":
            if avg >= args.trig:
                state = "fired"
                last_fire = now
                q.put(beep)
        elif state == "fired":
            # wait for cooldown start condition
            state = "cooldown"
        elif state == "cooldown":
            # re-arm once cool and quiet
            if (now - last_fire) >= args.cooldown and avg <= args.rel:
                state = "armed"

        if args.print and (rp == 0):
            print(f"dB(avg)={avg:6.1f} | state={state}")

    # Opens the input device at your chosen sample rate.
    # Note blocksize=1024 gives ~23 ms blocks at 44.1 kHz
    # The main thread just idles; the callback runs on PortAudio’s thread; the player thread waits for beeps.
    # On Ctrl-C, we send None to the player’s queue to stop that thread cleanly.
    with sd.InputStream(samplerate=sr, channels=1, callback=in_cb, blocksize=1024, device=(args.in_dev, None)):
        print("Listening… Ctrl+C to stop.")
        try:
            while True: time.sleep(0.2)
        except KeyboardInterrupt:
            pass
        finally:
            q.put(None)

if __name__ == "__main__":
    main()
