#!/usr/bin/python3

from octo_lib import lock_lib, free_lib
from sys import argv as args

action = args[1]
if action == 'PrintStarted':
    pass
elif action == 'PrintEnded':
    pass
elif action == 'Connecting':
    pass

lock = lock_lib()
lock.write()
lock.free_lib(lock, erase=False);
