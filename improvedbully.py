from state import state
import zerorpc
import gevent
from colored import fg, attr
import time

class bully():
	def __init__(self, addr, config_file):
		self.S = state()
		self.S.state = 'Normal'

		self.check_servers_greenlet = None

		self.addr = addr

		#The sort function here arranges the addresses in an ascending order like a dictionary.
		#The first address in this list is least priority and last entry is highest priority
		self.servers = sorted([line for line in open(config_file).read().strip().split('\n')])
		print('%sMy addr: %s %s' % (fg(3), self.addr, attr(0)))
		print('%sServer list: %s%s' % (fg(3), str(self.servers), attr(0)))

		self.serverListBackup = [];

		self.n = len(self.servers)

		self.connections = []

		#this is the place where we can say we are assigning priority variable, according to the order in the list
		for i, server in enumerate(self.servers):
			if server == self.addr:
				self.priority = i
				self.connections.append(self)
			else:
				c = zerorpc.Client(timeout=5)
				c.connect('tcp://' + server)
				self.connections.append(c)

	def areYouThere(self):
		return self.priority

	def areYouNormal(self):
		if self.S.state == 'Normal':
			return True
		else:
			return False

	def halt(self, j):
		self.S.state = 'Election'
		self.S.halt = j
		return self.priority

	def newCoordinator(self, j):
		print ('%scall new coordinator%s' % (fg(3), attr(0)))
		if self.S.halt == j and self.S.state == 'Election':
			self.S.coord = j
			self.S.state = 'Normal'

	# def ready(self, j, x=None):
	# 	print ('%sI am ready%s' % (fg(3), attr(0)))
	# 	if self.S.coord == j and self.S.state == "Reorganization":
	# 		self.S.state = 'Normal'

	def election(self):
		st = time.time()
		messages = 0 
		print ('%sCheck the states of all nodes%s' % (fg(3), attr(0)))
		top = self.priority
		tp = self.priority
		print( '%shalt all nodes including this node and find top node%s' % (fg(3), attr(0)))
		self.halt(self.priority)
		self.S.state = 'Election'
		print ('I am %s' % self.S.state)
		self.S.halt = self.priority
		self.S.Up = []
		self.serverListBackup = []
		ss = self.servers
		for i, server in enumerate(self.servers):
			try:
				messages += 1
				t = self.connections[i].halt(self.priority)
				if  self.priority< t:
					top = i
					tp = t
				print( '%s%s server halted successfully!%s' % (fg(2), server, attr(0)))
			except zerorpc.TimeoutExpired:
				print( '%s%s Timeout 2! server not reachable, cannot halt%s' % (fg(1), server, attr(0)))
				ss.remove(server)
				continue
		print('election2 conducted messages: %i  time: %d', messages, time.time() - st)
		for i, server in enumerate(ss):
			try:
				messages +=1
				self.connections[i].newCoordinator(tp)
				print( ' server received new coordinator!')
			except zerorpc.TimeoutExpired:
				print( 'Timeout 3! server not reachable, election has to be restarted')
				self.election()
				return

		self.S.state = 'Normal'
		print('election3 conducted messages: %i  time: %d', messages, time.time() - st)
		self.check_servers_greenlet = self.pool.spawn(self.check())

	def recovery(self):
		self.S.halt = -1
		self.election()

	def check(self):
		while True:
			print( 'My address is ', self.addr)
			if self.S.coord == self.priority:
				print( 'I am Coordinator')
			else:
				print( 'I am Normal')

			gevent.sleep(5)
			
			if self.S.state == 'Normal' and self.S.coord == self.priority:
				for i, server in enumerate(self.servers):
					if i != self.priority:
						try:
							ans = self.connections[i].areYouNormal(param=None)
							print ('%s%s node is Up!%s' % (fg(2), server, attr(0)))
						except zerorpc.TimeoutExpired:
							print( '%s%s Timeout 5! normal node unreachable%s' % (fg(1), server, attr(0)))
							continue

						if not ans:
							print ('%s this node is not normal! starting election' % server)
							self.election()
							return
			elif self.S.state == 'Normal' and self.S.coord != self.priority:
				print( '%scheck coordinator\'s state%s' % (fg(3), attr(0)))
				try:
					result = self.connections[self.S.coord].areYouThere()
					# print( '%s%s coordinator is up%s' % (fg(2), self.servers[self.S.coord], attr(0)))
				except zerorpc.TimeoutExpired:
					#print( '%s%s coordinator down, start election%s' % (fg(3), self.servers[self.S.coord], attr(0)))
					self.timeout()

	def timeout(self):
		if self.S.state == 'Normal' or self.S.state == 'Reorganization':
			try:
				self.connections[self.S.coord].areYouThere()
				# print( '%s%s coordinator alive%s' % (fg(2), self.servers[self.S.coord], attr(0)))
				print( 'coordinator alive')
			except zerorpc.TimeoutExpired:
				# print( '%s%s Timeout 6! coordinator down, start election%s' % (fg(1), self.servers[self.S.coord], attr(0)))
				self.election()
		else:
			print( '%sstarting election%s' % (fg(3), attr(0)))
			self.election()

	def initialize(self):
		self.pool = gevent.pool.Group()
		self.recovery_greenlet = self.pool.spawn(self.recovery)