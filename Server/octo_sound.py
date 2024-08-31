from datetime import datetime, timedelta
from threading import Thread
from periphery import PWM

_PWM_BUZZER = 1

from enum import Enum

class _Sound:
    STOP     = 0
    TOUCH    = 1      # 1 short beep
    TOUCHLG  = 2      # 3 short beeps and one long
    OPEN     = 3      # Encounters : A+B+GG-D
    CLOSE    = 4      # Beethoven 5 : GGGEb
    POWERON  = 5      # Leone : C#F#C#F#C#
    POWEROFF = 6      # Every Breath You Take : CDCBA
    START    = 7      # Star Trek : BEA+G#
    CANCEL   = 8      # Toccata & Fugue : A+GA+
    COOLING  = 9      # Let it go : FGA+bC
    COLD     = 10     # Ode a la joie : BBCD

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
        
Sound = _Sound()
