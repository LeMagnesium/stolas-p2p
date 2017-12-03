# Some conversion things
def i2b(n, minimal = -1):
	"""Integer to Bytes (Big Endian)"""
	if n == 0:
		return b"\0" if minimal <= 0 else b"\0" * minimal
	b = b""
	while n > 0:
		neon = n & 255
		# Latin is used so that we have the whole [0;256[ range for ourselves
		b = chr(neon).encode("latin") + b
		n = n >> 8

	if minimal > 0:
		while len(b) < minimal:
			b = b"\0" + b
	return b

def b2i(b):
	"""Bytes to Integers (Big Endian)"""
	n = 0
	for bt in b:
		n += bt
		n = n << 8
	return n >> 8
