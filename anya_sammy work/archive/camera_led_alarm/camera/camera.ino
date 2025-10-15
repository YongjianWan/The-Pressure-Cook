#include <Adafruit_NeoPixel.h>

#define PIN 6
#define NUMPIXELS 30

Adafruit_NeoPixel strip(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

bool alarm_on = false;

void setup() {
  Serial.begin(9600);
  strip.begin();
  strip.show();
}

void loop() {
  // --- Read serial input ---
  while (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim(); // remove any trailing newline or spaces

    if (command == "ALARM_ON") {
      alarm_on = true;
    } else if (command == "ALARM_OFF") {
      alarm_on = false;
      strip.clear();
      strip.show();
    }
  }

  // --- Blink LEDs if alarm is active ---
  if (alarm_on) {
    for (int i = 0; i < NUMPIXELS; i++) strip.setPixelColor(i, strip.Color(0, 0, 255)); // Blue
    strip.show();
    delay(200);
    strip.clear();
    strip.show();
    delay(200);
  }
}
