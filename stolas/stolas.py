#!/usr/bin/python3

import threading
import queue
import random
import time
import os, os.path
import logging			# `logging.Logger`, `logging.Formatter`, `logging.StreamHandler`
import logging.handlers	# `logging.handlers.RotatingFileHandler`

import stolas.protocol as protocol
from stolas.unisocket import UnisocketModel, i2b, b2i, PhantomLogger

randport = lambda: random.randrange(1024, 65536)

class MessagePile:
	on_add_callbacks = []
	def __init__(self):
		"""Initialize the Message Stack object. Needs no parameters."""
		self.data = {}
		self.__lock = threading.Lock()

	def __new_msgid(self):
		"""Internal. Get a new message ID."""
		# This, here, is a trick. If our list has no index holes, then the only
		# number returned by the generator will be the next index (hence '+1'),
		# but if holes remain then this generator will return the first one of
		# them instead.
		return [x for x in range(len(self.data)+1) if not self.data.get(x, False)][0]

	def __contains__(self, key):
		return True in [self.data[mid] == key for mid in self.data]

	def __len__(self):
		return len(self.data)

	def register_on_add(self, func):
		self.on_add_callbacks.append(func)

	def add(self, message):
		"""Add a message onto the pile. Expects a stolas.protocol.Message object."""
		if message == None or not isinstance(message, protocol.Message):
			raise TypeError("Invalid data type {0}: expected stolas.protocol.Message")

		elif not message.is_complete():
			raise ValueError("Incomplete Message object provided. One field is 'None'")

		# Otherwise, we're okay to go
		elif message.is_alive():
			self.__lock.acquire()
			nmid = self.__new_msgid()
			self.data[nmid] = message
			self.__lock.release()
			for callback in self.on_add_callbacks:
				callback(message)
			return nmid

	def get(self, message_id, alternative = None):
		return self.data.get(message_id, alternative)

	def get_random(self):
		self.__lock.acquire()
		acceptable = [mid for mid in self.data if self.data[mid].is_alive()]
		if len(acceptable) == 0:
			self.__lock.release()
			return None

		msg = self.get(random.choice(acceptable))
		self.__lock.release()
		return msg

	def list(self):
		return self.data.copy()

	def delete(self, message_id):
		if not self.get(message_id, False):
			return False

		self.__lock.acquire()
		del self.data[message_id]
		self.__lock.release()
		return True

	def vacuum(self):
		for mid in list(self.data.keys()):
			# We use the key list so that it is a separate entity from the pile
			# which size we cannot guarantee won't change during vacuuming
			msg = self.get(mid)
			if msg and not msg.is_alive():
				self.delete(mid)

class Stolas:
	def __init__(self, **kwargs):
		self.port = kwargs.get("port", randport())
		self.running = False
		self.name = kwargs.get("name", None)
		if self.name == None:
			self.name = hex(random.randrange(pow(16,8),pow(16,16)))[2:10]

		if kwargs.get("logging", False):
			self.__logging_setup()
		else:
			self.logger = PhantomLogger()

		if kwargs.get("logdown", False):
			self.networker = UnisocketModel(self.port, name = "US," + self.name, logger = self.logger)
		else:
			self.networker = UnisocketModel(self.port, name = "US," + self.name)

		self.networker.start()

		self.processor = threading.Thread(
			name = "CPU," + self.name,
			target = self.__processor_unit
		)

		self.now = None
		self.vacuum_timer = 5
		self.mpile = MessagePile()
		self.distribution_timer = 10

	def __repr__(self):
		return "Stolas(name='{0}',port='{1}')".format(self.name, self.port)

	def __del__(self):
		del self.networker
		#self.logger.debug("Stolas object deleted")
		if getattr(self, "mpile", None) != None:
			del self.mpile

	def __logging_setup(self):
		logfile = "stolas_logs"

		if os.name == "posix":
			logfile = "/tmp/stolas_logs"
		elif os.name == "nt":
			filepath = os.getenv('APPDATA') + os.path.sep + "Stolas"
			try:
				os.mkdir(filepath)
			except FileExistsError:
				pass
			except PermissionError:
				logfile = "stolas_logs"
			else:
				logfile = filepath + os.path.sep + logfile

		"""Internal. Setup logging and logging handlers."""
		# Create a console handler
		self.logger = logging.Logger("Stolas(" + self.name + ")")
		console = logging.StreamHandler()
		console.setLevel(logging.CRITICAL)
		c_formatter = logging.Formatter('%(message)s') # Keep it simple
		console.setFormatter(c_formatter)
		self.logger.addHandler(console)

		# Create the file handler.
		file_lo = logging.handlers.RotatingFileHandler(filename = logfile)
		file_lo.setLevel(logging.DEBUG)
		f_formatter = logging.Formatter('[%(asctime)s][%(levelname)7s][%(name)20s:%(funcName)25s:%(lineno)3s][%(threadName)20s] %(message)s')
		file_lo.setFormatter(f_formatter)
		self.logger.addHandler(file_lo)

		self.logger.debug("Logger Ready")

	def stop(self):
		self.running = False
		self.networker.stop()

	def join(self):
		self.networker.join()
		self.processor.join()

	def start(self):
		self.running = True
		self.processor.start()

	def is_alive(self):
		return self.running

	def message_distribution(self):
		self.distribution_timer = random.randrange(9,12)
		randomly_selected_message = self.mpile.get_random()
		if not randomly_selected_message:
			return
		self.message_broadcast(randomly_selected_message)

	def __processor_unit(self):
		self.now = time.time()
		while self.running:
			if not self.networker.running:
				self.running = False

			dt = time.time() - self.now
			self.vacuum_timer -= dt
			self.distribution_timer -= dt
			self.now += dt
			if self.vacuum_timer <= 0:
				self.logger.debug("Vacuuming the MPile")
				self.mpile.vacuum()
				self.vacuum_timer = 5

			if self.distribution_timer <= 0:
				self.message_distribution()
				# Parabolic timer
				#self.distribution_timer = (lambda x: -(10/65025) * (x**2 - 1)**2 + 10)(len(self.mpile.list()))
				# Hyperbolic timer
				self.distribution_timer = (lambda x: 1/(x-(9/10)))(len(self.mpile.list()))

			try:
				mtype, message = self.networker.imessages.get(timeout=0)
			except queue.Empty:
				continue

			if mtype == "message":
				# Create the message by exploding the binary blob
				msg = protocol.Message.explode(message)
				if not msg in self.mpile and msg.is_alive():
					nmid = self.mpile.add(msg)
					self.logger.info("Logged in message {0}".format(nmid))
			self.networker.imessages.task_done()

		self.logger.info("Shutting down CPU")

	def message_broadcast(self, msgobj):
		data = msgobj.implode()

		payload_len = i2b(len(data), 3)
		if payload_len == b"\0\0":
			return False

		self.networker.peerlock.acquire()
		for peerid in self.networker.peers:
			self.networker.peer_send(peerid, protocol.MESSAGE_BYTE, payload_len + data)
		self.networker.peerlock.release()
		if not msgobj in self.mpile and msgobj.is_alive():
			mid = self.mpile.add(msgobj)
			self.logger.info("Logged in message {0}".format(mid))
