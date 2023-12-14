#!/usr/bin/bash

mkdir -v /usr/share/octobox
chmod -v a+w /usr/share/octobox
cp -v octo*.py index.html /usr/share/octobox/
touch /usr/share/octobox/octobox.lock
chown -v -R octoprint:octoprint /usr/share/octobox
chmod -v -R g+w /usr/share/octobox
chmod -v a+w /usr/share/octobox/octobox.lock
rm -v /var/www/html/index.html
cp -v octocgi.py /var/www/bin/

cp -v octobox.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable octobox
systemctl restart octobox
systemctl status octobox
