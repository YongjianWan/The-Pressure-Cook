#include <Adafruit_NeoPixel.h>

#define PIN 6
#define NUMPIXELS 10   // set to your strip length

Adafruit_NeoPixel strip(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  strip.begin();
  strip.show();       // initialize all LEDs to 'off'
  Serial.begin(9600); // start serial communication
}

void loop() {
  // Turn all LEDs red
  for(int i = 0; i < NUMPIXELS; i++){
    strip.setPixelColor(i, strip.Color(255,0,0));
  }
  strip.show();

  Serial.println("ALARM_ON"); // notify Python
  delay(5000);                 // keep LEDs on for 5 seconds

  // Turn all LEDs off
  for(int i = 0; i < NUMPIXELS; i++){
    strip.setPixelColor(i, strip.Color(0,0,0));
  }
  strip.show();

  Serial.println("ALARM_OFF"); // optional
  delay(5000);                 // LEDs off for 5 seconds
}
