from datetime import datetime, timedelta
from threading import Thread
from periphery import PWM
from time import sleep

_PWM_BUZZER = 1

from enum import Enum

class Sound:
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

    P   = 1
    G0  = 392
    G0s = 415
    A1  = 440
    A1s = 466
    B1  = 494
    C1  = 523
    C1s = 554
    D1  = 587
    D1s = 622
    E1  = 659
    F1  = 698
    F1s = 740
    G1  = 784
    G1s = 831
    A2  = 880
    A2s = 932
    B2  = 988

    def __init__(self):
        self._pwm = PWM(0, _PWM_BUZZER)
        self._pwm.frequency = 1000
        self._pwm.duty_cycle = 0.5
        self._timer = datetime.now()
        self._melody = []
        self._running = False
        self._thread = Thread(target = self._run, name = "sound", daemon = True)
        self._thread.start()

    def _run(self):
        self._running = True
        while(self._running):
            if datetime.now() >= self._timer:
                self._pwm.disable()
                if len(self._melody) > 0:
                    melody = self._melody[0]
                    self._melody = self._melody[1:]
                    self._timer = datetime.now() + timedelta(seconds=melody[1])
                    self._pwm.frequency = melody[0] 
                    self._pwm.enable()
            sleep(0.1)

    def start(self, id):
        if len(self._melody) > 0 or id == Sound.STOP:
            self._melody = []
            self._pwm.disable()

        if id == Sound.TOUCH:
            self._melody = [(440, 0.2)]

        elif id == Sound.TOUCHLG:
            self._melody = [(440, 1.0)]

        elif id == Sound.OPEN:
            self._melody = [
                (Sound.A2, 0.2),
                (Sound.B2, 0.2),
                (Sound.G1, 0.2),
                (Sound.G0, 0.2),
                (Sound.D1, 1),
            ]

        elif id == Sound.CLOSE:
            self._melody = [
                (Sound.G1, 0.2),
                (Sound.P,  0.1),
                (Sound.G1, 0.2),
                (Sound.P,  0.1),
                (Sound.G1, 0.2),
                (Sound.P,  0.1),
                (Sound.D1s, 1),
            ]

        elif id == Sound.POWERON:
            self._melody = [
                (Sound.C1s, 0.2),
                (Sound.F1s, 0.2),
                (Sound.C1s, 0.2),
                (Sound.F1s, 0.2), 
                (Sound.C1s, 1.0),
            ]

        elif id == Sound.POWEROFF:
            self._melody = [
                (Sound.C1, 0.2),
                (Sound.D1, 0.2),
                (Sound.C1, 0.4),
                (Sound.B1, 0.4), 
                (Sound.A1, 1.0),
            ]

        elif id == Sound.START:
            self._melody = [
                (Sound.B1, 0.5),
                (Sound.E0, 0.5),
                (Sound.A1, 0.5),
                (Sound.G0s, 1.0), 
            ]

        elif id == Sound.CANCEL:
            self._melody = [
                (Sound.A2, 0.3),
                (Sound.G1, 0.3),
                (Sound.A2, 1.0), 
            ]

        elif id == Sound.COOLING:
            self._melody = [
                (Sound.F1,  0.3),
                (Sound.G1,  0.3),
                (Sound.G1s, 1.0), 
            ]

        elif id == Sound.COLD:
            self._melody = [
                (Sound.B1,  0.3),
                (Sound.P,   0.1),
                (Sound.B1,  0.3),
                (Sound.P,   0.1),
                (Sound.C1,  0.3),
                (Sound.P,   0.1),
                (Sound.D1,  0.3),
                (Sound.P,   0.1),
            ]

        
        if len(self._melody) > 0:
            self._timer = datetime.now()
        
    def stop(self):
        self.start(Sound.STOP)
    
    def __del__(self):
        self.stop()
        self._running = False
        self._thread.join(1.0)
