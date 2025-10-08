const unsigned long interval = 10000;  // 10 seconds
unsigned long previousMillis = 0;

void setup() {
  pinMode(13, OUTPUT);
  Serial.begin(9600);
}

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    // Tell Python
    Serial.println("ALARM");

    // LED on for 2 seconds
    digitalWrite(13, HIGH);
    delay(2000);
    digitalWrite(13, LOW);
  }
}
