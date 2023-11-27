#!/usr/bin/python3

from octo_lib import lock_lib, free_lib, sendUART
from sys import argv as args

action = args[1]

lock = lock_lib()
if action == 'Power':        # KR:RR Toggle relay
    sendUART('KR:RR')

elif action == 'Start':      # KR:PS
    sendUART('KR:PS')

elif action == 'End':        # KR:PE, KR:R0
    sendUART('KR:PE')
    sendUART('KR:R0')

elif action == 'Pause':      # KR:PP
    sendUART('KR:PP')

elif action == 'Resume':     # KR:PR
    sendUART('KR:PR')

free_lib(lock, erase=False);
