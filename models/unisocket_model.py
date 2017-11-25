#!/usr/bin/python3
import threading
import socket
import queue
import random
import logging, logging.handlers

def i2b(n):
	b = b""
	while n > 0:
		neon = n & 255
		b += chr(neon).encode("utf8")
		n = n >> 8
	return b

def b2i(b):
	n = 0
	for bt in b:
		n += bt
		n = n << 8
	return n >> 8

class Peer:
	def __init__(self, pid, thread, verbinfo = None):
		self.pid = pid
		self.thread = thread
		self.oqueue = b""
		self.iqueue = b""
		self.version = -1
		self.running = True
		self.verbinfo = verbinfo

# Model of UniSocket P2P client
# Should be tweaked/inherited to be modified
class UnisocketModel:
	"""Unisocket Model for the P2P instance of our project."""
	def __init__(self, port):
		self.port = port
		self.running = False
		self.peers = {}

		self.__logging_setup()

		self.death_sequence = DEATH_SEQUENCE

		self.iqueue = queue.Queue()
		self.oqueue = queue.Queue()

		self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.processor = threading.Thread(target = self.__processor_unit, name = "Processor")

	def __logging_setup(self):
		self.logger = logging.Logger("UniSocket")
		console = logging.StreamHandler()
		console.setLevel(logging.INFO)
		c_formatter = logging.Formatter('%(message)s')
		console.setFormatter(c_formatter)
		self.logger.addHandler(console)

		file_lo = logging.handlers.RotatingFileHandler(filename = "/tmp/unisocket_logs")
		file_lo.setLevel(logging.DEBUG)
		f_formatter = logging.Formatter('[%(asctime)s][%(levelname)7s][%(name)s:%(funcName)25s:%(lineno)3s][%(threadName)10s] %(message)s')
		file_lo.setFormatter(f_formatter)
		self.logger.addHandler(file_lo)
		self.logger.debug("Logger Ready")

	def start(self):
		self.running = True
		self.processor.start()
		self.__start_listen()

	def __peer_both_ways(self, sock, pid):
		sock.settimeout(0)
		self.logger.debug("Started peer {0}".format(pid))
		peer = self.peers[pid]
		while peer.running:
			# Pour ne pas bloquer le Thread : On a réglé le socket pour ne pas avoir de timeout.
			# Le socket est alors "non bloquant", mais il enverra une exception lors de la majorité de ses appels
			if len(peer.oqueue) > 0:
				sock.send(peer.oqueue)
				self.logger.debug("[{0}] << {1}".format(pid, peer.oqueue))
				peer.oqueue = b""

			if peer.iqueue == None:
				continue

			ddf = b""
			try:
				ddf += sock.recv(1024)
			except BlockingIOError:
				pass

			if ddf == b"":
				continue

			peer.iqueue += ddf
			self.logger.debug("[{0}] >> {1}".format(pid, ddf))

			self.parse_packets(pid)

		sock.close()
		self.logger.debug("Stopped")
		del self.peers[pid]

	def parse_packets(self, peerid):
		peer = self.peer_get(peerid)
		data = peer.iqueue
		while data and len(data) > 0:
			# HANDLE DATA SLICING HERE

			data = b""

		peer.iqueue = data # Actualize the data

	def __listener_thread(self):
		"""Thread principal d'écoute. Il est en charge de l'accueil des nouveaux pairs."""
		self.listen_socket.bind(("", self.port))
		self.listen_socket.listen(10)
		self.listen_socket.settimeout(0)
		self.logger.debug("Listener Ready")
		while self.running:
			# Encore un socket non bloquant
			try:
				psock, pinfo = self.listen_socket.accept()
			except BlockingIOError:
				continue

			npid = self.peer_add(pinfo, psock)
			self.peers[npid].thread.start()
		self.logger.debug("Stopped")

	def peer_add(self, verbinfo, sock = None):
		# New PeerID
		npid = 0
		while self.peer_get(npid):
			npid += 1

		if sock == None:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			try:
				sock.connect(verbinfo)
			except Exception as e:
				self.logger.warning("Will not add new Peer : couldn't connect ({0})".format(type(e)))
				return False

		# New Peer Attached to their Thread
		trd = threading.Thread(target = self.__peer_both_ways, args = (sock, npid), name = "Peer::{0}".format(npid))

		self.peers[npid] = Peer(npid, trd)
		return npid

	def peer_del(self, pid):
		peer = self.peer_get(pid)
		if not peer:
			return

		peer.iqueue = None # Drop all data
		peer.running = False # Stop the peer


	def peer_get(self, npid):
		return self.peers.get(npid, None)

	def __start_listen(self):
		self.listener = threading.Thread(target = self.__listener_thread, name = "Listener")
		self.listener.start()

	def stop(self):
		self.running = False
		self.logger.warning("Initiated Killing Process")

	def join(self):
		# Attendre que tous les threads aient fini
		self.logger.debug("Entered the join process")
		if self.listener.is_alive():
			self.listener.join()
		if self.processor.is_alive():
			self.processor.join()
		self.logger.debug("Left the join process")

	def is_alive(self):
		return self.running

	def __processor_unit(self):
		while self.running:
			try:
				data, pid = self.iqueue.get(timeout=0)
			except queue.Empty:
				continue

			# HANDLE DATA PROCESSING HERE

			self.iqueue.task_done()

		dunzo = []
		while len(self.peers) - len(dunzo) > 0:
			neox = [x for x in self.peers.keys() if not x in dunzo][0]
			self.peer_get(neox).oqueue += i2b(GOODBYE_BYTE)
			self.peer_del(neox)
			dunzo.append(neox)
		self.logger.debug("Stopped")
