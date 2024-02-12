#!/usr/bin/python3

from octo_lib import HD44780, UART, lock_lib, free_lib, sendUART
from time import sleep

lcd = HD44780()
lcd.lcd_clear()
lcd.lcd_display_string(1, "Octobox")

#################################################################
# Get the webcam

import subprocess, re, os, signal

def printTime0(seconds):
    if seconds == 0:
        return ''
    return (datetime.now().replace(hour=0, minute=0, second=0) + timedelta(seconds=int(seconds))).strftime('%H:%M')

def printTime(seconds):
    text = printTime0(seconds)
    if text == '':
        return '..:..'
    return text

NO_TEMPS   = (0.0, 0.0, 0.0, 0.0)
NO_JOBINFO = ('', 0, 0, 0, 0.0)

class Display:
    def __init__(self):
        self.setState('Printer')
        self.jobInfo = NO_JOBINFO
        self.lastNow = datetime.now().strftime("%H:%M")
        self.clearInfo()

    def setState(self, statusText):
        with open('/var/www/html/state', 'w') as target:
            print(statusText, file=target)

    def setTemps(self, temps):
        tempExt, tempBed, tempCpu, tempEnv = temps
        if tempExt == 0.0:
            temps = f'<tr><td>Extruder</td><td></td></tr><tr><td>Bed</td><td></td></tr>'
        else:
            temps = f'<tr><td>Extruder</td><td>{tempExt+0.5:.1f}&deg;</td></tr><tr><td>Bed</td><td>{tempBed+0.5:.1f}&deg;</td></tr>'
        temps += f'<tr><td>CPU</td><td>{tempCpu+0.05:.1f}&deg;</td></tr>'
        if tempEnv == 0.0:
            temps += f'<tr><td>Env</td><td></td></tr>'
        else:
            temps += f'<tr><td>Env</td><td>{tempEnv+0.05:.1f}&deg;</td></tr>'

        with open('/var/www/html/temps', 'w') as target:
            print(temps, file=target)
        
    def setJobInfo(self, jobInfo):
        filename, currentTime, remainingTime, fileEstimate, donePercent = jobInfo
        if filename != '':
            jobInfoText = f'<tr><td>File</td><td>{filename}</td></tr>'
        else:
            jobInfoText = f'<tr><td>File</td><td>{self.jobInfo[0]}</td></tr>'

        if currentTime > 0:
            jobInfoText += f'<tr><td>Elapsed</td><td>{printTime0(currentTime)} ({donePercent:.1f}%)</td></tr>'

            eta2 = eta1 = datetime.now()
            if remainingTime != 0:
                eta1 = (datetime.now() + timedelta(seconds = (remainingTime + 60))).replace(second=0)
            if fileEstimate != 0:
                eta2 = (datetime.now() - timedelta(seconds = currentTime) + timedelta(seconds = (fileEstimate + 60))).replace(second=0)
            if eta2 < eta1:
                eta = eta2
                eta2 = eta1
                eta1 = eta

            etas = '(No estimate)'
            if eta1 > datetime.now():
                etas = f'{eta1.strftime("%H:%M")} ~ {eta2.strftime("%H:%M")}'
            elif eta2 > datetime.now():
                etas = eta2.strftime("%H:%M")

            jobInfoText += f'<tr><td>ETA</td><td>{etas}</td></tr>'
            jobInfoText += f'<tr><td>Now</td><td>{datetime.now().strftime("%H:%M")}</td></tr>'
            self.lastNow = datetime.now().strftime("%H:%M")
            
        else:
            jobInfoText += f'<tr><td>Elapsed</td><td>{printTime0(self.jobInfo[1])}</td></tr>'
            jobInfoText += f'<tr><td>ETA</td><td> </td></tr>'
            if self.jobInfo[0] != '':
                jobInfoText += f'<tr><td>Ended</td><td>{self.lastNow}</td></tr>'
            else:
                jobInfoText += f'<tr><td>Ended</td><td> </td></tr>'

        self.jobInfo = jobInfo
        with open('/var/www/html/jobInfo', 'w') as target:
            print(jobInfoText, file=target)

    def clearInfo(self):
        self.setTemps(NO_TEMPS);
        self.setJobInfo(NO_JOBINFO);

def setupIP():
    list_if = subprocess.run(['/usr/bin/ip', 'addr'], capture_output=True, text=True).stdout
    match = re.search('inet 192\.168\.([.0-9]+)', list_if, flags=re.MULTILINE)
    if match is not None:
        my_ip = f'192.168.{match.group(1)}'
    else:
        my_ip = 'localhost'

    with open('/var/www/html/localIP', 'w') as target:
        print(my_ip, file=target)

class Webcam:
    def __init__(self):
        ps = subprocess.run(['/usr/bin/ps', '-C', 'mjpg_streamer', '--no-headers', '-o', 'pid'],
                            capture_output=True, text=True)\
                            .stdout.strip()
        if ps != '':
            print(f'Kill streamer PID={ps}')
            os.kill(int(ps), signal.SIGTERM)
        self.Popen = None
        list_devices = subprocess.run(['/usr/bin/v4l2-ctl', '--list-devices'],
                                      capture_output=True, text=True)\
                                 .stdout.splitlines()
        line_no = 0
        usb_device = 0
        for line in list_devices:
            line_no += 1
            if re.search('USB', line):
                usb_device = line_no

        self.device = list_devices[usb_device].strip()
        self.capture()
        
    def start(self):
        sendUART('KR:C1')
        webcamPopen = ['/usr/local/bin/mjpg_streamer',
                       '-i', f'/usr/local/lib/mjpg-streamer/input_uvc.so -d {self.device} -n -r 640x480',
                       '-o', '/usr/local/lib/mjpg-streamer/output_http.so -w /usr/local/share/mjpg-streamer/www']
        self.Popen = subprocess.Popen(webcamPopen)
        print(f'Started webcam process {self.Popen.pid}')

    def stop(self):
        if self.Popen is not None:
            print('Stop streamer')
            self.Popen.terminate()
            self.Popen = None
            sleep(1)
        self.capture()
        sendUART('KR:C0')

    def capture(self):
        subprocess.run(['/usr/bin/fswebcam', '-d', self.device, '-r', '640x480', '-F', '1', '--no-banner', '/var/www/html/image.jpg'])
        
#################################################################
# Monitor the UART, Octoprint info and events --> update the display

from datetime import time, datetime, timedelta
from urllib.request import urlopen, Request
from enum import Enum
import json
APIKEY = 'D613EB0DBA174390A1B03FCDC16E7BA0'

def readCpuTemp():
    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as temp:
        return int(temp.read().strip()) / 1000.0

def readEvent():
    lock = lock_lib()
    event = lock.read().strip()
    
    response = ''
    if event[:3] == 'KR:':
        print(f'Event "{event}"')
        if event[3] == 'C' or event[3] == 'L':
            sendUART(event)
        else:
            response = event[3:]
            
    free_lib(lock, erase=True);
    return response

def readUART():
    command = UART.readline().decode(errors='ignore').strip()
    if command[:3] == 'KR:':
        print(f'UART "{command}"')
        return command[3:]
    else:
        return ''

class Octoprint:
    def __init__(self):
        pass

    def query(self, command):
        try:
            with urlopen(f'http://localhost:5000/api/{command}?apikey={APIKEY}') as jobapi:
                return json.loads(jobapi.read())
        except OSError:
            return None

    def request(self, command, data):
        request = Request(f'http://localhost:5000/api/{command}',
                          headers = { 'X-Api-Key': APIKEY,
                                      'Content-Type': 'application/json'
                                     }
                          )
        try:
            urlopen(request, bytes(data, 'ascii'))
        except OSError:
            pass

    def disconnect(self):
        self.request('connection', '{ "command": "disconnect" }')

    def connect(self):
        self.request('connection', '{ "command": "connect" }')

    def cancel(self):
        self.request('job', '{ "command": "cancel" }')

    def getState(self):
        job = self.query('job')
        if job is None:
            return 'Disconnected'
        else:
            return job['state']

    def getTemps(self):
        printer = self.query('printer')
        if printer is None:
            return 0, 0
        else:
            tempExt = 0
            if printer['temperature'].get('tool0') is not None:
                tempExt = float(printer['temperature']['tool0']['actual'])
            tempBed = 0
            if printer['temperature'].get('bed') is not None:
                tempBed = float(printer['temperature']['bed']['actual'])
            return tempExt, tempBed

    def getJobInfo(self):
        job = self.query('job')
        if job is None:
            return NO_JOBINFO
        else:
            filename = job['job']['file']['name']
            if filename is None:
                filename = ''
            else:
                filename =  filename.removesuffix('.gcode')

            fileEstimate = job['job']['estimatedPrintTime']
            donePercent = job['progress']['completion']
            currentTime = job['progress']['printTime']
            remainingTime = job['progress']['printTimeLeft']

            if fileEstimate is None: fileEstimate = 0
            if donePercent is None: donePercent = 0
            if currentTime is None: currentTime = 0
            if remainingTime is None: remainingTime = 0

            return filename, currentTime, remainingTime, fileEstimate, donePercent

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
        sendUART('KR:R?')
        self.setTimeout(15)
        sendUART('KR:D?')

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
            if tempBed < 30.0:
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

    def displayTemps(self):
        tempExt, tempBed = self.o.getTemps()
        tempCpu = readCpuTemp()
        if tempExt == 0.0:
            lcd.lcd_display_string(2, f'       CPU:{tempCpu+0.5:2.0f} Env: 0')
        else:
            lcd.lcd_display_string(2, f'{tempExt+0.5:3.0f}/{tempBed+0.5:2.0f} CPU:{tempCpu+0.5:2.0f} Env: 0')
        self.d.setTemps((tempExt, tempBed, tempCpu, 0))

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

            lcd.lcd_display_string(4, f'{datetime.now().strftime("%H:%M")}) {eta1s} ~ {eta2s}')
            self.d.setJobInfo((filename, currentTime, remainingTime, fileEstimate, donePercent))
                
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
            self.displayState('Cooling')
        elif self.state == State.COLD:
            self.displayState('Cold')
        elif self.state == State.CLOSED:
            self.displayState('Door Closed')
            
setupIP()            
octo = Octobox()

while(True):
    octo.loop()
    sleep(1)
