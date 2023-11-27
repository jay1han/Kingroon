#!/usr/bin/python3

from octo_lib import HD44780, UART, lock_lib, free_lib
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
captureRun = ['/usr/bin/ffmpeg', '-f', 'v4l2', '-video_size', '1280x960', '-i', device_name,
              '-frames', '1', '/usr/local/share/mjpg-streamer/www/capture.jpg']

# ffmpeg -f v4l2 -video_size 1280x720 -i /dev/video0 -frames 1 out.jpg
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
    urlopen('localhost:5000/api/job', data)

def doorOpen():
    if isPaused:
        sendOctoprint('{ "command": "pause", "action": "resume" }')

def doorClosed():
    if !isPaused:
        sendOctoprint('{ "command": "pause", "action": "pause" }')

def startCamera():
    webcam = subprocess.Popen(webcamPopen)
    shutil.copyfile('index_stream.html', 'index.html')
    sendUART('KR:C1')

def stopCamera():
    webcam.terminate()
    subprocess.run(captureRun)
    shutil.copyfile('index_still.html', 'index.html')
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
    return time(second=seconds).strftime('%HH:%MM')

def readOcto():
    job = json.loads(urlopen('localhost:5000/api/job'))['job']

    state = job['state']
    lcd.lcd_display_string(0, state)

    fileName = job['job']['file']['name'].removesuffix('.gcode')
    lcd.lcd_display_string(1, filename)

    completion = job['progress']['completion']
    fileEstimate = job['job']['estimatedPrintTime']
    lcd.lcd_display_string(2, f'{completion:.1f}% of {printTime(fileEstimate)}')

    currentTime = job['progress']['printTime']
    remainingTime = job['progress']['printTimeLeft']
    eta = datetime.now() + timedelta(seconds = (remainingTime + 60))
    eta_round = eta.replace(minute=0)
    lcd.lcd_display_string(3, f'{printTime(currentTime)} ETA {eta_round.strftime("%HH:%MM")}')

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
            
    lock.free_lib(lock, erase=True);

while(True):
    readUART()
    readOcto()
    readEvent()
    sleep(1)
