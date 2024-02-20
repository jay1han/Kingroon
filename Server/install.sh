#!/usr/bin/bash

mkdir -v /usr/share/octobox
cp -v octo*.py /usr/share/octobox/
cp -v *.conf /usr/share/octobox/
touch /usr/share/octobox/octobox.lock
chown -v -R octoprint:octoprint /usr/share/octobox
chmod -v -R g+w /usr/share/octobox
chmod -v a+w /usr/share/octobox/octobox.lock

cp -v index.html /var/www/html
touch /var/www/html/state /var/www/html/temps /var/www/html/jobInfo /var/www/html/localIP
chown -v -R jay:www-data /var/www/html
chmod -v -R g+w /var/www/html

cp -v octocgi.py /var/www/bin/

cp -v octobox.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable octobox
systemctl restart octobox
systemctl status octobox
