#!/usr/bin/python3

import threading
import queue
import random
import time

import stolas.protocol as protocol
from stolas.unisocket import UnisocketModel, i2b, b2i

randport = lambda: random.randrange(1024, 65536)


class Stolas:
	def __init__(self, **kwargs):
		self.port = kwargs.get("port", randport())
		self.running = False

		self.networker = UnisocketModel(self.port, name = "STOLAS")
		self.networker.start()

		self.processor = threading.Thread(
			name = "Cpu",
			target = self.__processor_unit
		)

		self.now = None
		self.vacuum_timer = 60
		self.message_stack = {}

	def stop(self):
		self.running = False
		self.networker.stop()

	def join(self):
		self.networker.join()
		self.processor.join()

	def start(self):
		self.running = True
		self.processor.start()

	def message_vacuum(self):
		for ts in list(self.message_stack.keys()):
			msg = self.message_stack[ts]
			if msg.ttl > time.time() - msg.timestamp:
				del self.message_stack[ts]

	def is_alive(self):
		return self.running

	def __processor_unit(self):
		self.now = time.time()
		while self.running:
			if not self.networker.running:
				self.running = False

			dt = time.time() - self.now
			self.vacuum_timer -= dt
			self.now += dt
			if self.vacuum_timer <= 0:
				self.message_vacuum()

			try:
				mtype, message = self.networker.imessages.get(timeout=0)
			except queue.Empty:
				continue

			if mtype == "message":
				# Create the message by exploding the binary blob
				msg = protocol.Message.explode(message)
				self.message_stack[msg.get_timestamp()] = msg
				print("\r{0}\n[-]> ".format(msg.payload), end = " ") #FIXME: Temporary
			self.networker.imessages.task_done()

		#print("Shutting down")

	def message_broadcast(self, message):
		msgobj = protocol.Message()
		msgobj.set_payload(message)
		msgobj.set_timestamp(time.time())
		msgobj.set_ttl(70)
		msgobj.set_channel("")

		data = msgobj.implode()

		payload_len = i2b(len(data), 2)
		if payload_len == b"\0\0":
			return False

		self.networker.peerlock.acquire()
		for peerid in self.networker.peers:
			self.networker.peer_send(peerid, i2b(protocol.MESSAGE_BYTE) + payload_len + data)
		self.networker.peerlock.release()
		self.message_stack[msgobj.get_timestamp()] = msgobj
