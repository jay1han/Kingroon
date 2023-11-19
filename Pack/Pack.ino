#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <HardwareSerial.h>
#include <driver/uart.h>
#include <Esp.h>
#include <Adafruit_NeoPixel.h>

#define PIN_LIGHT   16
#define PIN_CAMERA  18
#define PIN_REED    33
#define PIN_SW1     35
#define PI_RX       37
#define PI_TX       39

#define LD_SDA      12
#define LD_SCL      11
#define PIN_SW2     9
#define PIN_RELAY   7
#define PD_RX       5
#define PD_TX       3

#define LIGHT_LEDS  30
#define CAMERA_LEDS 3

Adafruit_NeoPixel   Light(LIGHT_LEDS, PIN_LIGHT, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel   Camera(CAMERA_LEDS, PIN_CAMERA, NEO_GRB + NEO_KHZ800);

#define SSID       "HORS SERVICE"
#define PASS       "babeface00"
#define PORT       4884

void setLight(int state) {
    static int brightness = 255;

    if (state == 0) brightness = 0;
    else if (state == 1) brightness = 255;
    else brightness = 255 - brightness;
    for (int led = 0; led < LIGHT_LEDS; led++)
        Light.setPixelColor(led, Light.Color(brightness, brightness, brightness));
    Light.show();
}

void setCamera(int state) {
    static int brightness = 255;

    if (state == 0) brightness = 0;
    else if (state == 1) brightness = 255;
    else brightness = 255 - brightness;
    for (int led = 0; led < CAMERA_LEDS; led++)
        Camera.setPixelColor(led, Light.Color(brightness, brightness, brightness));
    Camera.show();
}

void doorOpen() {
    setCamera(1);
    setLight(1);
}

void doorClosed() {
    setCamera(0);
    setLight(0);
}

void switch1Action() {
    setLight(-1);
}

void switch2Action() {
    setCamera(-1);
}

void setup() {
    Serial.begin(2000000);
    Serial.println("START");
    delay(2000);
    Serial.println("START");

    Light.begin();
    Light.clear();
    Camera.begin();
    Camera.clear();
    setLight(1);
    setCamera(1);

    pinMode(PIN_REED, INPUT_PULLUP);
    pinMode(PIN_SW1,  INPUT);
    pinMode(PIN_SW2,  INPUT);
    pinMode(PIN_RELAY, OUTPUT_OPEN_DRAIN);
    digitalWrite(PIN_RELAY, LOW);
                    
    Wire.setPins(LD_SDA, LD_SCL);
    if (!Wire.begin()) {
        Serial.println("I2C init failed");
    }

    WiFi.begin(SSID, PASS);
    Serial.printf("WiFi \"%s\" ", SSID);
    int wait = 0;
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        if (++wait > 20) {
            Serial.println(" Failed! Rebooting");
            delay(1000);
            ESP.restart();
        }
        Serial.print(".");
    }
    Serial.print("OK IP=");
    Serial.println(WiFi.localIP());

    uart_set_pin(UART_NUM_1, 3, 5, -1, -1);
    Serial1.begin(115200);
}

#define DOOR_OPEN     1
#define DOOR_CLOSED   0
#define SW_TOUCHED    1
#define SW_LIFTED     0
#define STALE         0

int Reed = DOOR_OPEN, Switch1 = SW_LIFTED, Switch2 = SW_LIFTED;
unsigned int ReedDebounce = STALE, Debounce1 = STALE, Debounce2 = STALE;

void loop() {
    // Debounce Door both ways
    if (digitalRead(PIN_REED) == 0) { // Door closed
        if (Reed == DOOR_CLOSED) {
            if (ReedDebounce != STALE && millis() > ReedDebounce) {
                ReedDebounce = STALE;
                doorClosed();
            }
        } else if (Reed == DOOR_OPEN) {
            ReedDebounce = millis() + 1000;
            Reed = DOOR_CLOSED;
        }
    } else { // Door open
        if (Reed == DOOR_OPEN) {
            if (ReedDebounce != STALE && millis() > ReedDebounce) {
                ReedDebounce = STALE;
                doorOpen();
            }
        } else if (Reed == DOOR_CLOSED) {
            ReedDebounce = millis() + 1000;
            Reed = DOOR_OPEN;
        }
    }

    // Debounce switches only when touched
    if (digitalRead(PIN_SW1) == 0) { // Switch lifted
        if (Switch1 == SW_TOUCHED) {
            Serial.println("Switch1 left");
            Switch1 = SW_LIFTED;
            Debounce1 = STALE;
        }
    } else { // Switch touched
        if (Switch1 == SW_TOUCHED) {
            if (Debounce1 != STALE && millis() > Debounce1) {
                Debounce1 = STALE;
                switch1Action();
            }
        } else if (Switch1 == SW_LIFTED) {
            Serial.println("Switch1 landed");
            Debounce1 = millis() + 100;
            Switch1 = SW_TOUCHED;
        }
    }

    if (digitalRead(PIN_SW2) == 0) { // Switch lifted
        if (Switch2 == SW_TOUCHED) {
            Serial.println("Switch2 left");
            Switch2 = SW_LIFTED;
            Debounce2 = STALE;
        }
    } else { // Switch touched
        if (Switch2 == SW_TOUCHED) {
            if (Debounce2 != STALE && millis() > Debounce2) {
                Debounce2 = STALE;
                switch2Action();
            }
        } else if (Switch2 == SW_LIFTED) {
            Serial.println("Switch2 landed");
            Debounce2 = millis() + 100;
            Switch2 = SW_TOUCHED;
        }
    }

    // WiFi here
}
