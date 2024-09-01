import fcntl, os, socket

SOCK_FILE  = '/usr/share/octobox/socket'

class Socket:
   def __init__(self):
      pass
   
   def lock_lib():
      lock = open(LOCK_FILE, 'r+')
      fcntl.lockf(lock, fcntl.LOCK_EX)
      return lock

   def free_lib(lock, erase=False):
      lock.close()
      if erase:
         os.truncate(LOCK_FILE, 0)

   def readEvent():
      lock = lock_lib()
      event = lock.read().strip()
    
      response = ''
      if event[:3] == 'KR:':
         print(f'Event "{event}"')
      if event[3] == 'C' or event[3] == 'L':
         sendUART(event)
      else:
         response = event[3:]
            
      free_lib(lock, erase=True);
      return response
