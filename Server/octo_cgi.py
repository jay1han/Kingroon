#!/usr/bin/python3
from urllib.parse import parse_qs
from os import environ
from socket import socket

SOCK_FILE  = '/usr/share/octobox/socket'

def socketWrite(message):
    pass

cgi_args = parse_qs(environ['QUERY_STRING'], keep_blank_values=True)
action = cgi_args['action'][0]

if action == 'power':
    socketWrite('POWER')
elif action == 'reboot':
    socketWrite('REBOOT')
elif action == 'flash':
    socketWrite('FLASH')
elif action == 'light':
    socketWrite('LIGHT')
elif action == 'camera':
    socketWrite('CAMERA')

print("Status: 205\n\n")
