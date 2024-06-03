from datetime import datetime, timedelta
from threading import Thread
from periphery import PWM

_PWM_BUZZER = 1

class Sound:
    OFF    = 0
    SINGLE = 1
    TRIPLE = 2
    MULTI  = 3
    LONG   = 4

    _SHORT = timedelta(milliseconds = 100)
    _SPACE = timedelta(milliseconds = 500)
    _LONG  = timedelta(seconds = 2)
    
    def __init__(self):
        self._pwm = PWM(0, _PWM_BUZZER)
        self._pwm.frequency = 1000
        self._pwm.duty_cycle = 0.5
        self._thread = Thread(target = self.run, name = "sound")
        self._id = 0
        self._timer = datetime.now()

    def start(self, id):
        while(True):
            if self._id != 0:
                pass
        
    def stop(self):
        pass
    
    def __del__(self):
        self.stop()
        
