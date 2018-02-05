import json, random, time, os, os.path

class MarkovGenerator:
	def __init__(self):
		self.indices = {}
		self.file = "htmlgen.json"
		self.__load(self.file)

	def __load(self, filepath):
		try:
			self.indices = json.load(open(filepath))
		except FileNotFoundError:
			pass

	def feed(self, text):
		antechar = '_beg'
		for char in text:
			# Create index if needed
			self.indices[antechar] = self.indices.get(antechar, {'total': 0})
			self.indices[antechar][char] = self.indices[antechar].get(char, 0)

			self.indices[antechar]["total"] += 1
			self.indices[antechar][char] += 1

			antechar = char

		self.indices[antechar]["total"] += 1
		self.indices[antechar]["_end"] = self.indices[antechar].get("_end", 0) + 1

	def puke(self, minsize = -1):
		antechar = "_beg"
		if self.indices.get("_beg") == None:
			raise RuntimeError("No data loaded! Have you trained the MKvG on HTML files yet?")

		while True:
			total = self.indices[antechar]["total"]
			chrchoser = random.randrange(0,total)
			chosen_char = ''
			for possible_char in self.indices[antechar]:
				if possible_char == "total":
					continue

				chosen_char = possible_char
				chrchoser -= self.indices[antechar][possible_char]
				if chrchoser <= 0:
					break

			if chosen_char == '_end':
				if minsize == -1 or minsize <= 0:
					break
				else:
					chosen_char = "_beg"
					continue
			else:
				yield chosen_char
				minsize -= 1
				antechar = chosen_char

	def save(self):
		json.dump(self.indices, open(self.file, "w"))

def filefindergenerator(root):
	curtop = root
	for top, dirs, files in os.walk(curtop):
		for fl in files:
			if os.path.splitext(fl)[-1] == ".html" or os.name == "nt" and os.path.splitext(fl)[-1] == ".htm":
				yield top + os.path.sep + fl

def show_help():
	from stolas.betterui import pprint as print
	print("The following help shows you the available commands for markovgenerator.py :")
	print(" - ~<s:bright]markovgenerator.py feed [directory]~<s:reset_all] : Scans the provided directory for files\n\tending in '.html' to train on.")
	print(" - ~<s:bright]markovgenerator.py puke [outputfile]~<s:reset_all] : Generates random text and writes it\n\tinto the provided file (overwritting). Requires training.")
	print(" - ~<s:bright]markovgenerator.py help~<s:reset_all] : The very thing you are reading right now.\n")

def main():
	import sys
	if len(sys.argv) < 2:
		show_help()
		return

	if sys.argv[1] == "feed" and len(sys.argv) > 2:
		mkvg = MarkovGenerator()
		now = time.time()
		for filepath in filefindergenerator(sys.argv[2]):
			try:
				mkvg.feed(open(filepath).read())
			except UnicodeDecodeError:
				continue
			except FileNotFoundError:
				continue
			print("Fed {0} to the MKvG".format(filepath))
			if time.time() - now >= 60:
				mkvg.save()
				now = time.time()
		mkvg.save()

	elif sys.argv[1] == "puke" and len(sys.argv) > 2:
		mkvg = MarkovGenerator()
		outp = open(sys.argv[2], "wb")
		for char in mkvg.puke():
			outp.write(char.encode("utf8"))
			
		outp.close()

	elif sys.argv[1] == "help":
		show_help()

if __name__ == "__main__":
	main()
