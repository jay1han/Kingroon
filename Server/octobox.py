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

isPowered = False
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

tickTimeout = datetime.now() + timedelta(seconds=5)
isPaused = False

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

def printTime(seconds):
    return (datetime.now().replace(hour=0, minute=0, second=0) + timedelta(seconds=int(seconds))).strftime('%H:%M')

def readOcto():
    try:
        with urlopen('http://localhost:5000/api/job?apikey=D613EB0DBA174390A1B03FCDC16E7BA0') as jobapi:
            job = json.loads(jobapi.read())

            state = job['state']
            lcd.lcd_display_string(1, state)

            fileName = job['job']['file']['name']
            if fileName is None:
                lcd.lcd_display_string(2, "")
            else:
                fileName = fileName.removesuffix('.gcode')
                lcd.lcd_display_string(2, fileName)

            completion = job['progress']['completion']
            fileEstimate = job['job']['estimatedPrintTime']
            currentTime = job['progress']['printTime']
            if completion is None: completion = 0
            if fileEstimate is None: fileEstimate = 0
            if currentTime is None: currentTime = 0
            if completion != 0 or fileEstimate != 0 or currentTime != 0:
                lcd.lcd_display_string(3, f'{printTime(currentTime)}/{printTime(fileEstimate)} {completion:.1f}%')
            else:
                lcd.lcd_display_string(3, 'No print job')

            remainingTime = job['progress']['printTimeLeft']
            if remainingTime is not None and remainingTime > 0:
                eta = datetime.now() + timedelta(seconds = (remainingTime + 60))
                eta_round = eta.replace(second=0)
                lcd.lcd_display_string(4, f'Now {datetime.now().strftime("%H:%M")} ETA {eta_round.strftime("%H:%M")}')
            else:
                lcd.lcd_display_string(4, f'Now {datetime.now().strftime("%H:%M")}')
    except OSError:
        lcd.lcd_display_string(1, 'Server not running')

powerTimeout = None

def readEvent():
    global powerTimeout
    lock = lock_lib()
    event = lock.read().strip()
    if event[:3] == 'KR:':
        print(event)
        sendUART(event)
        lcd.lcd_display_string(2, event)
        if event[3] == 'P':
            powerTimeout = None
            if event[4] == 'P':
                isPaused = True
            elif event[4] == 'R':
                isPaused = False
            elif event[4] == 'S':
                startCamera()
            elif event[4] == 'E':
                stopCamera()
                sendDisconnect()
                powerTimeout = datetime.now() + timedelta(minutes=5)
        if event[3] == 'R':
            powerTimeout = None
            if event[4] == '1':
                startCamera()
            elif event[4] == '0':
                stopCamera()
            
    free_lib(lock, erase=True);

while(True):
    readUART()
    readOcto()
    readEvent()
    if powerTimeout is not None and datetime.now() > powerTimeout:
        powerTimeout = None
        sendUART('KR:R0')
        isPowered = False
        
    sleep(1)
