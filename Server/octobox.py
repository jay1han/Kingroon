#!/usr/bin/python3

from time import sleep
import os
import subprocess, re, os, signal
from datetime import time, datetime, timedelta
from enum import Enum

from octo_print import Octoprint
from octo_socket import Socket
from octo_sound import Sound
from octo_periph import Peripheral
from octo_cam import Camera
from octo_disp import Display

def readCpuTemp():
    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as temp:
        cpuTemp = int(temp.read().strip()) / 1000.0
    if  cpuTemp > highTemp:
        setFan(True)
    elif cpuTemp < lowTemp:
        setFan(False)
    return cpuTemp

class State(Enum):
    OFF      = 0
    POWERON  = 1
    IDLE     = 2
    PRINTING = 3
    COOLING  = 4
    COLD     = 5
    CLOSED   = -1
            
class Octobox:
    def __init__(self):
        self.state = State.OFF
        self.timeout = None
        self.elapsed = 0

        self.p = Peripheral()
        self.s = Sound()
        self.c = Camera(self.p)
        self.o = Octoprint()
        self.d = Display()

    def __del__(self):
        pass

    def setTimeout(self, seconds):
        if seconds == 0:
            self.timeout = None
        else:
            self.timeout = datetime.now() + timedelta(seconds = seconds)

    def isTimedout(self):
        if self.timeout is not None and datetime.now() > self.timeout:
            self.timeout = None
            print('Timeout')
            return True
        else:
            return False
    
    def processCLOSED(self, state, command, event):
        if command == 'DO':
            self.w.stop()
            self.d.setState('Printer')
            self.state = State.OFF
            self.timeout = None
        elif command == 'R1':
            sendUART('KR:R0')
            self.setTimeout(15)
        elif command == 'R0':
            self.timeout = None
        elif event == 'PE':
            sendUART('KR:R0')
            self.setTimeout(15)
        elif self.isTimedout():
            sendUART('KR:R0')
            self.setTimeout(15)

    def processOFF(self, state, command, event):
        # Door Close -> CLOSED
        # Long touch -> POWERON (timer)
        # Power button -> POWERON (timer)
        
        if command == 'R1':
            self.d.setState('Printer On')
            self.state = State.POWERON
            self.o.connect()
            self.w.start()
            self.setTimeout(15)
        elif command == 'DC':
            self.d.setState('Door Closed')
            self.state = State.CLOSED
        elif command == 'TL' or event == 'RR':
            sendUART('KR:R1')
            self.setTimeout(15)
        elif self.isTimedout():
            sendUART('KR:R?')
            self.setTimeout(15)

    def processON(self, state, command, event):
        # Timeout & Offline -> Connect
        # Operational -> IDLE
        if command == 'TL' or event == 'RR':
            sendUART('KR:R0')
        elif command == 'R0':
            self.w.stop()
            self.d.setState('Printer Off')
            self.state = State.OFF
        elif command == 'DC':
            self.d.setState('Door Closed')
            self.state = State.CLOSED
            sendUART('KR:R0')
        elif state == 'Offline' :
            if self.isTimedout():
                self.o.connect()
                self.setTimeout(15)
        elif state.startswith('Printing'):
            sendUART('KR:PS')
            self.state = State.PRINTING
        else:
            self.timeout = None
            self.state = State.IDLE

    def processIDLE(self, state, command, event):
        if command == 'TL' or event == 'RR':
            self.o.disconnect()
            sendUART('KR:R0')
        elif command == 'R0':
            self.d.setState('Printer Off');
            self.w.stop()
            self.state = State.OFF
        elif command == 'DC':
            self.d.setState('Door Closed')
            self.o.disconnect()
            sendUART('KR:R0')
            self.state = State.CLOSED
        elif state.startswith('Printing'):
            sendUART('KR:PS')
            self.d.setJobInfo(NO_JOBINFO);
            self.state = State.PRINTING
        elif state == 'Disconnected':
            self.state = State.POWERON
            
    def processPRINTING(self, state, command, event):
        if command == 'TL' or event == 'RR':
            sendUART('KR:PE')
            self.o.cancel()
        elif command == 'DC':
            self.d.setState('Door Closed')
            self.o.cancel()
            self.o.disconnect()
            sendUART('KR:R0')
            self.state = State.CLOSED
        elif not state.startswith('Printing'):
            sendUART('KR:PE')
            self.state = State.COOLING

    def processCOOLING(self, state, command, event):
        if command == 'TL' or event == 'RR':
            self.o.disconnect()
            sendUART('KR:R0')
        elif command == 'R0':
            self.w.stop()
            self.d.setState('Printer Off');
            self.state = State.OFF
        elif command == 'DC':
            self.d.setState('Door Closed')
            self.state = State.CLOSED
            sendUART('KR:R0')
        elif state == 'Printing':
            sendUART('KR:PS')
            self.state = State.PRINTING
            self.timeout = None
        else:
            tempExt, tempBed = self.o.getTemps()
            if tempBed < coldTemp:
                sendUART('KR:B2')
                self.o.disconnect()
                self.state = State.COLD
                self.setTimeout(5)
                sleep(1)
                sendUART('KR:R0')
                
    def processCOLD(self, state, command, event):
        if command == 'R0':
            self.w.stop()
            self.d.setState('Printer Off')
            sendUART('KR:L0')
            self.state = State.OFF
            self.timeout = None
        elif command == 'DC':
            self.d.setState('Door Closed')
            self.state = State.CLOSED
            sendUART('KR:R0')
            self.setTimeout(5)
        elif self.isTimedout():
            sendUART('KR:R0')
            self.setTimeout(5)

    def displayJob(self):
        self.d.setJobInfo((filename, currentTime, remainingTime, fileEstimate, donePercent))
        self.elapsed = currentTime
                
    def loop(self):
        state = self.o.getState()
        event = readEvent()

        print(f'{self.state} -> "{state}", "{command}"')
        if command == 'DC':
            sendUART('KR:OK')
        
        if self.state == State.OFF:
            self.processOFF(state, command, event)
        elif self.state == State.POWERON:
            self.processON(state, command, event)
        elif self.state == State.IDLE:
            self.processIDLE(state, command, event)
        elif self.state == State.PRINTING:
            self.processPRINTING(state, command, event)
        elif self.state == State.COOLING:
            self.processCOOLING(state, command, event)
        elif self.state == State.COLD:
            self.processCOLD(state, command, event)
        elif self.state == State.CLOSED:
            self.processCLOSED(state, command, event)

        tempExt, tempBed = self.o.getTemps()
        tempCpu = readCpuTemp()
        tempCold = 0.0
        if self.state == State.COOLING:
            tempCold = 35.0
        self.d.setTemps((tempExt, tempBed, tempCpu, tempCold))
        
        if self.state == State.OFF:
            self.d.setState('Printer Off')
        elif self.state == State.POWERON:
            self.d.setState(state)
        elif self.state == State.IDLE:
            self.d.setState(state)
        elif self.state == State.PRINTING:
            self.displayJob()
        elif self.state == State.COOLING:
            self.d.setElapsed(self.elapsed)
            self.d.setState('Cooling')
        elif self.state == State.COLD:
            self.d.setState('Cold')
        elif self.state == State.CLOSED:
            self.d.setState('Door Closed')

    def test(self):
        self.s.start(Sound.POWERON)
        
octobox = Octobox()
octobox.test()
