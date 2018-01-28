# ~ stolas/protocol.py: Protocol Variable Module ~
#
#  This module define network protocol constants as well as
#   utility classes linked to the messaging protocol.
#

#	#	#
# Network Protocol constants defined for more modularity and less hardcoded and
#  meaningless variables scattered in the code. Those variables are mostly
#  packet headers (see docs/protocol.md).
# FIXME: Discontinue the Death Sequence
HELLO_BYTE = 1
GOODBYE_BYTE = 2
SHAREPEER_BYTE = 3
REQUESTPEER_BYTE = 4
MESSAGE_BYTE = 5
MESSAGEACK_BYTE = 6
MALFORMED_DATA = 7
ADVERTISE_BYTE = 8
DEATH_SEQUENCE = b"\x57\x68\x61\x74\x20\x69\x73\x20\x6c\x6f\x76\x65\x3f\x20\x42\x61\x62\x79\x20\x64\x6f\x6e\x27\x74\x20\x68\x75\x72\x74\x20\x6d\x65\x2c\x20\x64\x6f\x6e\x27\x74\x20\x68\x75\x72\x74\x20\x6d\x65\x2c\x20\x6e\x6f\x20\x6d\x6f\x72\x65"

# Integration variables
# FIXME: When global configuration is operational, move those there.
MIN_INTEGRATION = 5
MAX_INTEGRATION = 50

from hashlib import sha512   # Required for uing generation
import time                  # `time.time`
import os                    # `os.urandom`
import random                # `random.randrange`

from .utils import b2i, i2b

class Message:
	"""Message Class.
	This class is meant to represent a communication message in the upper part
	 of Stolas' protocol. It can be initialized with a custom channel name and
	 Time To Live (TTL). The payload is required."""
	def __init__(self, **kwargs):
		self.__usig = sha512("{0}{1}{2}{3}".format(time.time(), MIN_INTEGRATION, kwargs, os.urandom(random.randrange(1, 256))).encode("utf8")).digest()

		# Optional parameters
		self.ttl = kwargs.get("ttl", 60)
		if self.ttl: # TTL cannot be 0
			self.set_ttl(self.ttl)

		self.channel = kwargs.get("channel", "")
		if self.channel:
			self.set_channel(self.channel)

		# Mandatory parameters
		# Timestamp can be and will be overwritten during binary explosion.
		self.timestamp = int(time.time())

		self.payload = kwargs.get("payload", None)
		if self.payload:
			self.set_payload(self.payload)

	def __eq__(self, value):
		"""Gives self == value."""
		if not isinstance(value, Message):
			return False

		return self.usig() == value.usig() and self.timestamp == value.timestamp and self.ttl == value.ttl and self.channel == value.channel and self.payload == value.payload

	def __neq__(self, value):
		"""Givess self != value."""
		return not self.__eq__(value)

	def __repr__(self):
		"""Gives str(self)."""
		return "protocol.Message(chan=\"{0}\", payload={1}, ttl={2}, timestamp={3})".format(
			self.channel,
			self.payload[:10] + b'...',
			self.ttl,
			self.timestamp
	)

	def usig(self):
		"""Returns self's (hopefully) Unique Signature."""
		return hex(b2i(self.__usig))[2:]

	def implode(self):
		"""Implode the Message's fields into a binary payload."""
		if self.timestamp == None:
			raise TypeError("Timestamp is None")
		if self.ttl == None:
			raise TypeError("TTL is None")
		if self.channel == None:
			raise TypeError("Channel Tuning Parameter is None")
		if self.payload == None:
			raise TypeError("Payload is None")

		# Check docs/protocol.md for details
		data = b""
		data += self.__usig
		data += i2b(self.timestamp, minimal = 8)
		data += i2b(self.ttl, minimal = 4)
		data += i2b(len(self.channel))
		data += self.channel.encode("utf8")
		data += self.payload

		# Since the payload size is encoded on three bytes in a message packet,
		#  we must ensure our data is correctly divided
		if len(data) >= 2**24:
			raise RuntimeError("Implosion payload size is above or on limit (2**24)")

		return data

	def is_complete(self):
		"""Checks for missing fields."""
		return not None in [self.timestamp, self.ttl, self.channel, self.payload]

	def is_alive(self):
		"""Check whether or not we've gone over our Time To Live."""
		return time.time() < self.timestamp + self.ttl

	@staticmethod
	def explode(data):
		"""Explode binary data into a Message object."""
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
		"""Sets the Message's timestamp. Checks whether the timestamp is valid beforehand."""
		if not type(timestamp) in map(type, [int(), float()]):
			raise TypeError("Timestamp provided is of type {0}".format(type(timestamp)))

		timestamp = int(timestamp)
		if timestamp < 0:
			raise ValueError("Timestamp provided is negative")

		self.timestamp = timestamp

	def get_timestamp(self):
		"""Returns the timestamp."""
		return self.timestamp

	def set_ttl(self, ttl):
		"""Sets the Time To Live. Checks whether or not it is valid beforehand."""
		if not type(ttl) in map(type, [int(), float()]):
			raise TypeError("TTL should be provided as a number")

		ttl = int(ttl)
		if ttl < 60 or ttl > 223200:
			raise ValueError("TTL must be in range(60, 223200)")

		self.ttl = ttl

	def get_ttl(self):
		"""Returns the Time To Live."""
		return self.ttl

	def set_channel(self, channel):
		"""Sets the message channel. Checks whether or not it is valid beforehand."""
		if not type(channel) == type(""):
			raise TypeError("Channel must be a string")

		if len(channel) > 255:
			raise ValueError("Channel cannot be longer than 255 characters")

		self.channel = channel

	def get_channel(self):
		"""Returns the message channel."""
		return self.channel

	def set_payload(self, payload):
		"""Sets the payload. Checks whether or not it is valid beforehand."""
		if not type(payload) == type(b""):
			raise TypeError("Payload must be a byte object")
		if len(payload) == 0:
			raise ValueError("Payload must not be empty")
		if len(payload) > 2**24:
			raise ValueError("Payload length is superior to 2**24.")

		self.payload = payload

	def get_payload(self):
		"""Returns the payload."""
		return self.payload
