# Core Logic & Implementation

> 把使用者流程轉成可落地、可維護的**技術規格**。  
> 特色：**單板（UNO R3）**、**LED 白光節奏**、**相機 ArUco + ROI**、**分貝門檻**、**跨平台 Hub（Mac/Win）**、**不衝突啟動**、**Hub 變體（前 3 回合 10 秒，其後 5 秒）**。

---

## 0. 架構（Architecture）

- **Hub / Event Center（`ledstrip_countdown.py`）**
  - 唯一開啟 Arduino 序列埠的程式（9600 bps）
  - 接收相機節點透過 UDP (`127.0.0.1:8787`) 送來的事件，整理後 forward 給 Arduino
  - 負責跨平台 TTS（macOS `say`、Windows `pyttsx3`）與 70 秒回合計時、事件仲裁

- **Camera 節點（`camera.py`）**
  - 追蹤 ArUco Marker 在預設 ROI（TABLE → SECTION）中的位置
  - 去抖 Messy / Hard Out 狀態，再以 UDP 事件送到 Hub
  - 完全在電腦端執行（不開 Serial），多感測器也不會佔用序列埠

- **Arduino 顯示層（`ledstrip.ino`）**
  - 透過 Serial 接收 Hub 的事件字串並驅動 LED / 蜂鳴節奏
  - 把 RFID（`START` / `FINISH`）與麥克風噪音狀態回報給 Hub
  - 同一韌體支援 NeoPixel 與 12V 單色燈條

**訊號流**

| Source | 介面 | Destination | 用途 |
| --- | --- | --- | --- |
| `camera.py` | UDP 127.0.0.1:8787 | Hub | `HARD_OUT`、`MESSY_ON/OFF` 等事件 |
| Hub | Serial 9600 | Arduino | LED / 蜂鳴命令（`ALARM_*`、`NOISY_*`…） |
| Arduino | Serial 9600 | Hub | RFID 與麥克風事件（`START`、`FINISH`、`NOISY_ON/OFF`、`QUIET_ON`） |

---

## 1. 事件總線（Event Bus）

### 1.1 PC → Arduino（顯示層）
`ALARM_WARNING`, `ALARM_ON`, `HARD_OUT`, `MESSY_ON`, `MESSY_OFF`, `NOISY_ON`, `NOISY_OFF`, `QUIET_ON`, `END`, `RESET`

> LED/蜂鳴（白光節奏，不用顏色）：  
> - `ALARM_WARNING`：閃 2（150/150），短嗶×2  
> - `ALARM_ON`：亮 800ms，長嗶  
> - `HARD_OUT`：快閃 2（100/100），短嗶×2  
> - `MESSY_ON`：閃 3（120/120），短嗶×2  
> - `MESSY_OFF`：熄滅  
> - `NOISY_ON`：脈衝 500ms（蜂鳴可選）  
> - `QUIET_ON`：脈衝 150ms  
> - `END`：三段慶祝

### 1.2 Arduino → PC（回報）
`START`, `FINISH`, `NOISY_ON`, `NOISY_OFF`, `QUIET_ON`

### 1.3 相機 → Hub（UDP 127.0.0.1:8787）
`HARD_OUT`, `MESSY_ON`, `MESSY_OFF`

---

## 2. Hub（`ledstrip_countdown.py`）

### 2.1 職責
- **唯一開 Serial**、**TTS**、**70s 計時**（Soon/5→1/Now）、**UDP 匯流**
- **語音仲裁優先序**：`NOISY_ON > HARD_OUT > MESSY_ON > QUIET_ON > NORMAL`
  - **HARD_OUT 永不延後**（即使 `NOISY_ON`）  
  - Task `ALARM_*` 照時間；撞噪音時**語音可延後**，**事件仍 forward**（LED/蜂鳴照節奏）

### 2.2 變體：前 3 回合 10 秒，其後 5 秒
- Hub 維持 `CYCLE=70`、`SWITCH=60`  
- **回合 0–2**：`WARN_AT=50`（10s 準備）  
- **回合 ≥3**：`WARN_AT=55`（5s 準備）  
- 在 `tick_timer()` 依 `self.round_idx` 切換 `warn_at`；送出 `ALARM_ON` 後 `self.round_idx += 1`；收到 `START` 時 `self.round_idx = 0`

**參考實作（節錄）**

```python
# __init__
self.round_idx = 0  # 0,1,2 回合為 10 秒準備

# handle()
if msg == "START":
    self.round_idx = 0
    return

# tick_timer()
warn_at = 50.0 if self.round_idx < 3 else 55.0
...
if abs(t - warn_at) < 0.12 and now_i != self._last_warn:
    self.enqueue("ALARM_WARNING")
    self._last_warn = now_i
if abs(t - SWITCH) < 0.12 and now_i != self._last_on:
    self.enqueue("ALARM_ON")
    self._last_on = now_i
    self.round_idx += 1
```

---

## 3. Camera（`camera.py`）

### 3.1 邏輯（TABLE → SECTION、去抖、失蹤超時）
- **TABLE（安全）**：不在 TABLE 連續 ≥0.3~0.5s → `HARD_OUT`
- **SECTION（秩序）**：命中允許區任一 → 合規；若先前 Messy，連續 ≥0.8s → `MESSY_OFF`
- **全未命中**：≥1.0s → `MESSY_ON`
- **遮擋忽略**：`MISS_HIDE = 0.5s`
- **失蹤超時**：`MISSING_KILL = 5s`；自動清狀態（Messy 中先送一次 `MESSY_OFF` 以防殘留）

### 3.2 設定（JSON）
- `zones.json`：TABLE/TRAY/PLATE… 多邊形（像素座標；四邊 +10–20px；解析度變更用 `scale_zones.py` 等比縮放或 `roi_calibrator.py` 重標）
- `allow.json`：Marker ID → 允許區列表（區名需與 `zones.json` 一致）

### 3.3 相機後端（跨平台）
- mac/Linux：`cv2.VideoCapture(0)`
- Windows：`cv2.VideoCapture(0, cv2.CAP_DSHOW)`
- 解析度：1280×720@30

---

## 4. Arduino（`ledstrip.ino`）

### 4.1 LED 顯示層（白光節奏）
- `USE_NEOPIXEL=1`：NeoPixel（WS2812B/SK6812，D6 資料）
- `USE_NEOPIXEL=0`：12V 單色燈條（D6 PWM → MOSFET）
- `DEFAULT_PIX`：燈條顆數（例：30）

### 4.2 RFID（START/FINISH）
- MFRC522（SDA/SS=D10、SCK=D13、MOSI=D11、MISO=D12、RST=D9、3.3V/GND）
- `UID_START_P3[]` / `UID_FINISH_P1[]`（請填實際 UID）

### 4.3 麥克風分貝（NOISY/QUIET）
- 取樣窗：`MIC_N=512`, `MIC_US=80`（約 40–50ms）
- 門檻/去抖：`NOISY_DB=72.0`, `NOISY_ON_MS=400`, `NOISY_OFF_MS=600`, `QUIET_DB=42.0`, `QUIET_WIN_MS=25000`
- 回報事件：`NOISY_ON` / `NOISY_OFF` / `QUIET_ON`

### 4.4 顯示層 switch-case
- 依「事件總線」的 LED/蜂鳴表；白光節奏，不用顏色語義

---

## 5. JSON 介面

### 5.1 `zones.json`（例）

```json
[
  {"name": "TABLE", "pts": [[60, 60], [1220, 60], [1220, 660], [60, 660]]},
  {"name": "TRAY",  "pts": [[420, 360], [720, 360], [720, 560], [420, 560]]},
  {"name": "PLATE", "pts": [[820, 380], [1100, 380], [1100, 580], [820, 580]]},
  {"name": "P2",    "pts": [[260, 380], [400, 380], [400, 560], [260, 560]]},
  {"name": "P3",    "pts": [[1120, 380], [1210, 380], [1210, 560], [1120, 560]]}
]
```

### 5.2 `allow.json`（例）

```json
{
  "10": ["TRAY"],         "11": ["TRAY"],
  "20": ["PLATE"],        "21": ["PLATE"],
  "30": ["TRAY", "PLATE"],"31": ["TRAY", "PLATE"],
  "32": ["TRAY"],         "33": ["TRAY"],
  "40": ["P2"],           "50": ["P3", "TRAY"]
}
```

---

## 6. 跨平台差異（都已內建）

| 項目 | macOS | Windows |
| --- | --- | --- |
| TTS | `say` | `pyttsx3`（SAPI） |
| 相機後端 | 預設 | `cv2.CAP_DSHOW` |
| 序列埠 | `/dev/cu.usbmodem*` / `usbserial*` | `COMx` |
| 啟 Hub | `python mac/run_hub.py`（互動選埠；支援 `--port`/`--no-timer`） | 同指令 |

---

## 7. 驗收 Checklist（含 Hub 變體）
- **回合節奏**：前 3 回合 `WARN_AT=50`（10s 準備），其後 `WARN_AT=55`（5s 準備）；60s 換位；交接 ≤10s
- **HARD_OUT 不延後**：在 `NOISY_ON` 期間，TABLE 外 ≥0.5s 即刻語音
- **Missing Kill 5s**：Marker 失蹤 >5s 自動清狀態（若 Messy 中先送一次 `MESSY_OFF`）
- **RFID 回報**：P3=START、P1=FINISH
- **NOISY/QUIET**：≥1s 吵 ⇒ `NOISY_ON`；約 0.6s 安靜 ⇒ `NOISY_OFF`；25–30s 安靜 ⇒ `QUIET_ON`
- **LED/蜂鳴**：白光節奏與事件表一致

---

## 8. 快修（Troubleshoot）
- **序列衝突**：同時只有 Hub 開 Serial；相機走 UDP
- **相機抓不到 Marker**：字典一致（`detect_dict.py`）；解析度 1280×720；光線均勻；Marker 邊長 ≥40–60px
- **Messy 誤報**：ROI 四邊＋10–20px；`MESSY_ON_S=1.2`；回位 0.8；邊界視為內
- **噪音門檻**：調整 `NOISY_DB`/`QUIET_DB`；去抖時間視現場微調
- **ROI 對不上**：`roi_calibrator.py` 重標或 `scale_zones.py` 等比轉換
