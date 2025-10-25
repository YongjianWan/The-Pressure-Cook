#include <Adafruit_NeoPixel.h>

#define PIN 6
#define NUMPIXELS 30
Adafruit_NeoPixel strip(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

enum State { OFF, GREEN, BLUE_BLINK, RED_BLINK, YELLOW_BLINK, PINK_BLINK, WHITE_BLINK };
State ledState = OFF;

// ---- non-blocking blink state ----
bool ledOn = false;
unsigned long lastToggle = 0;
uint16_t blinkOn = 250, blinkOff = 250;

void fillColor(uint8_t r, uint8_t g, uint8_t b) {
  for (int i = 0; i < NUMPIXELS; i++) strip.setPixelColor(i, strip.Color(r, g, b));
  strip.show();
}

void enter(State s) {
  ledState = s;
  ledOn = false;
  lastToggle = millis();
  strip.clear(); strip.show();

  switch (s) {
    case BLUE_BLINK:   blinkOn = 200; blinkOff = 200; break;
    case RED_BLINK:    blinkOn = 250; blinkOff = 250; break;
    case YELLOW_BLINK: blinkOn = 350; blinkOff = 350; break;
    case PINK_BLINK:   blinkOn = 400; blinkOff = 400; break;
    case WHITE_BLINK:  blinkOn = 300; blinkOff = 300; break;
    default: break;
  }
}

void setup() {
  Serial.begin(9600);
  strip.begin();
  strip.clear();
  strip.show();
}

void handleSerial() {
  while (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "DEFAULT_GREEN") enter(GREEN);
    else if (command == "SWITCH_TASK") enter(BLUE_BLINK);
    else if (command == "ALARM_ON") enter(RED_BLINK);
    else if (command == "YELLOW_BLINK") enter(YELLOW_BLINK);
    else if (command == "PINK_BLINK") enter(PINK_BLINK);
    else if (command == "WHITE_BLINK") enter(WHITE_BLINK);   // ← new
    else if (command == "OFF") enter(OFF);
  }
}

void loop() {
  handleSerial();
  unsigned long now = millis();

  switch (ledState) {
    case OFF:
      strip.clear(); strip.show();
      break;

    case GREEN:
      fillColor(0, 255, 0);
      break;

    case BLUE_BLINK:
      if (now - lastToggle >= (ledOn ? blinkOn : blinkOff)) {
        ledOn = !ledOn; lastToggle = now;
        if (ledOn) fillColor(0, 0, 255); else { strip.clear(); strip.show(); }
      }
      break;

    case RED_BLINK:
      if (now - lastToggle >= (ledOn ? blinkOn : blinkOff)) {
        ledOn = !ledOn; lastToggle = now;
        if (ledOn) fillColor(255, 0, 0); else { strip.clear(); strip.show(); }
      }
      break;

    case YELLOW_BLINK:
      if (now - lastToggle >= (ledOn ? blinkOn : blinkOff)) {
        ledOn = !ledOn; lastToggle = now;
        if (ledOn) fillColor(255, 180, 0); else { strip.clear(); strip.show(); }
      }
      break;

    case PINK_BLINK:
      if (now - lastToggle >= (ledOn ? blinkOn : blinkOff)) {
        ledOn = !ledOn; lastToggle = now;
        if (ledOn) fillColor(255, 50, 180); else { strip.clear(); strip.show(); }
      }
      break;

    case WHITE_BLINK:
      if (now - lastToggle >= (ledOn ? blinkOn : blinkOff)) {
        ledOn = !ledOn; lastToggle = now;
        if (ledOn) fillColor(255, 255, 255); else { strip.clear(); strip.show(); }
      }
      break;
  }
}
