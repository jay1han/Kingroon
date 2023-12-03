#!/usr/bin/python3
import fcntl
from urllib.parse import parse_qs
from os import environ

LOCK_FILE  = '/usr/share/octobox/octobox.lock'
def lock_write(kr):
    lock = open(LOCK_FILE, 'w+')
    fcntl.lockf(lock, fcntl.LOCK_EX)
    lock.write(f'KR:{kr}\n')
    lock.close()

cgi_args = parse_qs(environ['QUERY_STRING'], keep_blank_values=True)
action = cgi_args['action'][0]
with open('/usr/share/octobox/cgi.log', 'w+') as log:
    log.write(f'action={action}\n')

if action == 'switch':
    lock_write('RR')
elif action == 'light':
    lock_write('CC')

print('Location: \\\n\n')
