#!/usr/bin/python3

from unisocket import UnisocketModel, i2b, b2i
import threading
import random
import socket
import os

class Stolas:
	def __init__(self, port = None):
		self.port = port if port != None else random.randrange(1024, 65536)

		self.networker = UnisocketModel(self.port, "STOLAS")
		self.networker.start()

import time

def test_encoders():
	for e in range(1024, 65536):
		encoded = i2b(e)
		assert(len(encoded) < 3)
		print(encoded, end = "\r")
		decoded = b2i(encoded)
		try:
			assert(decoded == e)
		except AssertionError:
			print()
			print(decoded)
			print(e)
			raise
		#time.sleep(0.1)
	print("Encoders and decoders OK \u2713")

def __send_shutdown(obj):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect(('127.0.0.1', obj.port))
	s.send(obj.networker.death_sequence + b"\x02")
	s.close()
	print("Network is about to collapse...")

def test_network():
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

	print("\nReadying...")
	tr = threading.Timer(random.randrange(1, 10), lambda: __send_shutdown(eh))
	tr.start()
	print("Ready!")
	eh.networker.join()
	print("Now killing all models")
	for obj in models:
		obj.stop()
		obj.join()

	time.sleep(3)
	print("Stopped")
	assert(threading.active_count() == 1)
	os.remove(portfile)

def create_ponderation(ran):
	d = []
	for e in range(ran)[::-1]:
		d += [e+1] * (ran-e)
	return d


if __name__ == "__main__":
	test_encoders()
	for e in range(random.choice(create_ponderation(10))):
		test_network()
