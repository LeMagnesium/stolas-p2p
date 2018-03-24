import time
import random
from stolas.betterui import pprint as cupprint
from stolas.betterui import pretty_printing
from os import name as osname
from common import swap_in, swap_out, mean
from markovgenerator import MarkovGenerator


# From 72933fd89fe4efc9571ee58b312a2ad4f8913e2b
# A wrapper around print where we do our business
def olpprint(value = "", **kwargs):
	"""A wrapper around print created to parse and replace betterui's console
	altering codes before feeding them to the normal print function. It is
	recommended, for easy compatibility, to import this specific method as
	'print' in your code."""
	pstring = str(value)

	# Filter out all that is not ASCII if we're on Windows
	# Chances are that code is run from CMD on a school computer and those
	#  don't handle unicode at all.
	# FIXME: It is possible this section is making the CLI lag in CMD
	if osname == "nt":
		pstring = bytearray([x for x in pstring.encode("utf8") if x in range(128)]).decode("utf8")

	#	#
	# Substitution mechanic
	# FIXME: It is also possible this section is making the CLI lag in CMD
	# FIXME: Create multi handling and single-time parsing mechanic
	if pstring.find("~<") != -1:
		for code in pretty_printing:
			for variant in pretty_printing[code]:
				pstring = pstring.replace("~<{0}:{1}]".format(code, variant), pretty_printing[code][variant])

	print(pstring, **kwargs)

string_data = [
	"-" * 1000,
	"~<" * 250,
	"tests/network.py\t| 97 ~<f:green]" + '+' * 38 + "~<f:red]" + '-' * 83 + "~<s:reset_all]",
	"~Considering the following: ~<fbs:green,blue,bold]IT SUCKS~<s:reset_all]",
	"~<get:rekt]~<get:shrekt]~<s:reset_al]",
	"~~~moo<ss:corrupted_stuff that shouldn't work]",
	"There's... Antimony Arsenic Selenium Uranium, and Hafnium Osmium and Astatine and Radium, and Mangamene and Mercury, Molybdenum, etc...",
	"Mouse, Cat" * 30 + "~<s:reset_all]",
	"use markov",
]

def dtime(function):
	now = time.time()
	function()
	return time.time()-now

# CU: CUrrent BetterUI printing mechanism
# OL: OLd BetterUI printing mechanism
def main():
	cuspeeds = []
	olspeeds = []
	stdout = swap_out()
	total = pow(10,6)
	for i in range(total):
		randline = random.choice(string_data)
		cuspeeds.append(dtime(lambda: cupprint(randline)))
		olspeeds.append(dtime(lambda: olpprint(randline)))
		print("{0:2.4f}".format(i/total * 100), end = "\r", flush=True)

	traceback = swap_in(stdout)
	tolspeeds = []
	for index, olsp in enumerate(olspeeds):
		tolspeeds.append(olsp/cuspeeds[index])

	print("Current: {0}\nOld: {1}".format(mean(cuspeeds), mean(olspeeds)))
	print("Ration Old on Current: {0}".format(mean(tolspeeds)))

if __name__ == "__main__":
	main()
