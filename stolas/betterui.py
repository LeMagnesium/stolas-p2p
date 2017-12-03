# betterui.py
pretty_printing = {
	"f": {"black": "", "red": "", "green": "", "yellow": "", "blue": "", "magenta": "", "cyan": "", "white": "", "reset": ""},
	"b": {"black": "", "red": "", "green": "", "yellow": "", "blue": "", "magenta": "", "cyan": "", "white": "", "reset": ""},
	"s": {"dim": "", "normal": "", "bright": "", "reset_all": ""}
}

import readline
try:
	import colorama
except ImportError:
	colorama = None
else:
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

olprint = print

def pprint(st = "", **kwargs):
	#FIXME: I'm sure there is a cleaner way to do this
	st = str(st)
	if st.find("~<") != -1:
		for code in pretty_printing:
			for variant in pretty_printing[code]:
				st = st.replace("~<{0}:{1}]".format(code, variant), pretty_printing[code][variant])

	olprint(st, **kwargs)

#print = pprint
