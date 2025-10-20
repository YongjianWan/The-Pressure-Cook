# Stir Wars - 厨房监控系统 v0.2

> **状态：能跑，但没联调过**

## 文件结构（只看这几个）

```
mac/                          # 主要代码都在这
├── run_hub.py               # 启动这个（Hub 服务器）
├── ledstrip_countdown.py    # Hub 核心（定时器+串口+语音）
├── camera.py                # 摄像头监控（ArUco 追踪）
├── camera_works_fam.py      # 测试工具（看摄像头能不能识别）
├── roi_calibrator.py        # 标定工具（画监控区域）
├── allow.json               # 配置：哪个标记允许在哪个区域
└── zones.json               # 配置：监控区域坐标
arduino/
└── ledstrip.ino             # Arduino 代码（LED+蜂鸣器+麦克风+RFID）
anya_sammy work/             # 旧代码，可以忽略
```

---

## 硬件连接（Arduino Uno）

```
Arduino
├─ Pin 6  → NeoPixel 灯带（数据线）
├─ Pin 8  → 蜂鸣器 +
├─ Pin 9  → RFID RST
├─ Pin 10 → RFID SDA/SS
├─ A0     → 麦克风模块 A0
├─ 5V     → RFID VCC + 麦克风 VCC
└─ GND    → 公共地（LED/蜂鸣/麦克风/RFID）

USB → 电脑（COM5 或类似）
摄像头 → 电脑 USB
```

**NeoPixel 接线：**

- 红线 → 5V
- 黑线 → GND
- 绿线 → Pin 6

---

```bash
pip install opencv-contrib-python pyserial
```

### 2. 上传 Arduino 代码

```bash
# 用 Arduino IDE 或命令行
arduino-cli compile --fqbn arduino:avr:uno arduino/
arduino-cli upload --fqbn arduino:avr:uno --port COM5 arduino/
```

### 3. 启动 Hub（终端 1）

```bash
cd mac
python run_hub.py
# 会列出串口，按 Enter 选第一个（通常是 Arduino）
```

### 4. 测试摄像头（终端 2）

```bash
cd mac
python camera_works_fam.py
# 按 ESC 或 Q 退出
```

### 5. 实际运行（终端 2）

```bash
cd mac
python camera.py
# Hub 必须已经在运行
```

---

## 配置文件（必须先搞定）

### `zones.json` - 监控区域

**首次使用必须标定！**

- 左键点击画多边形（至少 3 个点）
- 右键完成，输入区域名（TABLE / TRAY / PLATE）
- `U` 撤销点，`Z` 删除区域，`S` 保存，`Q` 退出

**必须有的区域：**

- `TABLE` - 桌面边界（红色）
- `TRAY` - 托盘区域（绿色）
- `PLATE` - 盘子区域（绿色）

### `allow.json` - 标记权限

```json
{
  "10": ["TRAY"], // 标记10只能在托盘
  "20": ["PLATE"], // 标记20只能在盘子
  "30": ["TRAY", "PLATE"] // 标记30两个区域都行
}
```

---

## 工作流程

```
┌─────────────┐
│ 打印 ArUco  │ 标记（mac/markers/ 目录下）
│ 贴到工具上  │ 刀/削皮器/勺子/盘子
└──────┬──────┘
       │
┌──────▼──────┐
│ 标定区域    │ python roi_calibrator.py
│ zones.json  │ 圈出 TABLE/TRAY/PLATE
└──────┬──────┘
       │
┌──────▼──────┐
│ 启动 Hub    │ python run_hub.py
│ 选串口 COM5 │
└──────┬──────┘
       │
┌──────▼──────┐
│ 启动摄像头  │ python camera.py
│ 开始监控    │ 或先用 camera_works_fam.py 测试
└─────────────┘
```

---

## 事件说明（UDP 消息）

Camera → Hub (127.0.0.1:8787) → Arduino (Serial)

| 事件            | 触发条件             | LED 反应    | 语音                 |
| --------------- | -------------------- | ----------- | -------------------- |
| `HARD_OUT`      | 工具掉出桌面 ≥0.4s   | 蓝灯闪 2 次 | "Tool outside table" |
| `MESSY_ON`      | 工具离开允许区 ≥1.0s | 红灯闪 3 次 | "Messy detected"     |
| `MESSY_OFF`     | 工具回到允许区 ≥0.8s | 熄灯        | -                    |
| `NOISY_ON`      | 噪音 ≥72dB 且 ≥0.4s  | 红灯常亮    | "Too noisy"          |
| `QUIET_ON`      | 安静 ≤42dB 且 ≥30s   | 轻闪 1 次   | "Good silence"       |
| `ALARM_WARNING` | 定时器 T=55s         | 闪 2 次     | "5, 4, 3, 2, 1"      |
| `ALARM_ON`      | 定时器 T=60s         | 亮 800ms    | "Switch tasks now"   |

**优先级：** `NOISY_ON > HARD_OUT > MESSY_ON > QUIET_ON`

---

## 常见问题

### Q: 摄像头识别不到 ArUco 标记？

**A:**

1. 标记太小（至少 5cm × 5cm）
2. 光线不足或反光
3. 标记模糊（打印质量差）
4. 字典不匹配（代码用 `DICT_5X5_100`，标记也必须是）

### Q: 串口被占用（Permission Error）？

**A:**

```bash
taskkill //F //IM python.exe
```

或者重新插拔 Arduino USB 线。

### Q: 窗口卡死关不掉？

**A:** 按 Ctrl+C 或者强制杀进程。已经加了异常处理，应该不会卡了。

### Q: LED 不亮？

**A:**

1. 检查 NeoPixel 接线（Pin 6 / 5V / GND）
2. Arduino 代码里 `NUM_PIX` 改成你的灯珠数量
3. 用万用表测 Arduino Pin 6 有没有信号

### Q: 麦克风一直触发？

**A:** Arduino 代码里调 `NOISY_DB` 阈值（默认 72.0），或者转麦克风上的电位器（顺时针 = 降低灵敏度）。

### Q: RFID 读不到卡？

**A:**

1. 检查接线（尤其 3.3V 别接错成 5V）
2. Arduino 代码里改 `UID_START_P3` / `UID_FINISH_P1` 为实际卡片 UID
3. 打开串口监视器（9600 baud）看有没有读卡日志

---

## 已知问题（TODO）

- [ ] **Arduino 代码未实测**（写了但没上传验证过）
- [ ] **RFID UID 是假的**（`0xDEADBEEF` 占位符，要换成真卡）
- [ ] **没做完整联调**（Hub + Camera + Arduino 同时跑）
- [ ] **麦克风阈值未校准**（需要现场调）
- [ ] **zones.json 是空的**（需要现场标定）
- [ ] **失踪超时（5s）逻辑未测**
- [ ] **优先级仲裁未完全验证**

---

## 架构图（给懂的人看）

```
┌─────────────────────────────────────────────┐
│  camera.py (OpenCV + ArUco)                 │
│  ├─ 检测 TABLE 边界                          │
│  ├─ 检测 SECTION 允许区                      │
│  ├─ 去抖（<0.5s 忽略，>5s 清状态）            │
│  └─ UDP 发事件 → 127.0.0.1:8787             │
└──────────────────┬──────────────────────────┘
                   │ UDP
┌──────────────────▼──────────────────────────┐
│  run_hub.py / ledstrip_countdown.py         │
│  ├─ UDP 监听 (8787)                         │
│  ├─ 70s 定时器（前3回合 50s 警告，后续 55s）  │
│  ├─ 优先级队列                               │
│  ├─ TTS 语音（macOS say / Windows pyttsx3） │
│  └─ Serial 转发 → Arduino                   │
└──────────────────┬──────────────────────────┘
                   │ Serial @ 9600 baud
┌──────────────────▼──────────────────────────┐
│  arduino/ledstrip.ino                       │
│  ├─ NeoPixel LED 控制（Pin 6）               │
│  ├─ 蜂鸣器（Pin 8）                          │
│  ├─ 麦克风 dB 监控（A0）                     │
│  ├─ RFID 读卡（Pin 10 SS / Pin 9 RST）      │
│  └─ Serial 回传事件（NOISY/QUIET/START）     │
└─────────────────────────────────────────────┘
```

---

## 团队成员看这里

**不懂代码？没关系，你只需要：**

1. **运行脚本** → 复制上面的命令，粘贴到终端，按回车
2. **标定区域** → 用鼠标点点点，圈出桌子和托盘
3. **打印标记** → `mac/markers/` 里的 PNG 文件，打印出来贴到工具上
4. **调麦克风** → 转电位器，正常说话不触发，喊叫触发
5. **有问题？** → Ctrl+C 停掉，重新跑一遍

**不要：**

- 不要同时打开两个摄像头程序（会冲突）
- 不要手动改代码（除非你知道自己在干什么）
- 不要删 `.json` 文件（那是配置）

---

## 参考文档

- `technical doc ver0.3.md` - 技术规格（有点过时，代码和文档不完全一致）
- `User-Flow-and-Task-Structure.md` - 用户流程（最新，和代码匹配）

---

## License

这是学校课程作业（DECO3500），不是生产代码。
用它之前三思，出了事儿别找我们。

---

**最后更新：** 2025-10-10
**状态：** 各模块独立可用，集成测试 TBD
**下一步：** 上传 Arduino 代码 → 标定 ROI → 联调

---

Aiden Wan

### 1. 确认系统 Python 确实带包

```bash
python -c "import cv2,serial,pyttsx3,platform;print('ok')"
```

只要回显 `ok` 就继续，报错就 `pip install 缺的包` 一把梭。

---

### 2. 一键跑 Hub（不挑端口，自动选）

```bash
cd mac
python run_hub.py
```

出现端口列表后 **直接回车**（默认 0 号）。
如果 Arduino 在 COM5 而列表里 COM5 是 0 号，就回车；不是 0 号就敲对应数字再回车。

---

### 3. 一键跑摄像头（调试模式，只看不发事件）

```bash
cd mac
python camera_works_fam.py
```

窗口弹出后把 ArUco 标记放镜头前，能看到红框 + ID 就说明识别正常。
**退出**：按 `Q` 或 `ESC` 或直接把窗口 ❌ 掉。

---

### 4. 一键跑完整监控（发 UDP 给 Hub）

```bash
cd mac
python camera.py
```

**前提**：Hub 必须先跑着（第 2 步）。
摄像头会把 `HARD_OUT` / `MESSY_ON/OFF` 发到 Hub，Hub 再转串口 → Arduino → LED 闪。

---

### 5. 上传 Arduino 代码（一次就行）

```bash
arduino-cli compile --fqbn arduino:avr:uno arduino/ledstrip
arduino-cli upload -p COM5 --fqbn arduino:avr:uno arduino/ledstrip
```

把 `COM5` 换成你电脑上的实际端口。
上传成功会看到 **"Done uploading"**；失败就换端口再试。

---

### 6. 常见报错速查

| 报错                                   | 秒解                                |
| -------------------------------------- | ----------------------------------- |
| `ModuleNotFoundError: cv2`             | `pip install opencv-contrib-python` |
| `ModuleNotFoundError: serial`          | `pip install pyserial`              |
| `ModuleNotFoundError: pyttsx3`         | `pip install pyttsx3`               |
| `bash: python: command not found`      | 关终端重开，或 `winpty python`      |
| `SerialException: could not open port` | 端口被占 → 拔插 USB 或重启电脑      |

---

### 7. 现场 5 分钟 checklist（demo 前）

1. Arduino 插好 → 上传 [`ledstrip.ino`](arduino/ledstrip/ledstrip.ino) ✅
2. 打印 ArUco 标记（`markers/` 里 PNG）→ 贴工具 ✅
3. 运行 [`roi_calibrator.py`](mac/roi_calibrator.py) → 鼠标圈区域 → 按 `S` 保存 ✅
4. 终端 1：`python run_hub.py` → 回车 ✅
5. 终端 2：`python camera.py` → 窗口出现 ✅
6. 把工具拿出/放回区域 → LED 应该闪 ✅

---

更新时间 2024-10-11 00:42
