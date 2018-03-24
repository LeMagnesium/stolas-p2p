import json, random, time, os, os.path, socket

class MarkovGenerator:
	def __init__(self):
		self.indices = {}
		self.file = "htmlgen.json"
		self.__load(self.file)
		self.init_index = "_beg"
		self.end_index = "_end"

	def __load(self, filepath):
		try:
			self.indices = json.load(open(filepath))
		except FileNotFoundError:
			pass

	def feed(self, text):
		antechar = self.init_index
		for char in text:
			# Create index if needed
			self.indices[antechar] = self.indices.get(antechar, {'total': 0})
			self.indices[antechar][char] = self.indices[antechar].get(char, 0)

			self.indices[antechar]["total"] += 1
			self.indices[antechar][char] += 1

			antechar = char

		self.indices[antechar]["total"] += 1
		self.indices[antechar][self.end_index] = self.indices[antechar].get(self.end_index, 0) + 1

	def puke(self, minsize = -1):
		antechar = self.init_index
		if self.indices.get(self.init_index) == None:
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

			if chosen_char == self.end_index:
				if minsize == -1 or minsize <= 0:
					break
				else:
					chosen_char = self.init_index
					continue
			else:
				yield chosen_char
				minsize -= len(chosen_char)
				antechar = chosen_char

	def save(self):
		json.dump(self.indices, open(self.file, "w"))

class AdvancedMarkovGenerator(MarkovGenerator):
	def __init__(self):
		self.indices = {}
		self.file = "ahtmlgen.json"
		self.__load(self.file)
		self.init_index = ">_beg"
		self.end_index = "<_end"

	def __load(self, filepath):
		try:
			self.indices = json.load(open(filepath))
		except FileNotFoundError:
			pass

	def feed(self, text):
		antechar = self.init_index
		for word in self.splittext(text):
			# Create index if needed
			self.indices[antechar] = self.indices.get(antechar, {'total': 0})
			self.indices[antechar][word] = self.indices[antechar].get(word, 0)

			self.indices[antechar]["total"] += 1
			self.indices[antechar][word] += 1

			antechar = word

		self.indices[antechar] = self.indices.get(antechar, {"total": 0})
		self.indices[antechar]["total"] += 1
		self.indices[antechar][self.end_index] = self.indices[antechar].get(self.end_index, 0) + 1

	def splittext(self, text):
		seekbeg = True
		delimiters = [' ', '\n', '\t', '=', '<', '>']
		ipos = pos = 0
		antechar = ''
		while pos < len(text):
			curchar = text[pos]
			if antechar == '':
				antechar = curchar

			if curchar in delimiters:
				#some here
				if not antechar in delimiters:
					yield text[ipos:pos]
					ipos = pos
					antechar = curchar
					pos += 1
					yield curchar

				else:
					antechar = curchar
					pos += 1
					ipos = pos
					yield antechar

			elif antechar in delimiters:
				# We've begun a word
				ipos = pos
				antechar = text[pos]
				pos += 1

			else:
				pos += 1

		if ipos < len(text)-1:
			yield text[ipos:]


def filefindergenerator(root):
	curtop = root
	for top, dirs, files in os.walk(curtop):
		for fl in files:
			if os.path.splitext(fl)[-1] == ".html" or os.name == "nt" and os.path.splitext(fl)[-1] == ".htm":
				yield top + os.path.sep + fl

from html.parser import HTMLParser
class URLGrabber(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.scraps = []

	def handle_starttag(self, tag, attrs):
		if tag != "a":
			return
		for attr in attrs:
			if attr[0] == "href":
				self.scraps.append(attr[1])

	handle_stardendtag = handle_starttag

	def return_scraps(self):
		return self.scraps

	def clean_scraps(self):
		self.scraps.clear()

import http.client
import urllib.robotparser, urllib.parse, urllib.error
import queue
HISTORY_MAX = 2**20
class AutomatedNetworkTeacher:
	#lessons = queue.Queue(maxsize=HISTORY_MAX)
	lessons = []
	robotp = urllib.robotparser.RobotFileParser()
	user_agent = "Stolas Markov Generator"
	gatherer = URLGrabber()
	#recent_history = []

	def __init__(self, student):
		self.student = student

	def download(self, url):
		pres = urllib.parse.urlsplit(url)
		host = pres.netloc
		port = None
		if host.find(":") != -1:
			host, port = pres.netloc.split(":")

		if pres.scheme == "https":
			downloader = http.client.HTTPSConnection(host, port = port)
		else:
			downloader = http.client.HTTPConnection(host, port = port)

		downloader.request("GET", pres.path)
		response = downloader.getresponse()

		if response.status == 200:
			return True, response.read()
		elif response.status == 301 or response.status == 302:
			success, data = self.download(response.getheader("Location"))
			if success:
				return True, data
			else:
				return False, data
		else:
			return False, response

	def check_allowed(self, url):
		pres = urllib.parse.urlsplit(url)
		#data = self.download("{}://{}/robots.txt".format(pres.scheme, pres.netloc))
		self.robotp.set_url("{}://{}/robots.txt".format(pres.scheme, pres.netloc))
		try:
			self.robotp.read()
		except (urllib.error.URLError,ConnectionResetError,socket.gaierror):
			return False

		return self.robotp.can_fetch("*", url)

	def loop(self):
		while len(self.lessons) > 0:
			url = random.choice(self.lessons)
			self.lessons = self.lessons[1:]
			if not self.check_allowed(url):
				print("Not allowed to fetch {}".format(url))
				print("Left: {}".format(len(self.lessons)))
				#self.lessons.task_done()
				continue

			try:
				success, data = self.download(url)
				assert(success)
				data = data.decode("utf8")
			except (AssertionError,ConnectionResetError,UnicodeDecodeError,socket.gaierror) as err:
				print("Didn't succeed: {}".format(url))
				#self.lessons.task_done()
				continue

			self.student.feed(data)

			print("Fed {} \u2713".format(url))

			# Get the scraps
			self.gatherer.feed(data)
			scraps = [self.correctify(url, x) for x in self.gatherer.return_scraps()]
			self.gatherer.clean_scraps()
			# Filter out from recent_history
			#scraps = [scrap for scrap in scraps if not scrap in self.recent_history]
			# Filter out from unauthorized URLS
			#scraps = [scrap for scrap in scraps if self.check_allowed(scrap)]

			random.shuffle(scraps)
			for scrap in scraps:
				self.lessons.append(scrap)

			#while len(self.recent_history) > HISTORY_MAX:
			#	self.recent_history = self.recent_history[1:]

			#self.lessons.task_done()

	def correctify(self, url, scrap):
		return urllib.parse.urljoin(url, scrap)

	def start(self, urls):
		self.lessons = urls
		try:
			self.loop()
		except KeyboardInterrupt:
			print("Done \u2713")
		self.student.save()

def show_help():
	from stolas.betterui import pprint as print
	from sys import argv

	helps = [
		"The following help shows you the available commands for markovgenerator.py :",
		" - ~<s:bright]{} feed [directory]~<s:reset_all] : Scans the provided directory for files\n\tending in '.html' to train on.",
		" - ~<s:bright]{} puke [outputfile]~<s:reset_all] : Generates random text and writes it\n\tinto the provided file (overwritting). Requires training.",
		" - ~<s:bright]{} automatic : Learn from crawling on the internet.",
		" - ~<s:bright]{} help~<s:reset_all] : The very thing you are reading right now.\n"
	]
	for hp in helps:
		print(hp.format(argv[0]))

def main():
	import sys
	if len(sys.argv) < 2:
		show_help()
		return

	if sys.argv[1] == "feed" and len(sys.argv) > 2:
		mkvg = MarkovGenerator()
		if len(sys.argv) > 3 and sys.argv[3] == "--advanced":
			mkvg = AdvancedMarkovGenerator()
		now = time.time()
		for filepath in filefindergenerator(sys.argv[2]):
			try:
				mkvg.feed(open(filepath).read())
			except UnicodeDecodeError:
				continue
			except FileNotFoundError:
				continue
			except PermissionError:
				continue
			print("Fed {0} to the MKvG".format(filepath))
			if time.time() - now >= 60:
				mkvg.save()
				now = time.time()
		mkvg.save()

	elif sys.argv[1] == "puke" and len(sys.argv) > 2:
		mkvg = MarkovGenerator()
		if len(sys.argv) > 3 and sys.argv[3] == "--advanced":
			print("Loading Advanced Options")
			mkvg = AdvancedMarkovGenerator()
		outp = open(sys.argv[2], "wb")
		for char in mkvg.puke():
			outp.write(char.encode("utf8"))

		outp.close()

	elif sys.argv[1] == "automatic":
		if len(sys.argv) > 2 and sys.argv[2] == "--advanced":
			mkvg = AdvancedMarkovGenerator()
		else:
			mkvg = MarkovGenerator()

		teacher = AutomatedNetworkTeacher(mkvg)
		starters = [
			"https://docs.python.org",		"https://atom.io/",
			"https://wikipedia.org/",		"https://doc.qt.io/",
			"https://stackoverflow.com/",	"https://www.parcoursup.fr",
			"https://freedesktop.org",		"https://godotengine.org/",
			"http://www.cplusplus.com/",	"https://www.reddit.com/"
		]
		teacher.start(starters)

	elif sys.argv[1] == "help":
		show_help()

if __name__ == "__main__":
	main()
