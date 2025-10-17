
// ledstrip.ino — UNO R3: LED strip + buzzer (white-light rhythms) + RFID + microphone dB feedback
// Events (Serial in → display layer): ALARM_WARNING / ALARM_ON / HARD_OUT / MESSY_ON / MESSY_OFF / NOISY_ON / NOISY_OFF / QUIET_ON / END / RESET
// Events (Serial back → Hub): START / FINISH / NOISY_ON / NOISY_OFF / QUIET_ON

#define USE_NEOPIXEL 1      // 1=NeoPixel（WS2812/SK6812）；0=12V 單色燈條(PWM+MOSFET)
#define DEFAULT_PIX  30     // 燈條顆數（NeoPixel）/ Number of LEDs (NeoPixel)

#include <Arduino.h>
const int PIN_BUZZ = 8;

// ======== Buzzer ========
void buzz(int ms,int hz=1000){ tone(PIN_BUZZ,hz); delay(ms); noTone(PIN_BUZZ); }
void buzzSoon(){ buzz(150); delay(150); buzz(150); }
void buzzNow(){  buzz(800); }
void buzzFanfare(){ buzz(200,1100); delay(120); buzz(200,1200); delay(120); buzz(360,1300); }


// ======== LED (NeoPixel or 12 V single color) ========
#if USE_NEOPIXEL
  #include <Adafruit_NeoPixel.h>
  const int PIN_STRIP = 6;      // NeoPixel  / data pin
  const int NUM_PIX   = DEFAULT_PIX;
  Adafruit_NeoPixel strip(NUM_PIX, PIN_STRIP, NEO_GRB + NEO_KHZ800);
  void ledsInit(){ strip.begin(); strip.show(); }
  void ledsOff(){ for(int i=0;i<NUM_PIX;i++) strip.setPixelColor(i,0); strip.show(); }
  void ledsWhite(){ for(int i=0;i<NUM_PIX;i++) strip.setPixelColor(i, strip.Color(255,255,255)); strip.show(); }
  void flash(int n,int onMs,int offMs){ for(int i=0;i<n;i++){ ledsWhite(); delay(onMs); ledsOff(); delay(offMs);} }
  void pulse(int onMs){ ledsWhite(); delay(onMs); ledsOff(); }
#else
  const int PIN_PWM = 6; // MOSFET Gate
  void ledsInit(){ pinMode(PIN_PWM, OUTPUT); analogWrite(PIN_PWM,0); }
  void ledsOff(){ analogWrite(PIN_PWM, 0); }
  void ledsOnLvl(uint8_t lvl){ analogWrite(PIN_PWM, lvl); }
  void flash(int n,int onMs,int offMs){ for(int i=0;i<n;i++){ ledsOnLvl(255); delay(onMs); ledsOff(); delay(offMs);} }
  void pulse(int onMs){ ledsOnLvl(255); delay(onMs); ledsOff(); }
#endif


// ======== RFID (MFRC522) ========
#include <SPI.h>
#include <MFRC522.h>
const int PIN_SS  = 10;   // SDA/SS
const int PIN_RST = 9;    // RST
MFRC522 rfid(PIN_SS, PIN_RST);

// TODO: Replace with actual tag UIDs (hex)
// ⚠️ 临时方案：接受任意卡片（稍后替换真实 UID）
byte UID_START_P3[]  = {0xDE,0xAD,0xBE,0xEF};  //  P3 start
byte UID_FINISH_P1[] = {0x12,0x34,0x56,0x78};  //  P1 finish
bool hubRunning = false;
bool USE_ANY_CARD = true;  // ← 设为 false 后需要匹配 UID

bool uidEq(byte *a, byte *b, byte len){ for(byte i=0;i<len;i++){ if(a[i]!=b[i]) return false; } return true; }

// ======== Microphone relative dB ========
const int PIN_MIC = A0;
const long MIC_N = 512;      //  samples per window (~40–50 ms)
const long MIC_US = 80;      //  sampling interval (µs)
float NOISY_DB   = 72.0;     //  threshold, tweak per venue
float QUIET_DB   = 42.0;
long  NOISY_ON_MS  = 400;
long  NOISY_OFF_MS = 600;
long  QUIET_WIN_MS = 25000;
bool noisy=false; unsigned long noisyHit=0, noisyFall=0, quietAcc=0;

float readDb(){
  long sumsq=0;
  for(long i=0;i<MIC_N;i++){ int v=analogRead(PIN_MIC)-512; sumsq+=(long)v*v; delayMicroseconds(MIC_US); }
  float rms=sqrt((float)sumsq/MIC_N); if(rms<1) rms=1;
  return 20.0*log10(rms);
}

void setup(){
  pinMode(PIN_BUZZ, OUTPUT);
  Serial.begin(9600);
  ledsInit(); ledsOff();

  SPI.begin(); 
  rfid.PCD_Init();
  rfid.PCD_SetAntennaGain(rfid.RxGain_max);  // ★ 增加天线增益

  buzz(80); delay(60); buzz(80);   // power-on chirp
}

void loop(){

  // ---- RFID: detect START / FINISH tags ----
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()){
    byte *uid = rfid.uid.uidByte; 
    byte len = rfid.uid.size;
    
    // ⚠️ 临时模式：任意卡触发（调试用）
    if (USE_ANY_CARD) {
      if (!hubRunning) {
        // 任意卡 → START
        hubRunning = true;
        Serial.println("START");
        pulse(120);
        buzz(120);
      } else {
        // 再刷一次 → FINISH
        Serial.println("FINISH");
        hubRunning = false;
      }
    }
    // 正式模式：匹配 UID
    else {
      // P3 卡：启动会话
      if (!hubRunning && uidEq(uid, UID_START_P3, len)){
        hubRunning = true; 
        Serial.println("START");
        pulse(120);  // 短亮提示
        buzz(120);
      } 
      // P1 卡：结束会话
      else if (hubRunning && uidEq(uid, UID_FINISH_P1, len)){
        Serial.println("FINISH"); 
        hubRunning = false;
        // LED 庆祝由 Hub 的 END 事件控制，这里不做
      }
      // 未知卡或时机不对
      else {
        Serial.println("RFID_ERROR");
        flash(2, 100, 100);  // 红灯快闪（虽然是白光，但快闪 = 错误）
        buzz(150, 800);      // 低音错误提示
      }
    }
    
    rfid.PICC_HaltA();
    delay(500);  // 防连刷
  }

  // ---- Microphone: emit NOISY_* / QUIET_ON ----
  float dB = readDb();
  unsigned long now = millis();
  if (dB >= NOISY_DB){
    if (!noisy){ if (noisyHit==0) noisyHit=now;
      if (now - noisyHit >= (unsigned long)NOISY_ON_MS){
        noisy = true; Serial.println("NOISY_ON");
      }
    }
    quietAcc=0; noisyFall=0;
  } else {
    noisyHit=0;
    if (noisy){ if (noisyFall==0) noisyFall=now;
      if (now - noisyFall >= (unsigned long)NOISY_OFF_MS){
        noisy = false; Serial.println("NOISY_OFF");
      }
    }
    if (dB <= QUIET_DB){
      quietAcc += (MIC_N * MIC_US) / 1000;
      if (quietAcc >= (unsigned long)QUIET_WIN_MS){
        Serial.println("QUIET_ON"); quietAcc=0;
      }
    } else quietAcc=0;
  }


  // ---- Display layer: consume Hub commands (LED/buzzer) ----
  if (Serial.available()){
    String cmd = Serial.readStringUntil('\n'); cmd.trim();
    if      (cmd=="ALARM_WARNING"){ buzzSoon();  flash(2,150,150); }  // 閃2 / flash twice
    else if (cmd=="ALARM_ON")     { buzzNow();   pulse(800); }        // 亮800ms / on 800 ms
    else if (cmd=="HARD_OUT")     { buzzSoon();  flash(2,100,100); }  // 快閃2 / quick double flash
    else if (cmd=="MESSY_ON")     { buzzSoon();  flash(3,120,120); }  // 閃3 / flash three times
    else if (cmd=="MESSY_OFF")    {              ledsOff(); }         // 滅 / off
    else if (cmd=="NOISY_ON")     {              pulse(500); }        // 脈衝一次 / single pulse
    else if (cmd=="NOISY_OFF")    {              ledsOff(); }
    else if (cmd=="QUIET_ON")     {              pulse(150); }        // 輕閃一次 / gentle pulse
    else if (cmd=="RFID_ERROR")   {              flash(2,100,100); buzz(150,800); }  // 快閃+低音錯誤 / quick flash + low buzz
    else if (cmd=="END")          { buzzFanfare(); for(int i=0;i<3;i++){ pulse(180); delay(120);} }
    else if (cmd=="RESET")        {              ledsOff(); }
  }
}
