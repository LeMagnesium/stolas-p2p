#!/usr/bin/python3

import threading
import queue
import random

import stolas.protocol
from stolas.unisocket import UnisocketModel, i2b, b2i

class Stolas:
	def __init__(self, port = None):
		self.port = port if port != None else random.randrange(1024, 65536)
		self.running = False

		self.networker = UnisocketModel(self.port, "STOLAS")
		self.networker.start()

		self.processor = threading.Thread(
			name = "Cpu",
			target = self.__processor_unit
		)

	def stop(self):
		self.running = False
		self.networker.stop()

	def join(self):
		self.networker.join()
		self.processor.join()

	def start(self):
		self.running = True
		self.processor.start()

	def __processor_unit(self):
		while self.running:
			if not self.networker.running:
				self.running = False

			try:
				mtype, message = self.networker.imessages.get(timeout=0)
			except queue.Empty:
				continue

			#print("\n{0}".format(message))
			self.networker.imessages.task_done()

		print("Shutting down")

	def message_broadcast(self, message):
		payload_len = i2b(len(message), 2)
		if payload_len == b"\0\0":
			return False

		self.networker.peerlock.acquire()
		for peerid in self.networker.peers:
			self.networker.peer_send(peerid, i2b(protocol.MESSAGE_BYTE) + payload_len + message)
		self.networker.peerlock.release()
