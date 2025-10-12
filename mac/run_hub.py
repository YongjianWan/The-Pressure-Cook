# run_hub.py — 一鍵啟動 Hub（互動選埠）
# run_hub.py — one-click Hub launcher (interactive port picker)
import sys
import subprocess
from pathlib import Path

if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    target = script_dir / "ledstrip_countdown.py"
    cmd = [sys.executable, str(target)]
    # 也可以支援 pass-through：例 python run_hub.py --no-timer
    # Supports pass-through arguments, e.g. python run_hub.py --no-timer
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    subprocess.run(cmd)

