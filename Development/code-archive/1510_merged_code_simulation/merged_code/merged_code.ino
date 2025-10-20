#include <Adafruit_NeoPixel.h>

#define PIN 6
#define NUMPIXELS 30
Adafruit_NeoPixel strip(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

enum State { OFF, GREEN, BLUE_BLINK, RED_BLINK, YELLOW_BLINK, PINK_BLINK };
State ledState = OFF;

void setup() {
  Serial.begin(9600);
  strip.begin();
  strip.clear();
  strip.show();
}

void loop() {
  // --- Check for incoming commands ---
  while (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "DEFAULT_GREEN") ledState = GREEN;
    else if (command == "SWITCH_TASK") ledState = BLUE_BLINK;
    else if (command == "ALARM_ON") ledState = RED_BLINK;
    else if (command == "YELLOW_BLINK") ledState = YELLOW_BLINK;
    else if (command == "PINK_BLINK") ledState = PINK_BLINK;
    else if (command == "OFF") ledState = OFF;
  }

  // --- Handle LED states ---
  switch (ledState) {
    case OFF:
      strip.clear();
      strip.show();
      delay(100);
      break;

    case GREEN:
      for (int i = 0; i < NUMPIXELS; i++)
        strip.setPixelColor(i, strip.Color(0, 255, 0));
      strip.show();
      delay(100);
      break;

    case BLUE_BLINK:
      blink(0, 0, 255, 200);
      break;

    case RED_BLINK:
      blink(255, 0, 0, 250);
      break;

    case YELLOW_BLINK:
      blink(255, 255, 0, 400);
      break;

    case PINK_BLINK:
      blink(255, 50, 180, 400);
      break;
  }
}

void blink(uint8_t r, uint8_t g, uint8_t b, int wait) {
  for (int i = 0; i < NUMPIXELS; i++)
    strip.setPixelColor(i, strip.Color(r, g, b));
  strip.show();
  delay(wait);
  strip.clear();
  strip.show();
  delay(wait);
}
