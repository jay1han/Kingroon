#!/usr/bin/python3

from octo_lib import HD44780, UART, lock_lib, free_lib
from time import sleep
import shutil

lcd = HD44780()
lcd.lcd_clear()
lcd.lcd_display_string(1, "Hello")

#################################################################
# Get the webcam

import subprocess, re

list_devices = subprocess.run(['/usr/bin/v4l2-ctl', '--list-devices'], capture_output=True, text=True).stdout.splitlines()

line_no = 0
usb_device = 0
for line in list_devices:
    line_no += 1
    if re.search('USB', line):
        usb_device = line_no

device_name = list_devices[usb_device].strip()
webcamPopen = ['/usr/local/bin/mjpg_streamer',
               '-i', f'"/usr/local/lib/mjpg-streamer/input_uvc.so -d {device_name} -n -r 640x480"',
               '-o', '"/usr/local/lib/mjpg-streamer/output_http.so -w /usr/local/share/mjpg-streamer/www"']
captureRun = ['/usr/bin/fswebcam', '-r', '1280x960', '-d', device_name, '--no-banner',
              '--rotate', '180', '--jpeg', '95', '/var/www/html/capture.jpg']

# fswebcam -d /dev/video3 -r 640x480 --no-banner --rotate 180 --jpeg 95 /var/www/html/capture.jpg
# TODO: Run the webcam only when needed, replace with a still image when stopped
webcam = None
        
#################################################################
# Monitor the UART, Octoprint info and events --> update the display

from datetime import time, datetime, timedelta
from urllib.request import urlopen
import json

tickTimeout = datetime.now() + timedelta(seconds=5)
isPaused = False

def sendOctoprint(data):
    urlopen('http://localhost:5000/api/job?apikey=D613EB0DBA174390A1B03FCDC16E7BA0', data)

def doorOpen():
    if isPaused:
        sendOctoprint('{ "command": "pause", "action": "resume" }')

def doorClosed():
    if not isPaused:
        sendOctoprint('{ "command": "pause", "action": "pause" }')

def startCamera():
    webcam = subprocess.Popen(webcamPopen)
    shutil.copyfile('/var/www/html/stream.html', '/var/www/html/index.html')
    sendUART('KR:C1')

def stopCamera():
    webcam.terminate()
    subprocess.run(captureRun)
    shutil.copyfile('/var/www/html/still.html', '/var/www/html/index.html')
    sendUART('KR:C0')

def readUART():
    command = UART.readline()
    if command[:3] == 'KR:':
        if command[3:5] == 'OK':
            sendUART('KR:OK')

        elif command[3] == 'L':
            sendUART('KR:OK')
            
        elif command[3] == 'R':
            sendUART('KR:OK')
            
        elif command[3] == 'D':
            if command[4] == 'C':
                doorClosed()
            elif command[4] == 'O':
                doorOpen()
            sendUART('KR:OK')

def sendUART(command):
    UART.write((command + '\n').encode('utf-8'))

def printTime(seconds):
    return (datetime.now().replace(hour=0, minute=0, second=0) + timedelta(seconds=int(seconds))).strftime('%H:%M')

def readOcto():
    with urlopen('http://localhost:5000/api/job?apikey=D613EB0DBA174390A1B03FCDC16E7BA0') as jobapi:
        job = json.loads(jobapi.read())

        state = job['state']
        lcd.lcd_display_string(1, state)

        fileName = job['job']['file']['name']
        if fileName is None:
            lcd.lcd_display_string(2, "")
        else:
            fileName.removesuffix('.gcode')
            lcd.lcd_display_string(2, fileName)

        completion = job['progress']['completion']
        if completion is None: completion = 0
        fileEstimate = job['job']['estimatedPrintTime']
        if fileEstimate is None: fileEstimate = 0
        currentTime = job['progress']['printTime']
        if currentTime is None: currentTime = 0
        lcd.lcd_display_string(3, f'{printTime(currentTime)}/{printTime(fileEstimate)} {completion:.1f}%')
        
        remainingTime = job['progress']['printTimeLeft']
        if remainingTime is not None and remainingTime > 0:
            eta = datetime.now() + timedelta(seconds = (remainingTime + 60))
            eta_round = eta.replace(second=0)
            lcd.lcd_display_string(4, f'Now {datetime.now().strftime("%H:%M")} ETA {eta_round.strftime("%H:%M")}')
        else:
            lcd.lcd_display_string(4, f'Now {datetime.now().strftime("%H:%M")}')

def readEvent():
    lock = lock_lib()
    event = lock.read().strip()
    if event[:3] == 'KR:':
        if event[3] == 'P':
            if event[4] == 'P':
                isPaused = True
            elif event[4] == 'R':
                isPaused = False
            elif event[4] == 'S':
                startCamera()
            elif event[4] == 'E':
                stopCamera()
        sendUART(event)
            
    free_lib(lock, erase=True);

while(True):
    readUART()
    readOcto()
    readEvent()
    sleep(1)
