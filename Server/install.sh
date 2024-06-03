#!/usr/bin/bash

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

cp -v files/99-i2c.rules /etc/udev/rules.d/

cp -v files/octobox.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable octobox
systemctl restart octobox
systemctl status octobox

