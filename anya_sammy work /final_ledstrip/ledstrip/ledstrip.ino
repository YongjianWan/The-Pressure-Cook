#include <Adafruit_NeoPixel.h>

#define PIN 6
#define NUMPIXELS 8   // set to your strip length

Adafruit_NeoPixel strip(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  strip.begin();
  strip.show();       // all LEDs off
  Serial.begin(9600);
}

void loop() {
  // Wait 5s before warning
  delay(5000);

  Serial.println("ALARM_WARNING"); // Python starts countdown
  delay(5000);  // countdown duration

  Serial.println("ALARM_ON"); // LEDs will start blinking

  // Blink LEDs for 5 seconds
  unsigned long blinkEnd = millis() + 5000;  // end time
  while (millis() < blinkEnd) {
    // Turn LEDs on red
    for (int i = 0; i < NUMPIXELS; i++) {
      strip.setPixelColor(i, strip.Color(255, 0, 0));
    }
    strip.show();
    delay(250);  // 250ms on

    // Turn LEDs off
    strip.clear();
    strip.show();
    delay(250);  // 250ms off
  }

  Serial.println("ALARM_OFF"); // optional
  delay(5000); // off period before next cycle
}
