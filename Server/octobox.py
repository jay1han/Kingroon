#!/usr/bin/python3

from time import sleep
import os
import subprocess, re, os, signal
from datetime import time, datetime, timedelta
from enum import Enum

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
        self.o = Octoprint()
        self.d = Display()
        self.w = Webcam()
        self.elapsed = 0
        self.lastNow = datetime.now().strftime("%H:%M")
        sendUART('KR:R?')
        self.setTimeout(15)
        sendUART('KR:D?')

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

    def displayState(self, state):
        lcd.lcd_display_string(1, state)
        self.d.setState(state)

    def displayTemps(self, tempCold=0.0):
        tempExt, tempBed = self.o.getTemps()
        tempCpu = readCpuTemp()
        if cpuFan:
            fanText = ' (FAN)'
        else:
            fanText = ''
        if tempExt == 0.0:
            lcd.lcd_display_string(2, f'       CPU:{tempCpu:2.0f}{fanText}')
        else:
            lcd.lcd_display_string(2, f'{tempExt:3.0f}/{tempBed:2.0f} CPU:{tempCpu:2.0f}{fanText}')
        self.d.setTemps((tempExt, tempBed, tempCpu, tempCold))

    def displayElapsed(self):
        lcd.lcd_display_string(3, printTime(self.elapsed))
        lcd.lcd_display_string(4, self.lastNow)
        self.d.setElapsed(self.elapsed)

    def displayJob(self):
        filename, currentTime, remainingTime, fileEstimate, donePercent = self.o.getJobInfo()
        lcd.lcd_display_string(1, filename[-20:])

        if currentTime != 0:
            lcd.lcd_display_string(3, f'{printTime(currentTime)}/ {printTime(fileEstimate)} @{donePercent:5.1f}%')

            eta2 = eta1 = datetime.now()
            if remainingTime != 0:
                eta1 = (datetime.now() + timedelta(seconds = (remainingTime + 60))).replace(second=0)
            if fileEstimate != 0:
                eta2 = (datetime.now() - timedelta(seconds = currentTime) + timedelta(seconds = (fileEstimate + 60))).replace(second=0)
            if eta2 < eta1:
                eta = eta2
                eta2 = eta1
                eta1 = eta

            eta1s = "..:.."
            if eta1 > datetime.now(): eta1s = eta1.strftime("%H:%M")
            eta2s = "..:.."
            if eta2 > datetime.now(): eta2s = eta2.strftime("%H:%M")

            self.lastNow = datetime.now().strftime("%H:%M")
            lcd.lcd_display_string(4, f'{self.lastNow}) {eta1s} ~ {eta2s}')
            self.d.setJobInfo((filename, currentTime, remainingTime, fileEstimate, donePercent))
            self.elapsed = currentTime
                
    def loop(self):
        state = self.o.getState()
        command = readUART()
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

        if self.state == State.COOLING:
            self.displayTemps(coldTemp)
        else:
            self.displayTemps()
        
        if self.state == State.OFF:
            self.displayState('Printer Off')
        elif self.state == State.POWERON:
            self.displayState(state)
        elif self.state == State.IDLE:
            self.displayState(state)
        elif self.state == State.PRINTING:
            self.displayJob()
        elif self.state == State.COOLING:
            self.displayElapsed()
            self.displayState('Cooling')
        elif self.state == State.COLD:
            self.displayState('Cold')
        elif self.state == State.CLOSED:
            self.displayState('Door Closed')
            
octo = Octobox()

while(True):
    octo.loop()
    sleep(1)
