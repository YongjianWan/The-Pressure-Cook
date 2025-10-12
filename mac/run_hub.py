# run_hub.py — 一鍵啟動 Hub（互動選埠）
# run_hub.py — one-click Hub launcher (interactive port picker)
import sys, subprocess, socket

if __name__ == "__main__":
    cmd = [sys.executable, "ledstrip_countdown.py"]
    # 也可以支援 pass-through：例 python run_hub.py --no-timer
    # Supports pass-through arguments, e.g. python run_hub.py --no-timer
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    subprocess.run(cmd)
