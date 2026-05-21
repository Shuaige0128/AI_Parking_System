#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>
#include "MFRC522_I2C.h"

const byte LCD_ADDRESS = 0x27;
const byte RFID_ADDRESS = 0x28;  // Use i2c_scanner.ino to confirm this address.
const byte RFID_RST_PIN = A2;     // 4-pin I2C RC522 boards usually do not expose RST; this pin is only for the library.

LiquidCrystal_I2C lcd(LCD_ADDRESS, 16, 2);
MFRC522 rfid(RFID_ADDRESS, RFID_RST_PIN);
Servo entryGate;
Servo exitGate;

// Wiring:
// RFID SCL -> A5/SCL, SDA -> A4/SDA, V -> 3.3V, G -> GND.
// LCD SCL -> A5/SCL, SDA -> A4/SDA, VCC -> 5V, GND -> GND.
const int redLed = 13;
const int yellowLed = 12;
const int entryServoPin = 11;
const int exitServoPin = 10;
const int sensorPins[] = {2, 3, 4, 5, 6};
const int numSensors = 5;

// Safer servo pulses. 1000/2000 can hit the mechanical stop and make MG946R buzz.
// If a barrier does not fully open/close, adjust these values in small steps of 50.
const int ENTRY_CLOSED_US = 2000;
const int ENTRY_OPEN_US = 1000;
const int EXIT_CLOSED_US = 1000;  // Exit servo is mounted in reverse.
const int EXIT_OPEN_US = 2000;    // Exit servo is mounted in reverse.

unsigned long lastSpotUpdateTime = 0;
unsigned long lastRfidReadTime = 0;
String lastRfidUid = "";

String uidToString(byte *buffer, byte bufferSize) {
  String uid = "";
  for (byte i = 0; i < bufferSize; i++) {
    if (buffer[i] < 0x10) uid += "0";
    uid += String(buffer[i], HEX);
  }
  uid.toUpperCase();
  return uid;
}

void handleCommand(String cmd) {
  if (cmd == "A") {
    entryGate.writeMicroseconds(ENTRY_OPEN_US);
    digitalWrite(redLed, LOW);
  } else if (cmd == "a") {
    entryGate.writeMicroseconds(ENTRY_CLOSED_US);
  } else if (cmd == "R") {
    digitalWrite(redLed, HIGH);
  } else if (cmd == "r") {
    digitalWrite(redLed, LOW);
  } else if (cmd == "B") {
    exitGate.writeMicroseconds(EXIT_OPEN_US);
    digitalWrite(yellowLed, LOW);
  } else if (cmd == "b") {
    exitGate.writeMicroseconds(EXIT_CLOSED_US);
  } else if (cmd == "Y") {
    digitalWrite(yellowLed, HIGH);
  } else if (cmd == "y") {
    digitalWrite(yellowLed, LOW);
  } else if (cmd.startsWith("LCD:")) {
    lcd.clear();
    String msg = cmd.substring(4);
    int sep = msg.indexOf('|');
    if (sep != -1) {
      lcd.setCursor(0, 0);
      lcd.print(msg.substring(0, sep));
      lcd.setCursor(0, 1);
      lcd.print(msg.substring(sep + 1));
    } else {
      lcd.setCursor(0, 0);
      lcd.print(msg);
    }
  }
}

void readExitRfid() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  String uid = uidToString(rfid.uid.uidByte, rfid.uid.size);
  unsigned long now = millis();

  if (uid != lastRfidUid || now - lastRfidReadTime > 3000) {
    Serial.print("RFID:EXIT:");
    Serial.println(uid);
    lastRfidUid = uid;
    lastRfidReadTime = now;
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

void sendSpotStates() {
  unsigned long currentTime = millis();
  if (currentTime - lastSpotUpdateTime < 500) {
    return;
  }

  lastSpotUpdateTime = currentTime;
  Serial.print("SPOTS:");
  for (int i = 0; i < numSensors; i++) {
    Serial.print((digitalRead(sensorPins[i]) == LOW) ? 1 : 0);
    if (i < numSensors - 1) Serial.print(",");
  }
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(10);

  Wire.begin();
  lcd.init();
  lcd.backlight();
  rfid.PCD_Init();

  entryGate.attach(entryServoPin);
  exitGate.attach(exitServoPin);

  pinMode(redLed, OUTPUT);
  pinMode(yellowLed, OUTPUT);
  digitalWrite(redLed, LOW);
  digitalWrite(yellowLed, LOW);
  entryGate.writeMicroseconds(ENTRY_CLOSED_US);
  exitGate.writeMicroseconds(EXIT_CLOSED_US);

  for (int i = 0; i < numSensors; i++) {
    pinMode(sensorPins[i], INPUT);
  }

  lcd.print("Parking Ready");
  Serial.println("SYSTEM:READY");
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) {
      handleCommand(cmd);
    }
  }

  readExitRfid();
  sendSpotStates();
}
