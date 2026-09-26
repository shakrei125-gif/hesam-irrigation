#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>
#include <Keypad.h>
#include <DHT.h>
#include <Preferences.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <time.h>

// HARDWARE PINS
#define OLED_SDA        21
#define OLED_SCL        22
#define DHT_PIN         4
#define DHT_TYPE        DHT11
#define SOIL_PIN        34
#define RELAY_CH1       18 // Valve Relay
#define RELAY_CH2       19 // Door Relay

#define RELAY_ON        LOW
#define RELAY_OFF       HIGH

// MQTT
const char* mqtt_server = "broker.hivemq.com";
WiFiClient espClient;
PubSubClient mqttClient(espClient);

DHT dht(DHT_PIN, DHT_TYPE);
Preferences prefs;

// Global Variables
bool valveState = false;
bool autoSoilMode = false;
byte soilThreshold = 20;
float lastTemp = 0.0, lastHum = 0.0;
int lastSoilPercent = 0;

String wifiSSID = "";
String wifiPASS = "";

unsigned long doorOpenTimer = 0;
bool doorPulseActive = false;

void setValve(bool state) {
  valveState = state;
  digitalWrite(RELAY_CH1, valveState ? RELAY_ON : RELAY_OFF);
}

void triggerDoorRelay() {
  digitalWrite(RELAY_CH2, RELAY_ON);
  doorPulseActive = true;
  doorOpenTimer = millis();
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (int i = 0; i < length; i++) msg += (char)payload[i];

  if (msg == "VALVE_ON") setValve(true);
  else if (msg == "VALVE_OFF") setValve(false);
  else if (msg == "OPEN_DOOR") triggerDoorRelay();
  else if (msg == "AUTO_ON") autoSoilMode = true;
  else if (msg == "AUTO_OFF") autoSoilMode = false;
  else if (msg.startsWith("SET_SOIL_")) {
    soilThreshold = msg.substring(9).toInt();
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_CH1, OUTPUT);
  pinMode(RELAY_CH2, OUTPUT);
  digitalWrite(RELAY_CH1, RELAY_OFF);
  digitalWrite(RELAY_CH2, RELAY_OFF);

  prefs.begin("irrigation", false);
  wifiSSID = prefs.getString("wifi_ssid", "");
  wifiPASS = prefs.getString("wifi_pass", "");

  dht.begin();

  if (wifiSSID.length() > 0) {
    WiFi.begin(wifiSSID.c_str(), wifiPASS.c_str());
  }

  mqttClient.setServer(mqtt_server, 1883);
  mqttClient.setCallback(mqttCallback);
}

int getWiFiSignalPercentage() {
  if (WiFi.status() != WL_CONNECTED) return 0;
  int rssi = WiFi.RSSI();
  if (rssi <= -100) return 0;
  if (rssi >= -50) return 100;
  return 2 * (rssi + 100);
}

void publishStatus() {
  if (mqttClient.connected()) {
    String payload = "{\"temp\":" + String(lastTemp) +
                     ",\"hum\":" + String(lastHum) +
                     ",\"soil\":" + String(lastSoilPercent) +
                     ",\"valve\":\"" + (valveState ? "ON" : "OFF") + "\"" +
                     ",\"wifi_ssid\":\"" + WiFi.SSID() + "\"" +
                     ",\"wifi_rssi\":" + String(getWiFiSignalPercentage()) + "}";
    mqttClient.publish("hesam/irrigation/status", payload.c_str());
  }
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!mqttClient.connected()) {
      if (mqttClient.connect("ESP32_Hesam_Client")) {
        mqttClient.subscribe("hesam/irrigation/cmd");
      }
    }
    mqttClient.loop();
  }

  // Handle 2-second Pulse for Door Relay
  if (doorPulseActive && (millis() - doorOpenTimer >= 2000)) {
    digitalWrite(RELAY_CH2, RELAY_OFF);
    doorPulseActive = false;
  }

  // Read Sensors & Soil Thermostat Logic
  static unsigned long lastRead = 0;
  if (millis() - lastRead > 2000) {
    lastRead = millis();
    float t = dht.readTemperature();
    float h = dht.readHumidity();
    if (!isnan(t)) lastTemp = t;
    if (!isnan(h)) lastHum = h;

    int rawSoil = analogRead(SOIL_PIN);
    lastSoilPercent = map(rawSoil, 4095, 1500, 0, 100);
    lastSoilPercent = constrain(lastSoilPercent, 0, 100);

    // Automatic Soil Thermostat Logic
    if (autoSoilMode) {
      if (lastSoilPercent < soilThreshold && !valveState) {
        setValve(true);
      } else if (lastSoilPercent >= (soilThreshold + 5) && valveState) {
        setValve(false);
      }
    }

    publishStatus();
  }
}
