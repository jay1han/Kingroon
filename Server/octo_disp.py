from time import sleep
from octo_lcd import HD44780
import json, os

_JSON_FILE = "/var/www/html/json"

def printTime0(seconds):
    if seconds == 0:
        return ''
    return (datetime.now().replace(hour=0, minute=0, second=0) + timedelta(seconds=int(seconds))).strftime('%H:%M')

def printTime(seconds):
    text = printTime0(seconds)
    if text == '':
        return '..:..'
    return text

def replaceText(filename, text):
    with open(f"{filename}.1", "w") as newfile:
        print(text, file=newfile)
    os.replace(f"{filename}.1", filename)

class Display:
    def __init__(self):
        self._lcd = HD44780()
        self._lcd.lcd_clear()
        self.jobInfo = ['', 0.0, 0.0, 0.0, 0.0]
        self.lastNow = ''
        self.clearInfo()
        self.setState('Printer')

    def setupIP():
        list_if = subprocess.run(['/usr/bin/ip', 'addr'], capture_output=True, text=True).stdout
        match = re.search('inet 192\.168\.([.0-9]+)', list_if, flags=re.MULTILINE)
        if match is not None:
            my_ip = f'192.168.{match.group(1)}'
        else:
            my_ip = 'localhost'
        replaceText('/var/www/html/localIP', my_ip)
    
    def setState(self, statusText):
        replaceText('/var/www/html/state', statusText)
        self._lcd.lcd_display_string(1, statusText)

    def setTemps(self, temps):
        tempExt, tempBed, tempCpu, tempCold = temps
        if tempExt == 0.0:
            temps = f'<tr><td>Extruder</td><td></td></tr><tr><td>Bed</td><td></td></tr>'
        else:
            temps = f'<tr><td>Extruder</td><td>{tempExt:.1f}&deg;</td></tr>'
            if tempCold == 0.0:
                temps += f'<tr><td>Bed</td><td>{tempBed:.1f}&deg;</td></tr>'
            else:
                temps += f'<tr><td>Bed</td><td>{tempBed:.1f}&deg;({tempCold:.1f})</td></tr>'
        temps += f'<tr><td>CPU</td><td>{tempCpu:.1f}&deg;</td></tr>'
        replaceText('/var/www/html/temps', temps)
        
        if tempExt == 0.0:
            self._lcd.lcd_display_string(2, f'       CPU:{tempCpu:2.0f}')
        else:
            if tempCold == 0.0:
                self._lcd.lcd_display_string(2, f'{tempExt:3.0f} {tempBed:2.0f}    CPU:{tempCpu:2.0f}')
            else:
                self._lcd.lcd_display_string(2, f'{tempExt:3.0f} {tempBed:2.0f}/{tempCold:2.0f} CPU:{tempCpu:2.0f}')

    def setElapsed(self, currentTime):
        jobInfoText = '<tr><td>File</td><td></td></tr>'
        jobInfoText += f'<tr><td>Elapsed</td><td>{printTime0(currentTime)}</td></tr>'
        jobInfoText += '<tr><td>ETA</td><td></td></tr>'
        jobInfoText += f'<tr><td>Now</td><td>{self.lastNow}</td></tr>'
        
        lcd.lcd_display_string(3, printTime(self.elapsed))
        lcd.lcd_display_string(4, self.lastNow)
        
    def setJobInfo(self, jobInfo):
        filename, currentTime, remainingTime, fileEstimate, donePercent = jobInfo
        if filename != '':
            jobInfoText = f'<tr><td>File</td><td>{filename}</td></tr>'
        else:
            jobInfoText = f'<tr><td>File</td><td>{self.jobInfo[0]}</td></tr>'

        if currentTime > 0:
            jobInfoText += f'<tr><td>Elapsed</td><td>{printTime0(currentTime)} ({donePercent:.1f}%)</td></tr>'
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

            etas = '(No estimate)'
            if eta1 > datetime.now():
                etas = f'{eta1.strftime("%H:%M")} ~ {eta2.strftime("%H:%M")}'
                eta1s = eta1.strftime("%H:%M")
            elif eta2 > datetime.now():
                etas = eta2.strftime("%H:%M")
            eta1s = "..:.."
            if eta1 > datetime.now(): eta1s = eta1.strftime("%H:%M")
            eta2s = "..:.."
            if eta2 > datetime.now(): eta2s = eta2.strftime("%H:%M")

            jobInfoText += f'<tr><td>ETA</td><td>{etas}</td></tr>'
            self.lastNow = datetime.now().strftime("%H:%M")
            jobInfoText += f'<tr><td>Now</td><td>{self.lastNow}</td></tr>'
            self._lcd.lcd_display_string(4, f'{self.lastNow}) {eta1s} ~ {eta2s}')
            
        else:
            jobInfoText += f'<tr><td>Elapsed</td><td>{printTime0(self.jobInfo[1])}</td></tr>'
            jobInfoText += f'<tr><td>ETA</td><td> </td></tr>'
            if self.jobInfo[0] != '':
                jobInfoText += f'<tr><td>Ended</td><td>{self.lastNow}</td></tr>'
            else:
                jobInfoText += f'<tr><td>Ended</td><td> </td></tr>'

        self.jobInfo = jobInfo
        replaceText('/var/www/html/jobInfo', jobInfoText)

    def clearInfo(self):
        self.setTemps([0.0, 0.0, 0.0, 0.0]);
        self.setJobInfo(['', 0.0, 0.0, 0.0, 0.0]);

    def __del__(self):
        self._lcd.close()
