#!/usr/bin/python3

from octo_lib import lock_lib, free_lib, sendUART
from sys import argv as args

action = args[1]

lock = lock_lib()
if action == 'Connect':      # KR:R1 keep power on
    lock.write('KR:R1\n')

elif action == 'Start':      # KR:PS
    lock.write('KR:PS\n')

elif action == 'End':        # KR:PE, KR:R0
    lock.write('KR:PE\n')

elif action == 'Pause':      # KR:PP
    lock.write('KR:PP\n')

elif action == 'Resume':     # KR:PR
    lock.write('KR:PR\n')

elif action == 'Cancel':     # KR:PC
    lock.write('KR:PC\n')

free_lib(lock, erase=False);
