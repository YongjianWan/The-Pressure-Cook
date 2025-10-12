#include <Adafruit_NeoPixel.h>

#define PIN 6
#define NUMPIXELS 30
Adafruit_NeoPixel strip(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

enum State { OFF, GREEN, BLUE_BLINK, RED_BLINK, YELLOW_BLINK };
State ledState = OFF;

void setup() {
  Serial.begin(9600);
  strip.begin();
  strip.show();
}

void loop() {
  while (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "DEFAULT_GREEN") ledState = GREEN;
    else if (command == "SWITCH_TASK") ledState = BLUE_BLINK;
    else if (command == "ALARM_ON") ledState = RED_BLINK;
    else if (command == "ALARM_OFF") ledState = OFF;
    else if (command == "YELLOW_BLINK") ledState = YELLOW_BLINK;
    else if (command == "OFF") ledState = OFF;
  }

  switch (ledState) {
    case OFF:
      strip.clear();
      strip.show();
      delay(100);
      break;

    case GREEN:
      for (int i = 0; i < NUMPIXELS; i++) strip.setPixelColor(i, strip.Color(0, 255, 0));
      strip.show();
      delay(100);
      break;

    case BLUE_BLINK:
      for (int i = 0; i < NUMPIXELS; i++) strip.setPixelColor(i, strip.Color(0, 0, 255));
      strip.show();
      delay(200);
      strip.clear();
      strip.show();
      delay(200);
      break;

    case RED_BLINK:
      for (int i = 0; i < NUMPIXELS; i++) strip.setPixelColor(i, strip.Color(255, 0, 0));
      strip.show();
      delay(200);
      strip.clear();
      strip.show();
      delay(200);
      break;

    case YELLOW_BLINK:
      for (int i = 0; i < NUMPIXELS; i++) strip.setPixelColor(i, strip.Color(255, 255, 0));
      strip.show();
      delay(500);
      strip.clear();
      strip.show();
      delay(200);
      break;
  }
}
