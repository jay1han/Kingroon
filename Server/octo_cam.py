import subprocess, os
from octo_periph import Peripheral

class Camera:
    def __init__(self, peripheral: Peripheral):
        self.peripheral = peripheral
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
            if re.search('Camera', line):
                usb_device = line_no

        self.device = list_devices[usb_device].strip()
        self.capture()
        
    def start(self):
        self.peripheral.flash(1)
        webcamPopen = ['/usr/local/bin/mjpg_streamer',
                       '-i', f'/usr/local/lib/mjpg-streamer/input_uvc.so -d {self.device} -n -r 1280x720',
                       '-o', '/usr/local/lib/mjpg-streamer/output_http.so -w /usr/local/share/mjpg-streamer/www']
        self.Popen = subprocess.Popen(webcamPopen)
        print(f'Started webcam process {self.Popen.pid}')

    def stop(self):
        if self.Popen is not None:
            print('Stop streamer')
            self.Popen.terminate()
            self.Popen.wait()
        self.capture()
        self.peripheral.flash(0)

    def capture(self):
        self.peripheral.flash(1)
        subprocess.run(['/usr/bin/fswebcam', '-d', self.device, '-r', '1280x720', '-F', '1', '--no-banner', '/var/www/html/image.jpg'])
        self.peripheral.flash(0)

    def __del__(self):
        self.stop()
