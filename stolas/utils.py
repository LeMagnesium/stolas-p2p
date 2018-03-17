# ~ stolas/utils.py: Utilities Module ~
#
#  This module defines utility functions for repeated operations in
#   the project's different sections (i.e. byte conversion, etc).
#

def i2b(n, minimal = -1):
	"""Integer to Bytes (Big Endian)"""
	# If the integer is null, just return the empty byte with the desired
	#  length.
	if n == 0:
		return b"\0" if minimal <= 0 else b"\0" * minimal

	b = b""
	while n > 0:
		neon = n & 255
		# Latin is used so that we have the whole [0;256[ range for ourselves
		b = chr(neon).encode("latin") + b
		n = n >> 8

	# We add the 0 byte before our chain as many times as needed to
	if minimal > 0:
		b = (b"\0" * (minimal - len(b))) + b
	return b

def b2i(b):
	"""Bytes to Integers (Big Endian)"""
	n = 0
	for bt in b:
		n += bt
		n = n << 8
	return n >> 8

class PhantomLogger:
	def debug(msg, *args, **kwargs):
		pass

	def warning(msg, *args, **kwargs):
		pass

	def info(msg, *args, **kwargs):
		pass


