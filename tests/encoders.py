#!/usr/bin/python3

import random

from stolas.betterui import pprint as print
from stolas.utils import b2i, i2b

def test_encoders():
	for e in range(0, 65536):
		stupendous_encoding_minimal = random.randrange(2, 50)
		encoded = i2b(e, stupendous_encoding_minimal)
		decoded = b2i(encoded)
		try:
			assert(len(encoded) == stupendous_encoding_minimal)
			assert(decoded == e)
		except AssertionError:
			print()
			print(decoded)
			print(e)
			print("~<s:bright]~<f:red]Error with encoders : program aborted~<s:reset_all]")
			raise
		#time.sleep(0.1)
	print("Encoders and decoders ~<s:bright]~<f:green]OK \u2713~<s:reset_all]")

if __name__ == "__main__":
	test_encoders()
