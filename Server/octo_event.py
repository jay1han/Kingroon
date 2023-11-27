#!/usr/bin/python3

from octo_lib import lock_lib, free_lib
from sys import argv as args

action = args[1]
if action == 'Power':        // KR:RR Toggle relay
    pass
elif action == 'Start':      // KR:PS 
    pass
elif action == 'End':        // KR:PE, KR:R0
    pass
elif action == 'Pause':      // KR:PP
    pass
elif action == 'Resume':     // KR:PR
    pass
elif action == 'Connecting': // KR:R1
    pass

lock = lock_lib()
lock.write()
lock.free_lib(lock, erase=False);
