#!/usr/bin/bash

cp webcam.service /etc/systemd/system/
systemctl daemon-reload
systemctl restart webcam
systemctl status webcam

