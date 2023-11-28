#!/usr/bin/bash

mkdir /usr/share/octobox
chmod a+w /usr/share/octobox
cp octo_*.py /usr/share/octobox/
touch /usr/share/octobox/octobox.lock
chown -R octoprint:octoprint /usr/share/octobox
chmod -R g+w /usr/share/octobox
chmod a+w /usr/share/octobox/octobox.lock
rm /var/www/html/index.html
cp octocgi.py /var/www/bin/

cp octobox.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable octobox
systemctl restart octobox
systemctl status octobox
