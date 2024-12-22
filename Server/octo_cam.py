import subprocess, os, re
from octo_periph import Peripheral

class Camera:
    def __init__(self, peripheral: Peripheral):
        self._peripheral = peripheral
        ps = subprocess.run(['/usr/bin/ps', '-C', 'ustreamer', '--no-headers', '-o', 'pid'],
                            capture_output=True, text=True)\
                            .stdout.strip()
        if ps != '':
            print(f'Kill streamer PID={ps}')
            os.kill(int(ps), signal.SIGTERM)
        self._Popen = None
        list_devices = subprocess.run(['/usr/bin/v4l2-ctl', '--list-devices'],
                                      capture_output=True, text=True)\
                                 .stdout.splitlines()
        line_no = 0
        usb_device = 0
        for line in list_devices:
            line_no += 1
            if re.search('Webcam', line):
                usb_device = line_no

        self._device = list_devices[usb_device].strip()
        
    def start(self):
        self._peripheral.flash(1)
        self._Popen = subprocess.Popen(
            [
                '/home/jay/ustreamer/ustreamer',
                '-d',  self._device,
                '-s', '192.168.0.60', '-p', '60000',
                '-r', '1280x720',
                '-m', 'MJPEG',
                '--device-timeout', '5',
                '-l'
            ]
        )
        print(f'Started webcam process {self._Popen.pid}')

    def stop(self):
        if self._Popen is not None:
            print('Stop streamer')
            self._Popen.terminate()
            self._Popen.wait()
        self._peripheral.flash(0)

    def capture(self):
        self._peripheral.flash(1)
        subprocess.run(
            [
                '/usr/bin/fswebcam',
                '-d', self._device,
                '-r', '1280x720',
                '-F', '1', '--no-banner',
                '/var/www/html/image.jpg'
            ]
        )
        self._peripheral.flash(0)

    def __del__(self):
        self.stop()
