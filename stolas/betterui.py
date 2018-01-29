# ~ stolas/betterui.py: BetterUI ~
#
#  The BetterUI module for console-modifying code handling using colorama
#   and readline. This module is part of the Stolas project and acts,
#   for now, as a makup tool for Command Line Interfaces around
#   `stolas.Stolas` objects.
#

#	#	#
# The following table is a template to store style-altering codes for the
#  console. Until colorama is loaded, they remain empty (to symbolise the
#  removal of those symbols when colorama is absent)
# The codes are stored in the format of :
#
#    't': {"variant": code, ...}
#
#  where 't' is a type character (f for foreground, b for background, and s for
#  style), the "variant" chain is a specifier, and code is the real code put in
#  place of our betterui code, in the chain, before giving it to print.
# A betterui code in our (wrapped) prints must look like :
#
#    ~<t:variant] // Single console modifier
#    ~<t,t1,t2,...:col/style,col/style1,col/style2] // Multiple console modifiers
# IMPORTANT: Multiple code handling not yet implemented!!
#
pretty_printing = {
	"f": {"black": "", "red": "", "green": "", "yellow": "", "blue": "", "magenta": "", "cyan": "", "white": "", "reset": ""},
	"b": {"black": "", "red": "", "green": "", "yellow": "", "blue": "", "magenta": "", "cyan": "", "white": "", "reset": ""},
	"s": {"dim": "", "normal": "", "bright": "", "reset_all": ""}
}

#	#	#
# Readline lets us use a history file as well as the arrow and backspace keys
# It's quite interesting to have right now with our minimalistic CLI interface
# However, if readline's import were to fail (on Windows for example), we would
#  look for pyreadline instead. If that one fails as well we will simply
#  not have the aforementioned features.
#
try:
	import readline
except ImportError:
	try:
		import pyreadline as readline
	except ImportError:
		pass # Work with absolutely nothing

#	#	#
# Try and import colorama. If the import is successful, the pretty_printing
#  table must be filled in with the appropriate console altering codes for
#  future replacements. If not, the colorama namespace is mentioned and created
#  as a dummy object to let us know something went wrong.
#
try:
	import colorama
except ImportError:
	colorama = None
else:
	# Initialization must take place before anything else
	colorama.init()

	pretty_printing = {
		"f": {
			"black": colorama.Fore.BLACK,
			"red": colorama.Fore.RED,
			"green": colorama.Fore.GREEN,
			"yellow": colorama.Fore.YELLOW,
			"blue": colorama.Fore.BLUE,
			"magenta": colorama.Fore.MAGENTA,
			"cyan": colorama.Fore.CYAN,
			"white": colorama.Fore.WHITE,
			"reset": colorama.Fore.RESET
		},
		"b": {
			"black": colorama.Back.BLACK,
			"red": colorama.Back.RED,
			"green": colorama.Back.GREEN,
			"yellow": colorama.Back.YELLOW,
			"blue": colorama.Back.BLUE,
			"magenta": colorama.Back.MAGENTA,
			"cyan": colorama.Back.CYAN,
			"white": colorama.Back.WHITE,
			"reset": colorama.Back.RESET
		},
		"s": {
			"dim": colorama.Style.DIM,
			"normal": colorama.Style.NORMAL,
			"bright": colorama.Style.BRIGHT,
			"reset_all": colorama.Style.RESET_ALL
		}
	}

#	#	#
# We must know our system since windows's CMD is *somehow* still unable to
#  handle anything other than ASCII (and especially not multibyte characters).
#
from os import name as osname

# A wrapper around print where we do our business
def pprint(value = "", **kwargs):
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
