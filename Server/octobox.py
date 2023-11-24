#!/usr/bin/python3

from octo_lib import HD44780, UART, lock_lib, free_lib

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
webcam = subprocess.Popen(['/usr/local/bin/mjpg_streamer',
                           '-i', f'"/usr/local/lib/mjpg-streamer/input_uvc.so -d {device_name} -n -r 640x480"',
                           '-o', '"/usr/local/lib/mjpg-streamer/output_http.so -w /usr/local/share/mjpg-streamer/www"'],
                          )

# TODO: Run the webcam only when needed, replace with a still image when stopped
        
#################################################################
# Monitor the UART, Octoprint info and events --> update the display

from datetime import time, datetime, timedelta
from urllib.request import urlopen
import json

tickTimeout = datetime.now() + timedelta(seconds=5)

def readUART():
    byte = UART.read()
    ## TODO

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
    event = lock.read()
    sendUART(event.strip())
    lock.free_lib(lock, erase=True);

while(True):
    readUART()
    readOcto()
    readEvent()
    sleep(1)
