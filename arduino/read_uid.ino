// 临时上传这个代码到 Arduino，用串口监视器读出真实 UID
// 然后把读出的 UID 填回 ledstrip.ino 的第 42-43 行

#include <MFRC522.h>
#include <SPI.h>

const int PIN_SS = 10;
const int PIN_RST = 9;
MFRC522 rfid(PIN_SS, PIN_RST);

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    ;
  }  // 等待串口就绪
  delay(500);

  Serial.println("=== RFID UID Reader ===");
  Serial.println("Initializing MFRC522...");

  SPI.begin();
  rfid.PCD_Init();
  
  // ★ 硬复位 MFRC522（解决初始化问题）
  rfid.PCD_Reset();
  delay(50);
  
  // ★ 增加天线增益到最大（解决读卡失败问题）
  rfid.PCD_SetAntennaGain(rfid.RxGain_max);
  Serial.println("Antenna gain set to maximum");

  // 检查模块是否响应
  byte version = rfid.PCD_ReadRegister(rfid.VersionReg);
  Serial.print("MFRC522 Firmware Version: 0x");
  Serial.println(version, HEX);

  if (version == 0x00 || version == 0xFF) {
    Serial.println("ERROR: MFRC522 not detected! Check wiring:");
    Serial.println("  SDA  -> D10");
    Serial.println("  SCK  -> D13");
    Serial.println("  MOSI -> D11");
    Serial.println("  MISO -> D12");
    Serial.println("  RST  -> D9");
    Serial.println("  3.3V -> 3.3V (NOT 5V!)");
    Serial.println("  GND  -> GND");
    while (1);  // 停止运行
  }

  Serial.println("MFRC522 initialized successfully!");
  Serial.println("Place P3 card on reader...");
}

void loop() {
  // 持续检测卡片
  if (rfid.PICC_IsNewCardPresent()) {
    Serial.println("[DEBUG] Card detected, reading...");
    
    if (rfid.PICC_ReadCardSerial()) {
      Serial.print("✅ UID detected: byte UID[] = {");
      for (byte i = 0; i < rfid.uid.size; i++) {
        Serial.print("0x");
        if (rfid.uid.uidByte[i] < 0x10) Serial.print("0");
      Serial.print(rfid.uid.uidByte[i], HEX);
      if (i < rfid.uid.size - 1) Serial.print(",");
    }
      Serial.println("};");
      Serial.println("---");

      rfid.PICC_HaltA();
      delay(2000);  // 防连刷
    } else {
      Serial.println("⚠️ Card present but failed to read serial!");
    }
  } else {
    // 每 500ms 输出一次"等待中"，方便确认程序在运行
    static unsigned long lastPing = 0;
    if (millis() - lastPing > 500) {
      Serial.print(".");
      lastPing = millis();
    }
  }
}
