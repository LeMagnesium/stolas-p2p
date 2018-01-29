#!/usr/bin/python3

import zlib, os, math, gzip, time
from markovgenerator import MarkovGenerator

monster = MarkovGenerator()

def gen_payload(size):
	# Most of our big payloads will have a lot of randomized junk...
	# ...Yet most of our packets will be small
	return os.urandom(size)

def gen_real_payload(size, remnant = b""):
	payload = remnant
	delta = 0
	threshold = 1024
	then = time.time()
	plsize = len(payload)
	qtt = 35
	while plsize < size:
		for char in monster.puke():
			payload += char.encode("utf8")
			plsize += 1
			delta = (delta + 1)%threshold
			if delta == 0:
				dtime = time.time() - then
				pct = int(plsize/size * qtt)
				if pct >= qtt:
					pct = qtt
				print("[{0}{1}]{2:3.0f}Kb/s".format(
					pct * '=',
					(qtt - pct) * ' ',
					threshold/dtime / 1024
				), end = "\r")
				then = time.time()

	return payload[:size]

def show_comprs(size, csize, time = 0):
	print("Original payload size : {0:5s} -> {1:03.3f}% [puked in {2:.0f}s]".format(show_size(size), csize/size * 100, time))

def show_size(size):
	slog = math.log2(size)
	if slog < 10:
		return "{}b".format(size)
	elif slog < 20:
		return "{0:d}Kb".format(int(size/2**10))
	elif slog < 30:
		return "{0:d}Mb".format(int(size/2**20))
	elif slog < 40:
		return "{0:d}Gb".format(int(size/2**30))

def test_compression_advantages():
	upperb = 2**24
	lowerb = 2**0

	pld = b""
	genreal = True
	while lowerb <= upperb:
		try:
			now = time.time()
			pld = gen_real_payload(lowerb, pld)
			then = time.time() - now
			upc = len(gzip.compress(pld))
		except MemoryError:
			break
		except RuntimeError:
			print("Unable to use pseudo-real text generation. Please run tests/markovgenerator.py to feed the generator first.")
			break
		show_comprs(lowerb, upc, then)
		lowerb *= 2

if __name__ == "__main__":
	test_compression_advantages()
