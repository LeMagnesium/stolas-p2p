# protocol.py
# Network Protocol Constants
HELLO_BYTE = 1
GOODBYE_BYTE = 2
SHAREPEER_BYTE = 3
REQUESTPEER_BYTE = 4
MESSAGE_BYTE = 5
MESSAGEACK_BYTE = 6
MALFORMED_DATA = 7
ADVERTISE_BYTE = 8
DEATH_SEQUENCE = b"\x57\x68\x61\x74\x20\x69\x73\x20\x6c\x6f\x76\x65\x3f\x20\x42\x61\x62\x79\x20\x64\x6f\x6e\x27\x74\x20\x68\x75\x72\x74\x20\x6d\x65\x2c\x20\x64\x6f\x6e\x27\x74\x20\x68\x75\x72\x74\x20\x6d\x65\x2c\x20\x6e\x6f\x20\x6d\x6f\x72\x65"

MIN_INTEGRATION = 5
MAX_INTEGRATION = 50 # This one can be overwritten later

from hashlib import sha512
import time
import os
import random
from .utils import b2i, i2b

class Message:
	def __init__(self, **kwargs):
		self.__usig = sha512("{0}{1}{2}{3}".format(time.time(), MIN_INTEGRATION, kwargs, os.urandom(random.randrange(1, 256))).encode("utf8")).digest()

		timestamp = kwargs.get("timestamp", None)
		if timestamp != None:
			self.set_timestamp(timestamp)

		ttl = kwargs.get("ttl", None)
		if ttl: # TTL cannot be 0
			self.set_ttl(ttl)

		channel = kwargs.get("ttl", None)
		if channel:
			self.set_channel(channel)

		payload = kwargs.get("payload", None)
		if payload:
			self.set_payload(payload)

		if kwargs.get("defaults", False):
			self.__set_defaults()

	def __eq__(self, value):
		if not isinstance(value, Message):
			return False

		return self.usig() == value.usig() and self.timestamp == value.timestamp and self.ttl == value.ttl and self.channel == value.channel and self.payload == value.payload

	def __neq__(self, value):
		return not self.__eq__(value)

	def __set_defaults(self):
		self.set_timestamp(0)
		self.set_ttl(60)
		self.set_channel("")

	def usig(self):
		return hex(b2i(self.__usig))[2:]

	def implode(self):
		"""Implode the python object into a binary payload"""
		if self.timestamp == None:
			raise TypeError("Timestamp is None")
		if self.ttl == None:
			raise TypeError("TTL is None")
		if self.channel == None:
			raise TypeError("Channel Tuning Parameter is None")
		if self.payload == None:
			raise TypeError("Payload is None")

		data = b""
		data += self.__usig
		data += i2b(self.timestamp, minimal = 8)
		data += i2b(self.ttl, minimal = 4)
		data += i2b(len(self.channel))
		data += self.channel.encode("utf8")
		data += self.payload

		return data

	def is_complete(self):
		return not None in [self.timestamp, self.ttl, self.channel, self.payload]

	def is_alive(self):
		return time.time() < self.timestamp + self.ttl

	@staticmethod
	def explode(data):
		if type(data) != type(b""):
			raise TypeError("Data must be provided as a Byte object")
		if len(data) < 14:
			raise ValueError("Malformed message data")

		self = Message()
		self.__usig = data[:64]
		data = data[64:]
		self.set_timestamp(b2i(data[:8]))
		self.set_ttl(b2i(data[8:12]))
		chanlen = data[12]
		if len(data) < 14 + chanlen:
			raise ValueError("Malformed message data : channel is too long")
		self.set_channel(data[13:13+chanlen].decode("utf8"))
		self.set_payload(data[13+chanlen:])

		return self

	def set_timestamp(self, timestamp):
		if not type(timestamp) in map(type, [int(), float()]):
			raise TypeError("Timestamp provided is of type {0}".format(type(timestamp)))

		timestamp = int(timestamp)
		if timestamp < 0:
			raise ValueError("Timestamp provided is negative")


		self.timestamp = timestamp

	def get_timestamp(self):
		return self.timestamp

	def set_ttl(self, ttl):
		if not type(ttl) in map(type, [int(), float()]):
			raise TypeError("TTL should be provided as a number")

		ttl = int(ttl)
		if ttl < 60 or ttl > 223200:
			raise ValueError("TTL must be in range(60, 223200)")

		self.ttl = ttl

	def get_ttl(self):
		return self.ttl

	def set_channel(self, channel):
		if not type(channel) == type(""):
			raise TypeError("Channel must be a string")

		if len(channel) > 255:
			raise ValueError("Channel cannot be longer than 255 characters")

		self.channel = channel

	def get_channel(self):
		return self.channel

	def set_payload(self, payload):
		if not type(payload) == type(b""):
			raise TypeError("Payload must be a byte object")
		if len(payload) == 0:
			raise ValueError("Payload must not be empty")

		self.payload = payload

	def get_payload(self):
		return self.payload
