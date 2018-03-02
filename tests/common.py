import sys
from io import StringIO

def network_collapse(cluster):
	i = 1
	for obj in cluster:
		obj.stop()

	for obj in cluster:
		obj.join()
		print("Terminating model {0}...".format(i), end = "\r")
		i += 1
	print("\nAll models terminated")

def swap_in(stdout):
	"""Swap in the current stdout object for one given as argument (requires that object to support read/write operations)."""
	old = sys.stdout
	sys.stdout = stdout
	return old

def swap_out():
	"""Swap out the current stdout object for a StringIO object."""
	stdout = sys.stdout
	sys.stdout = StringIO()
	return stdout

def mean(lst):
	return sum(lst)/len(lst)

##########################################
# Old Functions
#

def __send_shutdown(obj):
	"""Remnant of the time when we had to send the Death Sequence to shut down peers."""
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect(('127.0.0.1', obj.port))
	s.send(obj.networker.death_sequence + b"\x02")
	s.close()
	print("Network is about to collapse...")

def prepare_logging_locations():
	"""Logging location determination function from before the time we used logging from python's logger library."""
	logfile, portfile = "/tmp/unisocket_logs", "/tmp/unisocket_port"
	if os.name == "nt":
		# Windows
		logfile, portfile = "unisocket_logs", "unisocket_port"
	elif os.name == "java":
		# I have no fucken' idea. Android?
		print("I don't know that system")
		assert(False)

	return portfile, logfile

def gen_payload(size):
	# Most of our big payloads will have a lot of randomized junk...
	# ...Yet most of our packets will be small
	return os.urandom(size)

def old_build_network(start_port, total = None):
	"""Defunct UniSocket network builder."""
	models = []
	ports = []
	port = start_port
	total = total or random.randrange(5, 10)
	print("Starting from {0}".format(start_port))

	for progress in range(total):
		while True:
			n = UnisocketModel(port, name = str(port-start_port)) # Should fail the first time
			try:
				n.start()
				if len(ports) > 0:
					rport = random.choice(ports)
					tr = threading.Thread(target = __trigger_connection, args = (n, ("127.0.0.1", rport)))
					tr.start()
					print("Connecting {0} to {1}".format(port, rport))
				ports.append(port)
				models.append(n)
				port += 1
				print("Connected peer {0}/{1}  ".format(progress+1, total), end = "\r")

			except OSError:
				n.stop() # FFS just let any ghost thread die, in case
				port += 1
				continue
			else:
				break

	print("")

	isolated = [x for x in models if len(x.peers) == 0]
	print(ports)
	print(isolated)
	assert(len(isolated) == 0)
	return models
