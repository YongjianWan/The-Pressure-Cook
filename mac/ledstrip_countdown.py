# ledstrip_countdown.py
# Hub / Event Center — 唯一開 Serial + TTS + 70s 回合 + UDP 匯流（Mac/Windows 通用）
# Hub / Event Center — single Serial owner + TTS + 70 s rounds + UDP hub (Mac/Windows)
#
# 特色：
# Highlights:
# - 自動掃描序列埠並「列出候選清單」→ 輸入數字選擇（Enter=第一個）
# - Auto-scan serial ports and list candidates → choose by number (Enter selects index 0)
# - --port 可強制指定、不互動；--no-timer 可關閉回合計時
# - `--port` pins a port without interaction; `--no-timer` disables the round timer
# - TTS 跨平台：mac 用 say，Windows/Linux 用 pyttsx3（失敗時降級為 print）
# - Cross-platform TTS: mac uses `say`, Windows/Linux uses `pyttsx3` (fallback to print on failure)
# - 語音仲裁優先序：NOISY_ON > HARD_OUT > MESSY_ON > QUIET_ON > NORMAL
# - Voice arbitration priority: `NOISY_ON > HARD_OUT > MESSY_ON > QUIET_ON > NORMAL`
# - HARD_OUT 安全最高：即使 NOISY_ON 期間也**不延後**語音
# - `HARD_OUT` is safety-critical: speech is never delayed even during `NOISY_ON`
# - 變體：前 3 回合準備窗 10 秒（WARN_AT=50），第 4 回合起 5 秒（WARN_AT=55）
# - Variant: rounds 0–2 warn at 50 s (10 s window), round 3+ warn at 55 s (5 s window)
# - 仍維持：只有本檔開 Serial；camera.py 以 UDP(127.0.0.1:8787) 丟事件進來
# - Rule: this module alone holds Serial; `camera.py` sends events via UDP (127.0.0.1:8787)
#
# 用法：
# Usage:
#   python ledstrip_countdown.py                  # 互動掃描 usbmodem/COM，輸入數字選
#   python ledstrip_countdown.py                  # Interactive scan usbmodem/COM; pick by number
#   python ledstrip_countdown.py --port COM6     # 指定埠（Windows）
#   python ledstrip_countdown.py --port COM6     # Specify port (Windows)
#   python ledstrip_countdown.py --port /dev/cu.usbmodem1101  # 指定埠（mac）
#   python ledstrip_countdown.py --port /dev/cu.usbmodem1101  # Specify port (mac)
#   python ledstrip_countdown.py --no-timer      # 關掉 70s 回合，只當 TTS/事件匯流
#   python ledstrip_countdown.py --no-timer      # Disable 70 s rounds; act as TTS/event hub only
#
# 事件（UDP/Serial）：
# Events (UDP / Serial):
#   IN : HARD_OUT / MESSY_ON / MESSY_OFF / NOISY_ON / NOISY_OFF / QUIET_ON / ALARM_WARNING / ALARM_ON / START / END
#   OUT: 同上（forward 到 Arduino；LED/蜂鳴在 Arduino 端實作）
#   OUT: same strings (forward to Arduino; LED/buzzer patterns live on Arduino)
#   ※ START 會重置回合計數（前 3 回合準備 10 秒，其後 5 秒）
#   ※ `START` resets the round counter (first 3 rounds = 10 s prep, afterwards 5 s)

import time
import sys
import socket
import threading
import queue
import serial
import serial.tools.list_ports
import subprocess
import argparse

# ====== 設定參數 ======
# ====== Parameters ======
CYCLE   = 70.0        # 回合長度（秒）/ Round length (sec)
SWITCH  = 60.0        # 換位點（秒）/ Swap point (sec)
UDP_HOST, UDP_PORT = "127.0.0.1", 8787

# 語音優先序（數字越小越優先）
# Voice priority (smaller number = higher priority)
PRIO = {
    'NOISY_ON': 1,
    'HARD_OUT': 2,   # ★ 安全最高，永不延後 / safety absolute priority, never delayed
    'MESSY_ON': 3,
    'QUIET_ON': 4,
    'ALARM_WARNING': 5,
    'ALARM_ON': 6,
    'END': 7
}

# ====== 跨平台 TTS ======
# ====== Cross-platform TTS ======
def say(txt: str, rate: int = 200):
    """macOS 用 say；Windows/Linux 用 pyttsx3；失敗時降級為 print / macOS uses say; Windows/Linux uses pyttsx3; fallback prints."""
    if sys.platform == "darwin":
        try:
            subprocess.run(["say", "-r", str(rate), txt], check=False)
        except Exception:
            print(f"[TTS] {txt}")
    else:
        try:
            import pyttsx3
            eng = pyttsx3.init()
            eng.setProperty('rate', rate)
            eng.say(txt)
            eng.runAndWait()
        except Exception:
            print(f"[TTS] {txt}")

# ====== 掃描 / 互動選擇序列埠 ======
# ====== Scan / interactively choose serial port ======
def scan_ports():
    ports = list(serial.tools.list_ports.comports())
    pref, others = [], []
    for p in ports:
        nameL = (f"{p.device} {p.description} {p.hwid}").lower()
        # 常見關鍵字：Arduino、usbmodem、usbserial、CH340、Silabs
        # Common keywords: Arduino, usbmodem, usbserial, CH340, Silabs
        if any(k in nameL for k in ["arduino", "usbmodem", "usbserial", "ch340", "silabs"]):
            pref.append(p)
        else:
            others.append(p)
    return pref + others

def pick_port_interactive():
    cand = scan_ports()
    if not cand:
        print("[Hub] No serial ports detected. Please connect the Arduino.")
        return None
    print("\n[Hub] Detected serial ports (enter index; press Enter for 0):")
    for i, p in enumerate(cand):
        print(f"  [{i}] {p.device}  |  {p.description}")
    try:
        sel = input("Select port index: ").strip()
    except EOFError:
        sel = ""
    if sel == "":
        idx = 0
    else:
        try:
            idx = int(sel)
            if idx < 0 or idx >= len(cand):
                print("[Hub] Index out of range. Defaulting to 0.")
                idx = 0
        except ValueError:
            print("[Hub] Non-numeric input. Defaulting to 0.")
            idx = 0
    return cand[idx].device

# ====== Hub 實作 ======
# ====== Hub Implementation ======
class Hub:
    def __init__(self, port: str, baud: int = 9600, use_timer: bool = True):
        self.port = port
        self.baud = baud
        print(f"[Hub] Opening serial port: {self.port}")
        self.ser  = serial.Serial(self.port, self.baud, timeout=0.1)

        # 事件佇列（優先序）
        # Priority event queue
        self.q    = queue.PriorityQueue()

        # 狀態
        # State tracking
        self.noisy      = False
        self.round_idx  = 0        # ★ 回合計數：0、1、2 回合準備 10s；之後 5s / round index with 10 s prep for first 3 rounds
        self.use_timer  = use_timer
        self._start_time= time.monotonic()
        self._last_warn = -1
        self._last_on   = -1

        # UDP listener（camera.py / 其他腳本丟事件進來）
        # UDP listener for camera.py and other publishers
        th = threading.Thread(target=self._udp_listen, daemon=True)
        th.start()

        # （可選）Arduino 回傳事件監聽
        # Optional: monitor Arduino feedback events
        th2 = threading.Thread(target=self._serial_listen, daemon=True)
        th2.start()

    # ----- 通訊 -----
    # ----- Communications -----
    def _udp_listen(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((UDP_HOST, UDP_PORT))
        print(f"[Hub] Listening for UDP events on {UDP_HOST}:{UDP_PORT}")
        while True:
            data, _ = s.recvfrom(1024)
            msg = data.decode(errors='ignore').strip()
            self.enqueue(msg)

    def _serial_listen(self):
        while True:
            m = self.ser.readline().decode(errors='ignore').strip()
            if m:
                self.enqueue(m)

    def forward(self, msg: str):
        """轉發事件到 Arduino（LED/蜂鳴在 Arduino 端處理） / Forward event to Arduino (LED/buzzer handled there)."""
        self.ser.write((msg + "\n").encode())

    # ----- 事件處理 -----
    # ----- Event handling -----
    def enqueue(self, msg: str):
        if msg in PRIO:
            self.q.put((PRIO[msg], time.time(), msg))
        else:
            # 未列入 PRIO 的雜訊忽略
            # Ignore unknown / noisy events
            pass

    def handle(self, msg: str):
        """語音仲裁 + forward 到 Arduino；HARD_OUT 安全最高不延後 / Voice arbitration + forward; HARD_OUT never delayed."""
        # ★ START：重置回合
        # ★ `START`: reset round state
        if msg == 'START':
            self.round_idx  = 0
            self._start_time= time.monotonic()
            self._last_warn = -1
            self._last_on   = -1
            # 可選：播提示
            # Optional: play start prompt
            # say('Session start.', rate=190)
            return

        if msg == 'NOISY_ON':
            self.noisy = True
            say('Too noisy… pause and take turns.', rate=190)
            self.forward('NOISY_ON')
            return

        if msg == 'NOISY_OFF':
            self.noisy = False
            self.forward('NOISY_OFF')
            return

        if msg == 'HARD_OUT':
            # ★ 安全最高優先：即使 NOISY 中也要立刻語音＋forward
            say('Object left the work area.', rate=190)
            self.forward('HARD_OUT')
            return

        if msg == 'MESSY_ON':
            if not self.noisy:
                say('Please return items to the shared tray or final plate.', rate=190)
            self.forward('MESSY_ON')
            return

        if msg == 'MESSY_OFF':
            self.forward('MESSY_OFF')
            return

        if msg == 'QUIET_ON':
            if not self.noisy:
                say('Too quiet, say the next step together.', rate=190)
            self.forward('QUIET_ON')
            return

        if msg == 'ALARM_WARNING':
            # 倒數：每秒一拍；噪音中可延後語音，但事件仍 forward
            if not self.noisy:
                say('Switching tasks soon.', rate=190)
                for n in ['5','4','3','2','1']:
                    say(n, rate=200)
                    time.sleep(1.0)
            self.forward('ALARM_WARNING')
            return

        if msg == 'ALARM_ON':
            if not self.noisy:
                say('Switch tasks now.', rate=190)
            self.forward('ALARM_ON')
            return

        if msg == 'END':
            self.forward('END')
            say('Task finished!', rate=190)
            return

    # ----- 計時：70s；前 3 回合 10s 準備，其後 5s -----
    # ----- Timer: 70 s; first 3 rounds warn at 10 s window, then 5 s -----
    def tick_timer(self):
        """
        前 3 回合（round_idx: 0,1,2）準備窗 10s（WARN_AT=50）；
        第 4 回合起（round_idx>=3）準備窗 5s（WARN_AT=55）。
        First three rounds (round_idx 0,1,2) warn at 50 s (10 s prep);
        From round_idx >= 3 warn at 55 s (5 s prep).
        """
        warn_at = 50.0 if self.round_idx < 3 else 55.0

        t = (time.monotonic() - self._start_time) % CYCLE
        now_i = int(time.monotonic())

        # 準備提醒（只觸發一次）
        # Preparation warning (fire once)
        if abs(t - warn_at) < 0.12 and now_i != self._last_warn:
            self.enqueue('ALARM_WARNING')
            self._last_warn = now_i

        # 換位點（只觸發一次），並增加回合數
        # Swap point (fire once) and bump round counter
        if abs(t - SWITCH) < 0.12 and now_i != self._last_on:
            self.enqueue('ALARM_ON')
            self._last_on = now_i
            self.round_idx += 1   # ★ 下一回合開始 / next round

    def loop(self):
        print("[Hub] Event loop started (CTRL+C to exit)")
        while True:
            if self.use_timer:
                self.tick_timer()

            try:
                _, _, m = self.q.get(timeout=0.05)
                # 噪音期間：只延後 Messy/Quiet 的「語音」（事件仍 forward）；
                # HARD_OUT 直接交給 handle()（不延後）。
                # During NOISY mode, only delay speech for Messy/Quiet (events still forward);
                # HARD_OUT goes straight to handle() (no delay).
                if self.noisy and m in ('MESSY_ON', 'QUIET_ON'):
                    self.forward(m)
                else:
                    self.handle(m)
            except queue.Empty:
                pass

# ====== 入口 ======
# ====== Entry point ======
def main():
    ap = argparse.ArgumentParser(description="Cross-platform LED/buzzer/voice hub")
    ap.add_argument("--port", help="Specify serial port (e.g. /dev/cu.usbmodem1101 or COM6)", default=None)
    ap.add_argument("--no-timer", action="store_true", help="Disable 70 s round timer (hub-only mode)")
    args = ap.parse_args()

    port = args.port
    if not port:
        port = pick_port_interactive()
        if not port:
            print("[Hub] No usable serial port found.")
            sys.exit(1)

    hub = Hub(port=port, baud=9600, use_timer=(not args.no_timer))
    try:
        hub.loop()
    except KeyboardInterrupt:
        print("\n[Hub] Bye")

if __name__ == "__main__":
    main()
