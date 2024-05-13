#define SENSOR_PIN 2

unsigned long previousMillis = 0;
unsigned long notifyMillis = 0;
const long interval = 500;
const long notifyInterval = 5000;
bool motionDetected = false;

void setup() {
  pinMode(SENSOR_PIN, INPUT);
  Serial.begin(9600);
}

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
    
    int sensorValue = digitalRead(SENSOR_PIN);
    
    if (sensorValue == HIGH) {
      motionDetected = true;
    }
  }

  if (currentMillis - notifyMillis >= notifyInterval) {
    if (motionDetected) {
      Serial.println("MOTION_DETECT");
    } else {
      Serial.println("NO_MOTION");
    }

    notifyMillis = currentMillis;
    motionDetected = false;
  }
}
