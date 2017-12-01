#!/usr/bin/python3

from unisocket import UnisocketModel
import threading
import random
import socket
import os

class Stolas:
	def __init__(self, port = random.randrange(1025, 65536)):
		self.port = port

		self.networker = UnisocketModel(self.port, "STOLAS")
		self.networker.start()

if __name__ == "__main__":
	logfile, portfile = "/tmp/unisocket_logs", "/tmp/unisocket_port"
	if os.name == "nt":
		# Windows
		logfile, portfile = "unisocket_logs", "unisocket_port"
	elif os.name == "java":
		# I have no fucken' idea. Android?
		print("I don't know that system")
		assert(False)

	threading.current_thread().setName("Main__")
	eh = Stolas()

	print("Started on port {0}".format(eh.port))

	open(portfile, "w").write(str(eh.port))
	open(logfile, "w")

	models = []
	port = eh.port
	for _ in range(random.randrange(10, 20)):
		while True:
			n = UnisocketModel(port, str(port))
			try:
				n.start()
			except OSError:
				n.running = False # FFS just let any ghost thread die, in case
				port += 1
				continue
			else:
				n.peer_add(("127.0.0.1", eh.port))
				n.peer_add(("127.0.0.1", port-1))
				break
		print("Connected peer {0}".format(port-eh.port), end = "\r")
		port += 1

		models.append(n)

	print("\nReady")
	eh.networker.join()
	print("Now killing all models")
	for obj in models:
		obj.stop()
		if obj.is_alive():
			obj.join()
	print("Stopped")
	os.remove(portfile)
