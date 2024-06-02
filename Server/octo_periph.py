from threading import Thread
from time import sleep
from periphery import GPIO

_GPIO_LIGHT = 1
_GPIO_REED  = 2
_GPIO_TOUCH = 3
_GPIO_FLASH = 4
_GPIO_FAN   = 5
_GPIO_RELAY = 6
    
def readCpuTemp():
    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as temp:
        cpuTemp = int(temp.read().strip()) / 1000.0
    if  cpuTemp > highTemp:
        setFan(True)
    elif cpuTemp < lowTemp:
        setFan(False)
    return cpuTemp

class Peripheral:
    def __init__(self):
        self._flash = 0
        self._flashGpio = GPIO("/dev/gpiochip0", _GPIO_FLASH, "out")
        self._light = 0
        self._lightGpio = GPIO("/dev/gpiochip0", _GPIO_LIGHT, "out")
        self._fan = 0
        self._fanGpio = GPIO("/dev/gpiochip0", _GPIO_FAN, "out")
        self._relay = 0
        self._relayGpio = GPIO("/dev/gpiochip0", _GPIO_RELAY, "out")
        
        self._reed = 0
        self._reedGpio = GPIO("/dev/gpiochip0", _GPIO_REED, "in")
        self._reedGpio.bias = "pull_up"
        self._touch = 1
        self._touchGpio = GPIO("/dev/gpiochip0", _GPIO_TOUCH, "in")
        self._touchDown = datetime.now()

        self._thread = Thread(target = self.run, name = "", daemon = True)
        self._thread.start()

    def run(self):
        while (True):
            touch = int(self._touchGpio.read())
            sleep(0.1)
        
    def flash(self, state = None) -> int:
        if state is not None:
            if state == -1:
                self._flash = 1 - self._flash
            else:
                self._flash = flash
            self._flashGpio.write(bool(self._flash))
        return self._flash
    
    def light(self, state = None) -> int:
        if state is not None:
            if state == -1:
                self._light = 1 - self._light
            else:
                self._light = state
            self._lightGpio.write(bool(self._light))
        return self._light

    def fan(self, state = None) -> int:
        if state is not None:
            if state == -1:
                self._fan = 1 - self._fan
            else:
                self._fan = state
            self._fanGpio.write(bool(self._fan))
        return self._fan

    def relay(self, state = None) -> int:
        if state is not None:
            if state == -1:
                self._relay = 1 - self._relay
            else:
                self._relay = state
            self.relayGpio.write(bool(self._relay))
        return self._relay

