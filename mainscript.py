import zerorpc
import sys
from state import state
from improvedbully import bully

import socket
print(socket.gethostbyname(socket.gethostname()))
addr = sys.argv[1]
bully = bully(addr, 'server_config_local')
# bully = bully(addr, 'server_config')
s = zerorpc.Server(bully)
s.bind('tcp://' + addr)
bully.initialize()
# initialize server
print('[%s] initializing Server' % addr)
s.run()