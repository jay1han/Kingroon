#!/usr/bin/python3

from octo_lib import HD44780, UART, lock_lib, free_lib, sendUART
from time import sleep

lcd = HD44780()
lcd.lcd_clear()
lcd.lcd_display_string(1, "Octobox")

#################################################################
# Get the webcam

import subprocess, re

list_if = subprocess.run(['/usr/bin/ip', 'addr'], capture_output=True, text=True).stdout
match = re.search('inet 192\.168\.([.0-9]+)', list_if, flags=re.MULTILINE)
if match is not None:
    my_ip = f'192.168.{match.group(1)}'
else:
    my_ip = 'localhost'

class Display:
    def __init__(self):
        self.temps = (0, 0)
        self.jobInfo = ('', 0, 0.0, 0, 0)
        self.setPowered(False)

    def setPowered(self, isPowered):
        self.isPowered = isPowered
        if self.isPowered:
            statusText  = 'Printer On'
            switchButton = 'Turn Off'
        else:
            statusText  = 'Printer Off'
            switchButton = 'Turn On'

        with open('/usr/share/octobox/index.html') as source:
            html = source.read()
        with open('/var/www/html/index.html', 'w+') as target:
            target.write(html\
                         .replace('{localIP}', my_ip)\
                         .replace('{statusText}', statusText)\
                         .replace('{switchButton}', switchButton)\
                         )

    def setTemps(self, temps):
        self.temps = temps
        tempExt, tempBed = self.temps
        temps = ''
        if tempExt != 0:
            temps = f'Printer: {tempExt:.1f}&deg;/{tempBed:.1f}&deg;'

        with open('/var/www/html/temps', 'w') as target:
            print(temps, file=target)
        
    def setJobInfo(self, jobInfo):
        self.jobInfo = jobInfo
        filename, fileEstimate, donePercent, currentTime, remainingTime = self.jobInfo
        jobInfo = ''
        if filename != '':
            jobInfo = f'File: {filename}<br>'

        if currentTime > 0:
            jobInfo += f'Elapsed: {printTime(currentTime)} @{donePercent:.1f}%<br>'

            eta2 = eta1 = datetime.now()
            if remainingTime != 0:
                eta1 = (datetime.now() + timedelta(seconds = (remainingTime + 60))).replace(second=0)
            if fileEstimate != 0:
                eta2 = (datetime.now() - timedelta(seconds = currentTime) + timedelta(seconds = (fileEstimate + 60))).replace(second=0)
            if eta2 < eta1:
                eta = eta2
                eta2 = eta1
                eta1 = eta

            eta1s = "(exceeded)"
            if eta1 > datetime.now(): eta1s = eta1.strftime("%H:%M")
            eta2s = "(exceeded)"
            if eta2 > datetime.now(): eta2s = eta2.strftime("%H:%M")
            jobInfo += f'ETA: {eta1s} ~ {eta2s}<br>Now: {datetime.now().strftime("%H:%M")}'

        with open('/var/www/html/jobInfo', 'w') as target:
            print(jobInfo, file=target)
        

list_devices = subprocess.run(['/usr/bin/v4l2-ctl', '--list-devices'], capture_output=True, text=True).stdout.splitlines()

line_no = 0
usb_device = 0
for line in list_devices:
    line_no += 1
    if re.search('USB', line):
        usb_device = line_no

device_name = list_devices[usb_device].strip()
webcamPopen = ['/usr/local/bin/mjpg_streamer',
               '-i', f'/usr/local/lib/mjpg-streamer/input_uvc.so -d {device_name} -n -r 640x480',
               '-o', '/usr/local/lib/mjpg-streamer/output_http.so -w /usr/local/share/mjpg-streamer/www']

webcam = subprocess.Popen(webcamPopen)
print(f'Started webcam process {webcam.pid}')
lcd.lcd_display_string(2, "Webcam started")
        
#################################################################
# Monitor the UART, Octoprint info and events --> update the display

from datetime import time, datetime, timedelta
from urllib.request import urlopen, Request
from enum import Enum
import json
APIKEY = 'D613EB0DBA174390A1B03FCDC16E7BA0'

def printTime(seconds):
    if seconds == 0:
        return '..:..'
    return (datetime.now().replace(hour=0, minute=0, second=0) + timedelta(seconds=int(seconds))).strftime('%H:%M')

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
            return '', 0, 0.0, 0, 0
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

            return filename, fileEstimate, donePercent, currentTime, remainingTime

class State(Enum):
    OFF      = 0
    POWERON  = 1
    IDLE     = 2
    PRINTING = 3
    COOLING  = 4
    COLD     = 5
            
class Octobox:
    def __init__(self):
        self.state = State.OFF
        self.timeout = None
        self.o = Octoprint()
        self.d = Display()
        sendUART('KR:R?')
        self.setTimeout(15)

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
    
    def doorOpen(self):
        if isPaused:
            print('Door open: Resume');
            sendOcto('job', '{ "command": "pause", "action": "resume" }')

    def doorClosed(self):
        if not isPaused:
            print('Door closed: Pause');
            sendOcto('job', '{ "command": "pause", "action": "pause" }')
        if not isPowered:
            stopCamera()

    def processOFF(self, state, command, event):
        if command == 'R1':
            self.d.setPowered(True);
            self.state = State.POWERON
            self.o.connect()
            self.setTimeout(15)
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
            self.d.setPowered(False);
            self.state = State.OFF
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
            self.d.setPowered(False);
            self.state = State.OFF
        elif state.startswith('Printing'):
            sendUART('KR:PS')
            self.state = State.PRINTING
        elif state == 'Disconnected':
            self.state = State.POWERON
            
    def processPRINTING(self, state, command, event):
        if command == 'TL' or event == 'RR':
            sendUART('KR:PE')
            self.o.cancel()
        elif not state.startswith('Printing'):
            sendUART('KR:PE')
            self.state = State.COOLING

    def processCOOLING(self, state, command, event):
        if command == 'TL' or event == 'RR':
            self.o.disconnect()
            sendUART('KR:R0')
        elif command == 'R0':
            self.d.setPowered(False);
            self.state = State.OFF
        else:
            tempExt, tempBed = self.o.getTemps()
            if tempBed <= 32.0:
                self.o.disconnect()
                sendUART('KR:R0')
                self.state = State.COLD
                self.setTimeout(5)

    def processCOLD(self, state, command, event):
        if command == 'R0':
            self.d.setPowered(False);
            self.state = State.OFF
            self.timeout = None
        elif self.isTimedout():
            sendUART('KR:R0')
            self.setTimeout(5)

    def displayState(self, state):
        lcd.lcd_display_string(1, state)

    def displayTemps(self):
        tempExt, tempBed = self.o.getTemps()
        if tempBed > 0:
            lcd.lcd_display_string(2, f'Pr:{tempExt + 0.5:3.0f}/{tempBed+0.5:2.0f} Env:00/00%')
            print(f'Pr:{tempExt + 0.5:3.0f}/{tempBed+0.5:2.0f} Env:00/00%')
            self.d.setTemps((tempExt, tempBed))

    def displayJob(self):
        filename, fileEstimate, donePercent, currentTime, remainingTime = self.o.getJobInfo()
        lcd.lcd_display_string(1, filename)

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
            self.d.setJobInfo((filename, fileEstimate, donePercent, currentTime, remainingTime))
                
    def loop(self):
        state = self.o.getState()
        command = readUART()
        event = readEvent()

        print(f'{self.state} -> "{state}", "{command}"')
        
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

        if self.state == State.OFF:
            self.displayState('OFF')
        elif self.state == State.POWERON:
            self.displayState(state)
            self.displayTemps()
        elif self.state == State.IDLE:
            self.displayState(state)
            self.displayTemps()
        elif self.state == State.PRINTING:
            self.displayJob()
            self.displayTemps()
        elif self.state == State.COOLING:
            self.displayState('Cooling')
            self.displayTemps()
        elif self.state == State.COLD:
            self.displayState('Cold')
            self.displayTemps()
            
o = Octobox()

while(True):
    o.loop()
    sleep(1)
