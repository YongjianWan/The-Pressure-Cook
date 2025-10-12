# User Flow & Task Structure

> 目標：**三人一起完成一盤水果沙拉**（指定切法／份量達成）。  
> 強化焦點：**社交參與、口語協作、公平輪替、秩序與安全**。  
> 節奏提示：**LED（白光節奏）＋蜂鳴**；口令：**TTS**（Soon/5→1/Now）。

---

## 1) 角色與站位（順時針輪替）

| 角色 | 主要任務 | 交付到哪裡 | 備註 |
|---|---|---|---|
| **P1｜Preparing** | 去皮、去蒂、去籽 | 放至中央 **共用托盤** | 保持砧板乾燥、刀口向內 |
| **P2｜Cut** | 切 **3 cm ± 0.5 cm** 丁（或指定切法） | 放至托盤**靠 P3** | 切塊一致 |
| **P3｜Plate & Tidy & Agenda Keeper** | 從托盤**直接上到同一盤**；同步整理 | 最終擺盤（Plate） | 每回合**開始**抽 1 張 Agenda（不宣讀），60s 內悄悄完成 |

- 站位：`P1（左砧板）｜共用托盤｜P2（右砧板）；P3 正前放終盤`  
- 輪替：`P1 → P2 → P3 → P1`（**順時針**）

---

## 2) Setup（T = −30s → 0s）

1. **閱讀 TASK**（今日水果與切法）：  
   例：蘋果 **3 cm 丁 ×16**、香蕉 **3 cm 丁 ×16**、葡萄 **對半 ×16 半**
2. **決定起始站位**（依上表）
3. **觸發點（二選一）**  
   - **P3 RFID Touch** → 系統收 **`START`**  
   - **主持人按按鈕** → 系統收 **`START`**

> **LED/蜂鳴（START）**：LED 短亮 **120ms**＋蜂鳴短嗶 **120ms**。

---

## 3) 回合節奏（**70s / 回合**）

> `工作 0–60s → 準備提醒/換位 → 交接 60–70s`

### 3.1 T = 0s｜回合開始
- **P3 私抽 1 張 Agenda**（不宣讀；60s 內完成）
- 三人依站位工作：
  - P1：準備 → **共用托盤**
  - P2：切丁 → **托盤靠 P3**
  - P3：**上盤**＋整理（可加裝飾）

> **LED（T=0）**：可不亮（安靜）或短亮 120ms（選用）

### 3.2 T = 55s − 60s｜`ALARM_WARNING`（準備提醒）
- **TTS**：「Switching tasks soon」→ **5 4 3 2 1**（每秒 1 拍）  
- **蜂鳴**：短嗶×2  
- **LED**：**閃 2 下**（150ms on / 150ms off ×2）

### 3.3 T = 60s｜`ALARM_ON`（立即換位）
- **TTS**：「Switch tasks now」 → **順時針換位**（P1→P2、P2→P3、P3→P1）  
- **蜂鳴**：長嗶 ~800ms  
- **LED**：**常亮 800ms**

### 3.4 T = 60–70s｜口頭交接（≤10/5s）
- 口訣：**剩什麼 → 下一步 → 風險**（刀滑、板濕、易滾）  
- LED：**熄滅**（避免干擾交接）

### 3.5 準備窗規則（補充）
- **第 1–3 回合**：準備窗 **10s**（**T=50** 發出 `ALARM_WARNING`）  
- **第 4 回合起**：準備窗 **5s**（**T=55** 發出 `ALARM_WARNING`）

### 3.6 回合 n+1
- **T = 0–70s**：同上（P3 再抽一張 Agenda）  
- 建議整場：**6–8 回合**（6–8 分）  
- **完成**：P1 RFID Touch → 送 **`FINISH`**

> **LED/蜂鳴（FINISH）**：**三段慶祝**（蜂鳴 1100→1200→1300Hz；LED 三段脈衝同節奏）

---

## 4) 完成後 TTS（依回合數）

- **≤ 6 回合（≤ 7:00）** — 高效率＋高互動  
  - 超準時完成，對話清楚、互助到位！  
  - 閃電節奏，輪替公平、交接乾脆！  
  - 默契滿點：一人一句說重點，合作零卡頓！  
  - 高速完成，分工清楚、情緒穩定！
- **7–8 回合（7:01–9:20）** — 穩健達標＋社交品質穩  
  - 在目標時間內完成；說得清楚、聽得專心！  
  - 準時交付；輪替有序、彼此支援不間斷！  
  - 節奏穩，交接公式好用：剩什麼、下一步、風險！  
  - 合作順、氛圍佳；需要時就開口、適時就支援！
- **9–10 回合（9:21–11:40）** — 耐心完成＋秩序與安全到位  
  - 穩穩做完；音量控制得宜、越界立刻回位！  
  - 耐心到位；隨手整理、動線順暢，收尾漂亮！  
  - 合作持續在線；每次換位都能快速就緒！  
  - 步步確實；安全細節與共同托盤秩序顧到！
- **＞ 10 回合（＞ 11:40）** — 完成任務＋引導下輪提升  
  - 任務完成！下輪試著更快口頭交接，更流暢！  
  - 做得好！多用「剩什麼→下一步→風險」，更順！  
  - 完成囉！下輪主動請求/提供小幫手，互動更熱！  
  - 收工！下次更快回共同托盤，效率再提升！

> **LED**：完成播報後只做 **三段短脈衝**，不長亮，以利收尾與拍照。

---

## 5) 三套機制（Data Flow × Boundaries × LED）

### 5.1 ① Task ALARM（Soon／5→1／Now）
**Input**：`START`（P3 RFID/按鈕）、`FINISH`（P1 RFID）  
**Process（70s）**：T=0 `ALARM_DRAW`／T=55 `ALARM_WARNING`／T=60 `ALARM_ON`／T=60–70 交接  
**Output**：TTS（Soon+倒數／Now）、蜂鳴（短/長嗶）、LED（閃2／亮800ms／三段慶祝）  
**Boundaries**：節奏獨立；`ALARM_ON` 後 ≤10s 交接；倒數先播 TTS，蜂鳴/LED 只節奏提示

### 5.2 ② Camera Messy（Marker + 允許區 ROI）
**概念**：**Marker＝要回家的物件；ROI＝停車格**。**TABLE（安全）→ SECTION（秩序）**。  
**判斷**：  
- TABLE：不在（連續 ≥0.3–0.5s）→ **`HARD_OUT`**  
- SECTION：命中允許區任一 → 合規；若先前 Messy，連續 ≥0.8s → **`MESSY_OFF`**；全未命中連續 ≥1.0s → **`MESSY_ON`**  
- 遮擋 <0.5s 忽略；**失蹤超時 >5s** → 自動清狀態（若 Messy 中先送一次 `MESSY_OFF`）  
**LED/蜂鳴**：HARD_OUT 快閃2＋短嗶×2；MESSY_ON 閃3＋短嗶×2；MESSY_OFF 熄滅

### 5.3 ③ Sound dB（吵 / 安靜）
**Input**：A0 麥克風，短窗 50–100ms  
**Process**：RMS→相對 dB；`NOISY_ON`（≥70–75 dB 且 ≥400ms）／`NOISY_OFF`（回落 ≥600ms）／`QUIET_ON`（≤40–45 dB 且 ≥25–30s，一次性）  
**Output**：NOISY_ON（TTS＋LED 0.5s 脈衝）；NOISY_OFF（靜默）；QUIET_ON（TTS＋LED 150ms 輕閃）  
**仲裁**：`NOISY_ON > HARD_OUT > MESSY_ON > QUIET_ON > NORMAL`（**HARD_OUT 不延後**）

---

## 6) 硬體與檔案（單板）

- **RFID（MFRC522）**：SDA/SS=D10、SCK=D13、MOSI=D11、MISO=D12、RST=D9、3.3V/GND  
- **按鈕**：D2（INPUT_PULLUP）↔ GND  
- **蜂鳴**：D8→+、GND→−  
- **LED**：NeoPixel（D6 資料）或 12V 單色（D6 PWM→MOSFET）  
- **麥克風**：AO→A0（5V/GND）  
- **相機**：USB → PC  
- **檔案**：`run_hub.py`／`ledstrip_countdown.py`／`camera.py`／`camera_works_fam.py`／`roi_calibrator.py`／`allow.json`／`zones.json`／`ledstrip.ino`

---

## 7) 現場驗收（Checklist）

- [ ] START：LED 120ms＋短嗶；Hub 收 `START`  
- [ ] 55s 倒數：每秒 1 拍、LED 閃 2、短嗶×2  
- [ ] 60s 換位：LED 亮 800ms、長嗶；交接 ≤10s  
- [ ] Messy：離位 ≥1s → `MESSY_ON`；回位 ~0.8s → `MESSY_OFF`  
- [ ] **Hard Out（NOISY 中也立即語音）**  
- [ ] **Missing Kill 5s：自動清狀態**（若 Messy 中會送一次 `MESSY_OFF`）  
- [ ] NOISY/QUIET：≥1s 吵 ⇒ `NOISY_ON`；~0.6s 安靜 ⇒ `NOISY_OFF`；25–30s 長安靜 ⇒ `QUIET_ON`  
- [ ] Finish：回合數評語；LED/蜂鳴三段慶祝
