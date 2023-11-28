#!/usr/bin/python3
import fcntl

LOCK_FILE  = '/usr/share/octobox/octobox.lock'

lock = open(LOCK_FILE, 'w+')
fcntl.lockf(lock, fcntl.LOCK_EX)
lock.write('KR:RR\n')
lock.close()

print('Location: \\\n\n')
