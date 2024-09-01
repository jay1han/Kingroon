#!/usr/bin/bash

apt install python3-smbus

mkdir -v /usr/share/octobox
cp -v octo*.py /usr/share/octobox/
touch /usr/share/octobox/socket
chown -v -R octoprint:octoprint /usr/share/octobox
chmod -v -R g+w /usr/share/octobox
chmod -v a+w /usr/share/octobox/socket

cp -v files/index.html /var/www/html
touch /var/www/html/json
chown -v -R octoprint:www-data /var/www/html
chmod -v -R g+w /var/www/html

cp -v octocgi.py /var/www/bin/

addgroup gpio
addgroup i2c
addgroup pwm
usermod -aG gpio,i2c,pwm,www-data octoprint 
usermod -aG gpio,i2c,pwm,www-data jay

cp -v files/99-i2c.rules /etc/udev/rules.d/
chmod g+w /sys/class/pwm/pwmchip0/export
chmod g+w /sys/class/pwm/pwmchip0/unexport
chmod g+w /sys/class/pwm/pwmchip0/pwm1/enable
chmod g+w /sys/class/pwm/pwmchip0/pwm1/duty_cycle
chmod g+w /sys/class/pwm/pwmchip0/pwm1/period
chmod g+w /sys/class/pwm/pwmchip0/pwm1/polarity
chmod g+w /sys/class/pwm/pwmchip0/pwm2/enable
chmod g+w /sys/class/pwm/pwmchip0/pwm2/duty_cycle
chmod g+w /sys/class/pwm/pwmchip0/pwm2/period
chmod g+w /sys/class/pwm/pwmchip0/pwm2/polarity

cp -v files/octobox.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable octobox
systemctl restart octobox
systemctl status octobox

