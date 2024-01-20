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

isPaused = False
isPowered = False
isIdle = True
powerTimeout = None
discTimeout  = None

def writeIndex():
    if isPowered:
        statusText  = 'Printer Ready'
        switchButton = 'Power off'
    else:
        statusText  = 'Printer Off'
        switchButton = 'Power on'
        
    with open('/usr/share/octobox/index.html') as source:
        html = source.read()
    with open('/var/www/html/index.html', 'w+') as target:
        target.write(html\
                     .replace('{localIP}', my_ip)\
                     .replace('{statusText}', statusText)\
                     .replace('{switchButton}', switchButton)\
                     )

writeIndex()

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
import json
APIKEY = 'D613EB0DBA174390A1B03FCDC16E7BA0'

DISC_DELAY = 300
POWER_DELAY = 310

def sendOctoprint(command, data):
    request = Request(f'http://localhost:5000/api/{command}',
                      headers = { 'X-Api-Key': APIKEY,
                                  'Content-Type': 'application/json'
                                  }
                      )
                                  
    try:
        urlopen(request, bytes(data, 'ascii'))
    except OSError:
        pass

def doorOpen():
    if isPaused:
        print('Door open: Resume');
        sendOctoprint('job', '{ "command": "pause", "action": "resume" }')

def doorClosed():
    if not isPaused:
        print('Door closed: Pause');
        sendOctoprint('job', '{ "command": "pause", "action": "pause" }')
    if not isPowered:
        stopCamera()

def sendDisconnect():
    sendOctoprint('connection', '{ "command": "disconnect" }')

def startCamera():
    sendUART('KR:C1')

def stopCamera():
    sendUART('KR:C0')

def readUART():
    command = UART.readline().decode(errors='ignore')
    if command[:3] == 'KR:':
        print(command)
        
        if command[3:5] == 'OK':
            sendUART('KR:OK')

        elif command[3] == 'L':
            sendUART('KR:OK')
            
        elif command[3] == 'R':
            global isPowered
            if command[4] == '1':
                isPowered = True
            else:
                isPowered = False
            writeIndex()
            sendUART('KR:OK')
            
        elif command[3] == 'D':
            if command[4] == 'C':
                doorClosed()
            elif command[4] == 'O':
                doorOpen()
            sendUART('KR:OK')

        elif command[3:5] == 'TL':
            if isPowered:
                isIdle = True
                global powerTimeout, discTimeout
                if powerTimeout is not None:
                    powerTimeout = None
                    if discTimeout is not None:
                        discTimeout = None
                    lcd.lcd_display_string(2, 'Touch to power off')
                    lcd.lcd_display_string(3, '')
                    lcd.lcd_display_string(4, '')
                else:
                    sendUART('KR:R0\n')
            else:
                sendUART('KR:R1\n')

def printTime(seconds):
    return (datetime.now().replace(hour=0, minute=0, second=0) + timedelta(seconds=int(seconds))).strftime('%H:%M')

def queryOcto(command):
    try:
        with urlopen(f'http://localhost:5000/api/{command}?apikey={APIKEY}') as jobapi:
            response = json.loads(jobapi.read())
        return response
    except OSError:
        lcd.lcd_display_string(1, 'Offline')
        return None

def readOcto():
    hasJob = False

    if not isIdle:
        job = queryOcto('job')
        if job is not None:
            state = job['state']
            lcd.lcd_display_string(1, state)

            fileName = job['job']['file']['name']
            if fileName is None:
                fileName = ''
            else:
                fileName = fileName.removesuffix('.gcode')
                lcd.lcd_display_string(2, fileName)

            completion = job['progress']['completion']
            fileEstimate = job['job']['estimatedPrintTime']
            currentTime = job['progress']['printTime']
            remainingTime = job['progress']['printTimeLeft']

            if completion is None: completion = 0
            if fileEstimate is None: fileEstimate = 0
            if currentTime is None: currentTime = 0
            if remainingTime is None: remainingTime = 0
            if currentTime != 0:
                hasJob = True
                lcd.lcd_display_string(3, f'{printTime(fileEstimate)}) {printTime(currentTime)} @{completion:5.1f}%')

                eta2 = eta1 = datetime.now()
                if remainingTime != 0:
                    eta1 = (datetime.now() + timedelta(seconds = (remainingTime + 60))).replace(second=0)
                if fileEstimate != 0:
                    eta2 = (datetime.now() - timedelta(seconds = currentTime) + timedelta(seconds = (fileEstimate + 60))).replace(second=0)
                if eta2 < eta1:
                    eta = eta2
                    eta2 = eta1
                    eta1 = eta

                if eta1 <= datetime.now():
                    eta1 = 0
                if eta2 <= datetime.now():
                    eta2 = 0

                eta1s = "..:.."
                if eta1 != 0:
                    eta1s = eta1.strftime("%H:%M")
                eta2s = "..:.."
                if eta2 != 0:
                    eta2s = eta2.strftime("%H:%M")
                lcd.lcd_display_string(4, f'{datetime.now().strftime("%H:%M")}) {eta1s} ~ {eta2s}')

    if not hasJob:
        lcd.lcd_display_string(3, 'Printer idle')
        printer = queryOcto('printer')
        if printer is None:
            lcd.lcd_display_string(4, '')
        else:
            temp0 = float(printer['temperature']['tool0']['actual'])
            tempBed = float(printer['temperature']['bed']['actual'])
            if tempBed >= 35.0:
                isHot = True
            else:
                if isHot:
                    # Beep once
                    pass
                isHot = False
            lcd.lcd_display_string(4, f'Ext:{temp0:5.1f}C Bed:{tempBed:4.1f}C')            

def readEvent():
    global powerTimeout, discTimeout
    lock = lock_lib()
    event = lock.read().strip()
    if event[:3] == 'KR:':
        print(event)
        lcd.lcd_display_string(2, event)
        if event[3] == 'P':
            powerTimeout = None
            discTimeout = None
            if event[4] == 'P':
                isPaused = True
            elif event[4] == 'R':
                isPaused = False
            elif event[4] == 'S':
                startCamera()
                isIdle = False
            elif event[4] == 'E':
                stopCamera()
                isIdle = True
                discTimeout  = datetime.now() + timedelta(seconds=DISC_DELAY)
                powerTimeout = datetime.now() + timedelta(seconds=POWER_DELAY)
                
        if event[3] == 'R':
            powerTimeout = None
            discTimeout  = None
            if event[4] == '1':
                startCamera()
            elif event[4] == '0':
                stopCamera()
                sendDisconnect()
            elif event[4] == 'R':
                if isPowered:
                    sendDisconnect()
        sendUART(event)
            
    free_lib(lock, erase=True);

def getIdle():
    job = queryOcto('job')
    if job is not None:
        state = job['state']
        if state.startswith('Printing'):
            return False
    return True

isIdle = getIdle()
        
while(True):
    readUART()
    readOcto()
    readEvent()
    
    if discTimeout is not None and datetime.now() > discTimeout:
        discTimeout = None
        sendDisconnect()
        
    if powerTimeout is not None:
        if datetime.now() > powerTimeout:
            powerTimeout = None
            sendUART('KR:R0')
            isPowered = False
            lcd.lcd_display_string(2, '')
            lcd.lcd_display_string(3, '')
        else:
            remaining = int((discTimeout - datetime.now()).total_seconds())
            lcd.lcd_display_string(2, f'Shutdown in {remaining // 60}:{remaining % 60:02d}')
        
    sleep(1)
