#!/usr/bin/bash

cp octobox.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable octobox
systemctl start octobox
systemctl status octobox

cp octo_*.py /home/octoprint/scripts/
