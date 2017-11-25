#!/usr/bin/python3

from unisocket import UnisocketModel
import threading
import random
import socket
import os

class Stolas:
	def __init__(self):
		self.port = random.randrange(1025, 65536)

		self.networker = UnisocketModel(self.port, "STOLAS")
		self.networker.start()


if __name__ == "__main__":
	threading.current_thread().setName("Main__")
	eh = Stolas()

	import time
	print("Started on port {0}".format(eh.port))

	open("/tmp/unisocket_port", "w").write(str(eh.port))
	open("/tmp/unisocket_logs", "w")

	models = []
	port = random.randrange(1025, 65530)
	for _ in range(random.randrange(5, 20)):
		while True:
			n = UnisocketModel(port, str(port))
			try:
				n.start()
			except OSError:
				n.running = False # FFS just let any ghost thread die, in case
				port += 1
				continue
			else:
				break
		port += 1

		models.append(n)

	print("Ready")
	eh.networker.join()
	for obj in models:
		obj.stop()
		obj.join()
	print("Stopped")
	os.remove("/tmp/unisocket_port")
