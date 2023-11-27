#!/usr/bin/bash

cp octo_*.py /home/octoprint/scripts/
touch /home/octoprint/scripts/octobox.lock
chown -R octoprint:octoprint /home/octoprint/scripts
chmod -R g+w /home/octoprint/scripts
cp html/*.html /var/www/html/

cp octobox.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable octobox
systemctl start octobox
systemctl status octobox
