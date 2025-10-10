# 專案 Wiki 首頁

- [User Flow & Task Structure](User-Flow-and-Task-Structure)
- [Core Logic & Implementation](Core-Logic-and-Implementation)

> 不衝突原則：**只有 Hub（`ledstrip_countdown.py`）開啟 Arduino 的序列埠**；相機 `camera.py` 以 UDP(127.0.0.1:8787) 丟事件給 Hub。


# 水果沙拉協作系統（Mac / Windows 通用）

單板（UNO R3 相容）＋ LED Strip（白光節奏）＋ 相機 Marker 監測（ArUco）＋ 聲音分貝  
不衝突原則：只有 Hub（ledstrip_countdown.py / 透過 run_hub.py）開啟 Arduino 的序列埠；其他程式（相機等）不用開 Serial，改以 UDP(127.0.0.1:8787) 把事件丟給 Hub。

## 架構概覽

- **Hub / Event Center（`ledstrip_countdown.py`）**
  - 唯一開啟 Arduino 序列埠（9600 bps）的程式
  - 接收相機節點透過 UDP (`127.0.0.1:8787`) 丟來的事件並整理後轉發給 Arduino
  - 內建跨平台 TTS（macOS `say`、Windows `pyttsx3`）、70 秒回合計時與事件仲裁

- **Camera 節點（`camera.py`）**
  - 追蹤 ArUco Marker 在預設 ROI（TABLE → SECTION）內的位置
  - 對 Messy / Hard Out 狀態去抖後以 UDP 事件送到 Hub
  - 完全在電腦端運行（不開 Serial），避免多感測器佔用序列埠

- **Arduino 顯示層（`ledstrip.ino`）**
  - 透過 Serial 接收 Hub 事件字串並驅動 LED／蜂鳴節奏
  - 回報 RFID（`START` / `FINISH`）與麥克風噪音狀態給 Hub
  - 同一韌體支援 NeoPixel 與 12V 單色燈條

**訊號流**

| Source | 介面 | Destination | 用途 |
| --- | --- | --- | --- |
| `camera.py` | UDP 127.0.0.1:8787 | Hub | `HARD_OUT`、`MESSY_ON/OFF` 等事件 |
| Hub | Serial 9600 | Arduino | LED／蜂鳴命令（`ALARM_*`、`NOISY_*`…） |
| Arduino | Serial 9600 | Hub | RFID 與麥克風事件（`START`、`FINISH`、`NOISY_ON/OFF`、`QUIET_ON`） |

## 目錄
- 硬體需求與接線（單板）
- 安裝（Arduino / Python）
- 專案結構與檔案說明
- 設定 Marker 與 ROI（allow.json / zones.json）
- 啟動步驟（不衝突模式｜互動選擇序列埠）
- 快速驗收（5 分鐘）
- 常見問題（Troubleshoot）
- 事件表（PC↔Arduino）

## 1) 硬體需求與接線（單板）

- Arduino UNO R3 相容板 ×1（Little Bird）
- LED 燈條（擇一）
  - NeoPixel（WS2812B / SK6812，5V）：D6 → Data（串 330Ω），5V，GND（與 Arduino 共地）
  - 12V 單色燈條 + N 溝道 MOSFET：D6 → 1kΩ → Gate；LED(+)→12V；LED(−)→Drain；Source→GND；12V 與 Arduino 共地
- 蜂鳴器：D8 → +，GND → −
- （可選）RFID MFRC522：SDA/SS=D10、SCK=D13、MOSI=D11、MISO=D12、RST=D9、3.3V/GND
- （可選）麥克風模組：AO→A0（5V/GND）
- USB 攝影機：接到電腦（macOS / Windows）
- 只用 1 塊 Arduino：負責 LED/蜂鳴（顯示層），若你有整合 RFID/麥克風也可在同板處理。相機走電腦 USB。

## 2) 安裝（Arduino / Python）

### 2.1 Arduino

- 安裝 Arduino IDE：https://www.arduino.cc/en/software
- 開發板：Arduino/Genuino Uno
- 連接埠：
  - macOS：/dev/cu.usbmodemXXXX（或 /dev/cu.usbserial…）
  - Windows：COMx（若是 CH340 相容板，需先安裝 CH340 Driver）
- 上傳 arduino/ledstrip.ino
- 預設 NeoPixel：資料腳 D6、顆數 DEFAULT_PIX=30
- 若用 12V 燈條：把 #define USE_NEOPIXEL 1 改 0（D6 走 PWM → MOSFET）

### 2.2 Python（macOS / Windows）

```bash
cd Stir-Wars/mac  
# macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows（PowerShell）
# py -3.11 -m venv .venv
# . .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install opencv-contrib-python pyserial numpy
# Windows 需要 TTS 套件
# python -m pip install pyttsx3
```

TTS：macOS 用系統內建 say，Windows 用 pyttsx3（SAPI）。

## 3) 專案結構與檔案說明

```
0910/
├─ arduino/
│  └─ ledstrip.ino            # LED/蜂鳴 switch-case（白光節奏；NeoPixel/12V 兩用）
├─ mac/
│  ├─ camera.py               # ArUco + 多 ROI + 去抖 → UDP 送事件（不開 Serial）
│  ├─ camera_works_fam.py     # 檢視器（顯示 ROI 與 Marker ID；不送事件）
│  ├─ ledstrip_countdown.py   # Hub：唯一開 Serial + TTS + 70s 回合 + UDP 匯流（互動選埠）
│  ├─ run_hub.py              # 一鍵啟動 Hub（預設互動選埠；支援 --port / --no-timer）
│  ├─ roi_calibrator.py       # 滑鼠標註 ROI → zones.json
│  ├─ allow.json              # Marker ID → 允許區（TRAY/PLATE/P1/P2/P3…）
│  └─ zones.json              # ROI 多邊形（TABLE/TRAY/PLATE…）
└─ mac/tools/
   ├─ detect_dict.py          # 偵測貼紙字典（4x4_50 / 5x5_100 / 6x6_250）
   └─ scale_zones.py          # 解析度改變時，等比例縮放 zones.json
```

camera.py 讀 allow.json（ID→允許區）與 zones.json（ROI 多邊形），逐幀判斷 TABLE→SECTION；離位/回位去抖後以 UDP 送 HARD_OUT / MESSY_ON / MESSY_OFF 到 Hub。  
ledstrip_countdown.py 是唯一開 Serial 的中樞：TTS＋70s 回合＋UDP 匯流＋語音仲裁，並把事件轉給 Arduino（LED/蜂鳴）。

## 4) 設定 Marker 與 ROI（allow.json / zones.json）

### 4.1 確認貼紙字典

```bash
cd ANN_0910/mac/tools
python detect_dict.py
```

把任一貼紙對鏡頭，視窗左上會顯示：Dict: 4x4_50 / 5x5_100 / 6x6_250 與 ID: xx。  
若是 4x4_50，請把 mac/camera.py 的 DICT = aruco.DICT_5X5_100 改為 aruco.DICT_4X4_50。

### 4.2 量 Marker ID、填 allow.json

```bash
cd ANN_0910/mac
python camera_works_fam.py
```

畫面會畫出多邊形與紅字 ID；把「物件→ID」抄下來並填入 allow.json（區名要與 zones.json 名稱一致）：

```json
{
  "10": ["TRAY"],
  "11": ["TRAY"],
  "20": ["PLATE"],
  "21": ["PLATE"],
  "30": ["TRAY", "PLATE"],
  "31": ["TRAY", "PLATE"],
  "32": ["TRAY"],
  "33": ["TRAY"],
  "40": ["P2"],
  "50": ["P3", "TRAY"]
}
```

### 4.3 產出 / 調整 zones.json

- 重標（最穩）

  ```bash
  python roi_calibrator.py      # 左鍵點多邊形、右鍵/Enter 收尾命名（TABLE/TRAY/PLATE…）
  python camera_works_fam.py    # 檢視 ROI 與 ID 是否清楚
  ```

- 等比例縮放（解析度改變時）

  ```bash
  cd ANN_0910/mac/tools
  python scale_zones.py ../zones.json 1280 720 1920 1080 > ../zones.json
  ```

1280 720 為舊寬高；1920 1080 為新寬高。會自動把所有頂點等比放大。

## 5) 啟動步驟（不衝突模式｜互動選擇序列埠）

原則：只有 Hub（ledstrip_countdown.py）開啟 Arduino 的序列埠；camera.py 不開 Serial，改用 UDP(127.0.0.1:8787) 丟事件（HARD_OUT / MESSY_* / NOISY_* / QUIET_ON / ALARM_*）。

- 視窗 A：Hub（TTS＋70s 回合＋UDP 匯流｜互動選埠）

  ```bash
  cd ANN_0910/mac
  # 啟動虛擬環境（macOS：source .venv/bin/activate；Windows：.\.venv\Scripts\Activate.ps1）
  python run_hub.py
  # 會列出 /dev/cu.usbmodem* / usbserial*（mac）或 COMx（Windows）
  # 輸入數字選擇；直接 Enter ＝選第一個
  ```

  參數：
  - --port COM6 或 --port /dev/cu.usbmodem1101：不互動，直接指定埠
  - --no-timer：關閉 70s 計時，只當 TTS／事件匯流中樞

- 視窗 B：相機（ArUco → UDP）

  ```bash
  cd ANN_0910/mac
  python camera.py
  ```

不要 同時啟動任何會開同一個 Serial 的腳本（例如舊的 arduino_led_beep.py）。

## 6) 快速驗收（5 分鐘）

- 55s → TTS 倒數 5→1（每秒一拍），LED 閃 2 下，蜂鳴短嗶×2
- 60s → TTS「Now」，LED 亮 800ms，蜂鳴長嗶；≤10s 完成交接
- Messy：把貼 Marker 的小碗移出允許區 ≥1s → TTS 提醒＋LED 閃 3 下；放回 ~0.8s → LED 滅（靜默）
- Hard Out：把物件移到 TABLE 外 ≥0.5s → TTS「離開工作區」＋快閃 2 下
- Noisy：喊叫 ≥1s → TTS 噪音口令＋LED 0.5s 脈衝（正常說話不觸發）
- Finish：完成 → 完成話術（依回合數）＋LED/蜂鳴三段慶祝

## 7) 常見問題（Troubleshoot）

- 相機抓不到 Marker / ID 飄忽
  - 檢查字典（tools/detect_dict.py）是否與貼紙一致（4x4_50 / 5x5_100 / 6x6_250）
  - 解析度 1280×720；光線均勻；Marker 在畫面邊長 ≥40–60 px
  - 貼紙霧面列印、留 ≥5mm 白邊（quiet zone），避免反光
- Messy 誤報／回位仍叫
  - ROI 四邊 +10–20 px
  - 離位去抖 ≥1.2s，回位 0.8s
  - allow.json 的區名與 zones.json 名稱完全一致（大小寫相同）
  - 「點在邊界視為內」的判定要一致
- 沒有聲音或 LED 不亮
  - Hub 的 Serial 埠是否正確（互動選擇或 --port 指定）
  - 只有 Hub 開 Serial；不要同時跑會開埠的其他 Python
  - Arduino ledstrip.ino 上傳成功；燈條類型/顆數與檔案常數一致（NeoPixel/12V）
- UDP 沒反應
  - 防火牆允許 Python（Windows 第一次會跳出許可）
  - Hub 與 camera.py 均在本機 127.0.0.1:8787
  - 事件字串：HARD_OUT / MESSY_ON / MESSY_OFF / NOISY_ON / NOISY_OFF / QUIET_ON / ALARM_WARNING / ALARM_ON

## 8) 事件表（PC↔Arduino）

```
+--------+---------------+--------------------------------------+--------------------------+----------+
| 類型    | 事件字串       | TTS（語音）                           | LED（白光）               | 蜂鳴      |
+--------+--------------+--------------------------------------+--------------------------+----------+
| Task   | ALARM_WARNING | Switching tasks soon + 5→1          | 閃 2 下（150/150×2）      | 短嗶×2    |
| Task   | ALARM_ON      | Switch tasks now                    | 亮 800ms                 | 長嗶      |
| Camera | HARD_OUT      | 物件離開工作區                        | 快閃 2 下（100/100×2）     | 短嗶×2    |
| Camera | MESSY_ON      | 請把物件回共同托盤或終盤                | 閃 3 下（120/120×3）      | 短嗶×2    |
| Camera | MESSY_OFF     | （靜默）                             | 熄滅                      | （靜默）  |
| Sound  | NOISY_ON      | 太吵鬧囉…先停一下，一人一句下一步        | 脈衝 1 次（500ms）         | 可選      |
| Sound  | NOISY_OFF     | （靜默）                             | 熄滅                      | （靜默）  |
| Sound  | QUIET_ON      | 太安靜囉，請一起說下一步                | 輕閃 1 次（150ms）         | （靜默）  |
| Task   | END           | Task finished!（依回合數播評語）       | 三段脈衝                   | 三段慶祝  |
+--------+--------------+--------------------------------------+--------------------------+-----------+

+------------------------------------------------+--------------------------------------------------------------------+
| 語音仲裁優先序                                   | 備註                                                               |
+------------------------------------------------+--------------------------------------------------------------------+
| NOISY_ON > HARD_OUT > MESSY_ON > QUIET_ON > NORMAL | Task 的 ALARM_WARNING/ALARM_ON 依時序；撞 NOISY_ON 可延後語音，但事件仍照發（LED/蜂鳴按節奏走）。 |
+------------------------------------------------+--------------------------------------------------------------------+
```
