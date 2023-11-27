#include <Arduino.h>
#include <Wire.h>
#include <Esp.h>
#include <HardwareSerial.h>
#include <driver/uart.h>

#define PIN_SW2     0
#define PIN_SW1     1
#define PIN_REED    3
#define PIN_LIGHT   4
#define PIN_CAMERA  6
#define PIN_LCD     7
#define PI_RX       20
#define PI_TX       21
#define PIN_BUZZER  5
#define PIN_RELAY   10

#define LEDS_LIGHT  30
#define LEDS_CAMERA 3

bool isPrinting = false;
bool isPowered = false;
time_t powerTimeout = 0;
time_t buzzerCycle = 0;

typedef struct {
    int        pin;
    int        numLeds;
    rmt_obj_t  *rmtObject;
    rmt_data_t *rmtBuffer;
} Strip;
Strip Light, Camera;

void initStrip(Strip *strip, int pin, int numLeds) {
    Serial.printf("Init strip PIN%d, %d leds ", pin, numLeds);
    strip->pin     = pin;
    strip->numLeds = numLeds;
    strip->rmtBuffer = (rmt_data_t*)calloc(numLeds * 8 * 3, sizeof(rmt_data_t));
    strip->rmtObject = rmtInit(pin, RMT_TX_MODE, RMT_MEM_64);
    if (strip->rmtObject == NULL) {
        Serial.println("FAILED");
        while(true);
    }
    float tick = rmtSetTick(strip->rmtObject, 50.0);
    if (abs(tick - 50.0) > 1.0) {
        Serial.printf("tick %.0fns!\n", tick);
        while(true);
    }
    Serial.println("OK");
}

/*                                           5050 2020
  T1H 1 code, high voltage time 580ns~1us   =  12   12
  T1L 1 code, low voltage time 220ns~420ns  =   5    7
  T0H 0 code, high voltage time 220ns~380ns =   5    5
  T0L 0 code, low voltage time 580ns~1us    =  12   12
  RES Frame unit, low voltage time >280us
*/
rmt_data_t *stuffBits(rmt_data_t *data, byte level) {
    for (int bit = 7; bit >= 0; bit--) {
        if (level & (1 << bit)) {
            data->level0    = 1;
            data->duration0 = 12;
            data->level1    = 0;
            data->duration1 = 7;
        } else {
            data->level0    = 1;
            data->duration0 = 5;
            data->level1    = 0;
            data->duration1 = 12;
        }
        data++;
    }
    return data;
}

void sendStrip(Strip *strip, byte r, byte g, byte b) {
    Serial.printf("Send PIN%d: #%02X%02X%02X ", strip->pin, r, g, b);
    rmt_data_t *data = strip->rmtBuffer;
    for (int led = 0; led < strip->numLeds; led++) {
        // Green
        data = stuffBits(data, g);
        // Red
        data = stuffBits(data, r);
        // Blue
        data = stuffBits(data, b);
    }

    rmtWriteBlocking(strip->rmtObject, strip->rmtBuffer, strip->numLeds * 8 * 3);
    Serial.println("Done");
}

bool wantOK = false;
char ackMessage[8];
time_t responseTimeout = 0;
time_t heartbeatTimeout = 0;

#define CAMERA_ON       0
#define CAMERA_BRIGHT   1
#define CAMERA_DARK     2
#define CAMERA_OFF      3

void setCamera(int setMode) {
    static bool isHigh  = true;
    static bool isLight = true;

    switch (setMode) {
    case CAMERA_ON:     isHigh = true; break;
    case CAMERA_BRIGHT: isLight = true; break;
    case CAMERA_DARK:   isLight = false; break;
    case CAMERA_OFF:    isHigh = false; break;
    }

    int brightness;
    if (isHigh) {
        if (isLight) brightness = 255;
        else brightness = 40;
    }
    else brightness = 0;
    
    sendStrip(&Camera, brightness, brightness, brightness);
    Serial.printf("Camera %d\n", brightness);
}

void setLight(int setState) {
    static int state = 1;

    if (setState >= 0) state = setState;
    else state = 1 - state;
    Serial.printf("Light %s\n", state == 1 ? "on" : "off");
    sendStrip(&Light, state * 255, state * 255, state * 255);
    Serial1.printf("KR:L%d\n", state);
    setBacklight(state == 1 ? 100 : 10);
    setCamera(CAMERA_DARK + state);
}

void setBacklight(float duty) {
    Serial.printf("Backlight %.0f%\n", duty);
    int value = (int)(255.0 * duty) / 100;
    analogWrite(PIN_LCD, value);
}

void setRelay(int command) {
    static int state;
    
    Serial.printf("Relay command %d, state %d", command, state);
    if (command < 0) state = 1 - state;
    else state = command;
    Serial.printf(" -> %d\n", state);

    if (state == 1) digitalWrite(PIN_RELAY, 1);
    else digitalWrite(PIN_RELAY, 0);
    Serial1.printf("KR:R%d\n", state);
    
    isPowered = state;
    if (!isPowered) isPrinting = false;
}

#define BUZZ_OFF      0
#define BUZZ_START    1
#define BUZZ_END      2
#define BUZZ_DOOR     3
#define BUZZ_ALERT    4
#define BUZZ_NOTICE   5
#define BUZZ_ON       8
#define BUZZ_BOOT     9
#define BUZZ_CONTINUE -1

unsigned long buzzerTimer = 0;
void setBuzzer(int tone) {
    static int running = 0;
    static int cycle = 0;
    
    if (tone == 0) { // stop
        running = 0;
        Serial.println("Buzzer: stopped");
    } else if (tone == BUZZ_ON) { // on forever: no timer
        running = 0;
        Serial.println("Buzzer: on");
        analogWrite(PIN_BUZZER, 128);
    } else if (tone > 0) { // (re)start alert
        running = tone;
        cycle = 0;
        Serial.printf("Buzzer: %d\n", running);
    } // fall-through: continue
    
    if (running == 0) {
        buzzerTimer = 0;
        return;
    }
    
    switch (running) {
    case BUZZ_START: // Print started: 5 beeps
        if (cycle == 5) { // finished
            running = 0;
            analogWrite(PIN_BUZZER, 0);
        } else {
            if (cycle % 2 == 0) {
                analogWrite(PIN_BUZZER, 128);
                buzzerTimer = millis() + 200;
            } else {
                analogWrite(PIN_BUZZER, 0);
                buzzerTimer = millis() + 100;
            }
        }
        break;

    case BUZZ_END: // Print ended: 1 long beep
        if (cycle == 1) { // finished
            running = 0;
            analogWrite(PIN_BUZZER, 0);
        } else {
            analogWrite(PIN_BUZZER, 128);
            buzzerTimer = millis() + 1500;
        }
        break;

    case BUZZ_DOOR: // Door closed OK: 2 short beeps
        if (cycle == 3) { // finished
            running = 0;
            analogWrite(PIN_BUZZER, 0);
        } else {
            if (cycle % 2 == 0) {
                analogWrite(PIN_BUZZER, 255);
                buzzerTimer = millis() + 150;
            } else {
                analogWrite(PIN_BUZZER, 0);
                buzzerTimer = millis() + 50;
            }
        }
        break;
        
    case BUZZ_ALERT: // Door closed while printing: short beeps forever
        if (cycle % 2 == 0) {
            analogWrite(PIN_BUZZER, 255);
            buzzerTimer = millis() + 200;
        } else {
            analogWrite(PIN_BUZZER, 0);
            buzzerTimer = millis() + 100;
        }
        break;

    case BUZZ_NOTICE: // Door closed while powered: short beeps forever
        if (cycle % 2 == 0) {
            analogWrite(PIN_BUZZER, 255);
            buzzerTimer = millis() + 500;
        } else {
            analogWrite(PIN_BUZZER, 0);
            buzzerTimer = millis() + 500;
        }
        break;

    case BUZZ_BOOT: // Booting: one beep
        if (cycle == 1) { // finished
            running = 0;
            analogWrite(PIN_BUZZER, 0);
        } else {
            analogWrite(PIN_BUZZER, 80);
            buzzerTimer = millis() + 100;
        }
        break;
    }
    cycle ++;
}

void doorOpen() {
    Serial.println("Door open");
    strcpy(ackMessage, "KR:DO\n");
    Serial1.print(ackMessage);
    wantOK = true;
    responseTimeout = time(NULL) + 5;
    setLight(1);
    if (powerTimeout > 0) {
        powerTimeout = 0;
    }

    setBuzzer(BUZZ_BOOT);
}

void doorClosed() {
    Serial.println("Door closed");
    strcpy(ackMessage, "KR:DC\n");
    Serial1.print(ackMessage);
    wantOK = true;
    responseTimeout = time(NULL) + 5;
    setLight(0);
    
    if (isPowered) {
        if (isPrinting) {
            setBuzzer(BUZZ_ALERT);
            powerTimeout = time(NULL) + 30;
        } else {
            setBuzzer(BUZZ_NOTICE);
        }
    } else {
        setBuzzer(BUZZ_DOOR);
    }
}

void switch1Action() {
    setLight(-1);
}

void switch2Action() {
    setRelay(-1);
}

void setup() {
    Serial.begin(115200);
    Serial.println("START");
    delay(2000);
    Serial.println("START");

    initStrip(&Light, PIN_LIGHT, LEDS_LIGHT);
    initStrip(&Camera, PIN_CAMERA, LEDS_CAMERA);

    pinMode(PIN_REED,   INPUT_PULLUP);
    pinMode(PIN_SW1,    INPUT);
    pinMode(PIN_SW2,    INPUT);
    pinMode(PIN_LCD,    OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);
    pinMode(PIN_RELAY,  OUTPUT);
    digitalWrite(PIN_RELAY, 0);

    analogWriteFrequency(1001);
    analogWriteResolution(8);
                    
    setLight(1);
    setCamera(CAMERA_ON);
    setBacklight(100);
    setBuzzer(BUZZ_BOOT);

    Serial1.begin(9600, SERIAL_8N1, PI_RX, PI_TX);
    Serial1.print("\n\n\nKR:OK\n");
    heartbeatTimeout = time(NULL) + 60;
}

#define DOOR_OPEN     1
#define DOOR_CLOSED   0
#define STALE         0

int Reed = DOOR_OPEN, Switch1 = 0, Switch2 = 0;
unsigned int ReedDebounce = STALE, Debounce1 = STALE, Debounce2 = STALE;

// For each step and current debounce, return
// 0 if STALE, negative to continue current bounce, positive debounce millseconds
int bounceLong(int step, unsigned int debounce) {
    if (debounce == 0 || millis() > debounce) {
        switch(step) {
        case 1: case 3: case 5:
            setBuzzer(BUZZ_OFF);
            return 600;

        case 0: case 2: case 4:
            setBuzzer(BUZZ_ON);
            return 100;

        case 6:
            setBuzzer(BUZZ_ON);
            return 1200;

        default:
            setBuzzer(BUZZ_OFF);
            return -1;
        }
    } else {
        return -1;
    }
}

void loop() {
    // Debounce Door both ways
    if (digitalRead(PIN_REED) == 0) { // Door closed
        if (Reed == DOOR_CLOSED) {
            if (ReedDebounce != STALE && millis() > ReedDebounce) {
                ReedDebounce = STALE;
                doorClosed();
            }
        } else if (Reed == DOOR_OPEN) {
            Serial.println("Reed closed");
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
            Serial.println("Reed open");
            ReedDebounce = millis() + 1000;
            Reed = DOOR_OPEN;
        }
    }

    // Debounce switches only when touched
    if (digitalRead(PIN_SW1) == 0) { // Switch lifted
        if (Switch1 > 0) {
            Serial.println("Switch1 left");
            Switch1 = 0;
            Debounce1 = STALE;
        }
    } else { // Switch touched
        if (Switch1 > 0) {
            if (Debounce1 != STALE && millis() > Debounce1) {
                Debounce1 = STALE;
                switch1Action();
            }
        } else if (Switch1 == 0) {
            Serial.println("Switch1 landed");
            Debounce1 = millis() + 100;
            Switch1 = 1;
        }
    }

    // Switch 2 has long debounce
    if (digitalRead(PIN_SW2) == 0) { // Switch lifted
        if (Switch2 > 0) {
            Serial.println("Switch2 left");
            Switch2 = 0;
            Debounce2 = STALE;
        }
    } else { // Switch touched
        if (Switch2 > 0) {
            if (Debounce2 != STALE) {
                int bounce = bounceLong(Switch2, Debounce2);
                if (bounce == 0) {
                    switch2Action();
                    Debounce2 = STALE;
                } else if (bounce > 0) {
                    Debounce2 = millis() + bounce;
                    Switch2 ++;
                } // else do nothing
            }
        } else {
            Serial.println("Switch2 landed");
            Debounce2 = millis() + bounceLong(0, 0);
            Switch2 = 1;
        }
    }

    char message[8];
    int messageLength;
    while (Serial1.available() > 0 &&
           (messageLength = Serial1.readBytesUntil('\n', message, 7)) > 0) {
        message[7] = 0;
        Serial.printf("Received \"%s\"\n", message);
        if (messageLength < 5 || strncmp(message, "KR:", 3) != 0) {
            Serial.println("Ignored");
            continue;
        }
        switch(message[3]) {
        case 'C':
            if (message[4] >= '0' && message[4] <= '1') {
                setCamera(message[4] == '1' ? CAMERA_ON : CAMERA_OFF);
                Serial1.print("KR:ok\n");
            } else {
                Serial.println("Ignored");
            }
            break;

        case 'L':
            if (message[4] >= '0' && message[4] <= '1') {
                setLight(message[4] - '0');
                Serial1.print("KR:ok\n");
            } else {
                setLight(-1);
            }
            break;

        case 'O':
            if (message[4] == 'K') {
                Serial.println("Received OK");
                if (wantOK) {
                    Serial.println("Clear wantOK");
                    wantOK = false;
                }
                Serial1.print("KR:ok\n");
            } else {
                Serial.println("Ignored");
            }
            break;

        case 'P':
            switch(message[4]) {
            case 'S': case 'P':
                isPrinting = true;
                setBuzzer(BUZZ_START);
                Serial1.print("KR:ok\n");
                break;
                
            case 'E': case 'R':
                isPrinting = false;
                powerTimeout = 0;
                setBuzzer(BUZZ_END);
                Serial1.print("KR:ok\n");
                break;
                
            default:
                Serial.println("Ignored");
                break;
            }
            break;

        case 'R':
            if (message[4] == '1' || message[4] == '0') {
                setRelay(message[4] - '0');
                Serial1.print("KR:ok\n");
            } else {
                setRelay(-1);
                Serial1.print("KR:ok\n");
            }
            break;

        case 'A':
            setBuzzer(message[4] - '0');
            Serial1.print("KR:ok\n");
            break;

        default:
            Serial.println("Ignored");
            break;
        }
    }

    if (powerTimeout > 0 && time(NULL) > powerTimeout) {
        setRelay(0);
        Serial.println("Power off");
        powerTimeout = 0;
    }

    if (wantOK && time(NULL) > responseTimeout) {
        Serial.printf("Resend \"%s\"\n", ackMessage);
        Serial1.print(ackMessage);
        responseTimeout = time(NULL) + 5;
    }

    if (millis() > buzzerTimer) {
        setBuzzer(BUZZ_CONTINUE);
    }

    if (time(NULL) > heartbeatTimeout) {
        Serial1.print("KR:OK\n");
        heartbeatTimeout = time(NULL) + 60;
        Serial.println("Heartbeat");
    }

    delay(10);
}
