#include <Adafruit_NeoPixel.h>

#define PIN 6
#define NUMPIXELS 100

Adafruit_NeoPixel strip(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  strip.begin();
  strip.show();
  Serial.begin(9600);
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "ALARM_ON") {
      blinkRed(2000);  // blink for 2 seconds
    } 
    else if (cmd == "ALARM_OFF") {
      strip.clear();
      strip.show();
    }
  }
}

void blinkRed(unsigned long duration) {
  unsigned long endTime = millis() + duration;

  while (millis() < endTime) {
    for (int i = 0; i < NUMPIXELS; i++) {
      strip.setPixelColor(i, strip.Color(255, 0, 0));
    }
    strip.show();
    delay(250);

    strip.clear();
    strip.show();
    delay(250);
  }

  strip.clear();
  strip.show();
}
