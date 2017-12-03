#!/usr/bin/python3
#
# Unisocket Model for P2P networking
#	Project Stolas, ßý Lymkwi
#

# Modules
import threading	# `threading.Thread`
import socket		# `socket.socket`
import queue		# `queue.Queue`, `queue.Empty`
import logging		# `logging.Logger`, `logging.Formatter`, `logging.StreamHandler`
import logging.handlers	# `logging.handlers.RotatingFileHandler`
import os			# `os.name`
import random		# `random.randrange`, `random.choice`
import time

from .protocol import *
from .utils import b2i, i2b


class Peer:
	"""Representation of the data surrounding a Network Peer"""
	def __init__(self, pid, thread, verbinfo = None):
		"""Initialization requires a Peer ID, a thread object, and, optionally, verbose information (an addr tuple)."""
		self.pid = pid
		self.thread = thread
		self.oqueue = b""
		self.iqueue = b""
		self.version = -1
		self.running = True
		self.verbinfo = verbinfo
		self.listen = None
		self.datalock = threading.Lock()

# Model of UniSocket P2P client
# Should be tweaked/inherited to be modified
class UnisocketModel:
	"""Unisocket Model for the P2P instance of our project."""
	def __init__(self, port, name = None):
		"""Initialization requires a port and, optionally, a name"""
		self.port = port
		self.listen_addr = "127.0.0.1" # Will change later
		self.running = False
		self.peers = {}
		self.possible_peers = []
		self.name = name
		self.integrated = False

		self.peerlock = threading.Lock()
		self.now = time.time()

		self.__logging_setup()

		self.death_sequence = DEATH_SEQUENCE

		self.iqueue = queue.Queue()
		self.oqueue = queue.Queue()

		self.imessages = queue.Queue()

		self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.processor = threading.Thread(
			target = self.__processor_unit,
			name = "Processor" + self.__nametag()
		)

		self.timers = {
			"integration": 0
		}

	def __nametag(self):
		"""Return the nametag for our object, appended to the Thread Name Roots"""
		return "::{0}".format(self.name) if self.name != None else ""

	def __logging_setup(self):
		"""Internal. Setup logging and logging handlers."""
		# Create a console handler
		self.logger = logging.Logger("UniSocket" + self.__nametag())
		console = logging.StreamHandler()
		console.setLevel(logging.WARNING)
		c_formatter = logging.Formatter('%(message)s') # Keep it simple
		console.setFormatter(c_formatter)
		self.logger.addHandler(console)

		# Create the file handler.
		logfile = "unisocket_logs"
		if os.name == "posix":
			logfile = "/tmp/unisocket_logs"
		file_lo = logging.handlers.RotatingFileHandler(filename = logfile)
		file_lo.setLevel(logging.DEBUG)
		f_formatter = logging.Formatter('[%(asctime)s][%(levelname)7s][%(name)20s:%(funcName)25s:%(lineno)3s][%(threadName)20s] %(message)s')
		file_lo.setFormatter(f_formatter)
		self.logger.addHandler(file_lo)

		self.logger.debug("Logger Ready")

	def start(self):
		"""Start the Unisocket Networker. This is where threads are created."""
		self.running = True
		self.__start_listen() # There might be errors here, so we don't start anything
		self.processor.start()

	def __is_already_peer(self, verbinfo):
		return verbinfo == (self.listen_addr, self.port) or verbinfo in (self.peers[peer].listen for peer in self.peers if self.peers[peer].listen != None)

	def __is_already_known(self, verbinfo):
		return self.__is_already_peer(verbinfo) or verbinfo in self.possible_peers

	def __peer_both_ways(self, sock, pid):
		"""Internal. Runs the network exchange logic between a Peer and our UniSocket Model."""
		# We want a non blocking socket to be able to alternative without stopping between I and O
		sock.settimeout(0)
		self.logger.debug("Started peer {0}".format(pid))
		peer = self.peers[pid] # Peer object access is faster
		while peer.running or peer.oqueue != b"":
			peer.datalock.acquire()
			# If output must be sent, then so be it
			if len(peer.oqueue) > 0:
				try:
					sock.send(peer.oqueue)
				except BrokenPipeError:
					self.logger.warning("BROKEN Pipe! Connection with peer {0} broken".format(pid))
					peer.datalock.release()
					break
				except ConnectionResetError:
					self.logger.warning("Connection Reset with Peer {0}".format(pid))
					peer.datalock.release()
					break

				self.logger.debug("[{0}] << {1}".format(pid, peer.oqueue))
				peer.oqueue = b""
			elif not peer.running:
				peer.datalock.release()
				break

			# No iqueue means we're being deleted; no need to recv, or parse
			if peer.iqueue == None:
				peer.datalock.release()
				continue

			# Create the Differed Delta Frame, fancy word for "Data that's new"
			ddf = b""
			try:
				ddf += sock.recv(1024)
			except BlockingIOError:
				pass
			except ConnectionResetError:
				self.logger.warning("Connection Reset with Peer {0}".format(pid))
				peer.datalock.release()
				break

			# No news is good news
			if ddf == b"":
				peer.datalock.release()
				continue

			peer.iqueue += ddf
			self.logger.debug("[{0}] >> {1}".format(pid, ddf))

			self.parse_packets(pid)
			peer.datalock.release()

		sock.close()
		# Only the UniSocket Peer Thread of a specific Peer can eventually erase itself
		# That ensures we never run into a situation where a semi-ghost peer thread runs
		self.peerlock.acquire()
		del self.peers[pid]
		self.peerlock.release()
		self.logger.debug("Stopped")

	def parse_packets(self, peerid):
		"""Parse the peer's input buffer and slice the packets when complete so
		that they're processed later. Requires the peer's Peer ID."""
		peer = self.peer_get(peerid)
		# IMPORTANT: We get a snapshot of the input buffer, not a reference to it. It saves time.
		data = peer.iqueue
		while data and len(data) > 0:
			# Just refer to the protocol
			if data[0] == HELLO_BYTE:
				if len(data) < 2:
					break
				self.iqueue.put((data[0:2], peerid))
				data = data[2:]

			elif data[0] == GOODBYE_BYTE:
				self.iqueue.put((data[:1], peerid))
				data = data[1:]

			elif data[0] == SHAREPEER_BYTE: # Share Peer
				if len(data) < 2:
					break

				addr_len = data[1]
				if len(data) < 4 + addr_len:
					break

				if addr_len > 2: # No address would be so short
					self.iqueue.put((data[:4+addr_len], peerid))
				data = data[4+addr_len:]

			elif data[0] == REQUESTPEER_BYTE: # Request Byte
				self.iqueue.put((b"\x04", peerid))
				data = data[1:]

			elif data[0] == MESSAGE_BYTE:
				if len(data) < 3:
					break

				payload_len = b2i(data[1:3])
				if len(data) < 3 + payload_len:
					break

				self.iqueue.put((data[:3+payload_len], peerid))
				data = data[3 + payload_len:]

			elif data[0] == MESSAGEACK_BYTE:
				if len(data) < 3:
					break
				self.iqueue.put((data[:3], peerid))
				data = data[3:]

			elif data[0] == MALFORMED_DATA:
				if len(data) < 3:
					break
				self.iqueue.put((data[:3], peerid))
				data = data[3:]

			elif data[0] == ADVERTISE_BYTE:
				if len(data) < 2:
					break

				addr_len = data[1]
				if len(data) < 4 + addr_len:
					break

				self.iqueue.put((data[:4+addr_len], peerid))
				data = data[4+addr_len:]

			elif data[0:56] == self.death_sequence:
				self.logger.info("Found the Death Sequence")
				self.iqueue.put((self.death_sequence, peerid))
				data = b""

			else:
				self.peer_send(peerid, i2b(MALFORMED_DATA) + i2b(len(data), 2))
				data = b""

		peer.iqueue = data # Refresh the data from our modified snapshot

	def __listener_thread(self):
		"""Listening thread. Responsible for the creation of all Peer Threads."""
		self.logger.debug("Listener Ready")
		while self.running:
			# Same 'non blocking' principle here, so that we can exit ASAP
			try:
				psock, pinfo = self.listen_socket.accept()
			except BlockingIOError:
				continue

			npid = self.peer_add(pinfo, psock)
		self.listen_socket.shutdown(socket.SHUT_RDWR)
		self.listen_socket.close()
		self.logger.debug("Stopped")

	def peer_add(self, verbinfo, sock = None):
		"""Add a peer, either from an info tuple, or an info tuple and a socket.
		If the socket is None, then this means initiating a connection, creating sock,
		connecting it, and eventually creating and storing the informations of the peer."""
		if not self.running:
			return False

		self.peerlock.acquire()
		# New PeerID
		npid = 0
		while self.peer_get(npid):
			npid += 1

		advertise = True

		# Initiating the connection
		if sock == None:
			if self.__is_already_peer(verbinfo):
				self.logger.warning("Will not add new Peer : already connected to {0}".format(verbinfo))
				self.peerlock.release()
				return False

			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			try:
				sock.connect(verbinfo)
			except Exception as e:
				self.logger.warning("Will not add new Peer : couldn't connect ({0})".format(type(e)))
				self.peerlock.release()
				return False
		else:
			# We gotta advertise
			advertise = False

		# New Peer Attached to their Thread
		trd = threading.Thread(
			target = self.__peer_both_ways,
			args = (sock, npid),
			name = "Peer::{0}".format(npid) + self.__nametag()
		)

		self.peers[npid] = Peer(npid, trd, verbinfo)
		self.peerlock.release()
		self.peers[npid].thread.start()
		if advertise:
			self.peer_send(npid, i2b(ADVERTISE_BYTE) + b"\0" + i2b(self.port, 2))
			self.peers[npid].listen = verbinfo

		return npid

	def peer_del(self, pid):
		"""Initiate the deletion of a peer. In the end, most of the data remains until the thread ends."""
		peer = self.peer_get(pid)
		if not peer:
			return

		peer.datalock.acquire()
		peer.iqueue = None # Drop all data
		peer.running = False # Stop the peer's thread
		peer.oqueue += i2b(GOODBYE_BYTE)
		peer.datalock.release()

	def peer_get(self, npid):
		return self.peers.get(npid, None)

	def peer_count(self):
		ln = len(self.peers.keys())
		return ln

	def __start_listen(self):
		"""Internal. Creates and starts the listen thread after initializing the listen socket and setting some of its properties."""
		# We initialize the socket here so that any error in binding/listening can be caught from in the main thread
		self.listen_socket.bind(("", self.port))
		self.listen_socket.listen(10)
		self.listen_socket.settimeout(0)

		self.listener = threading.Thread(
			target = self.__listener_thread,
			name = "Listener" + self.__nametag()
		)
		self.listener.start()

	def stop(self):
		self.running = False
		self.logger.debug("Initiated Killing Process : ")

	def is_alive(self):
		return self.running

	def join(self):
		# Waiting individually for each category of threads
		self.logger.debug("Entered the join process")
		# Stop the source of new connections
		if self.listener.is_alive():
			self.listener.join()
		# Stop the processing of all data
		# FIXME: Maybe finish processing currently queued packets if possible?
		if self.processor.is_alive():
			self.processor.join()
		# All peers are summoned for deletion by the PU, so we wait last for them
		while len(self.peers) > 0:
			pass
		self.logger.debug("Left the join process")

	def peer_send(self, pid, data):
		peer = self.peer_get(pid)
		if peer == None:
			return False

		peer.oqueue += data
		return len(data)

	def __processor_unit(self):
		"""Internal. Processing unit. Must be modified for the handling of packets according to the protocol though."""
		self.now = time.time()
		while self.is_alive():
			then = time.time() - self.now
			self.now = time.time()
			for timer in self.timers:
				self.timers[timer] -= then

			# Detect a lack of network integration and ask for peers
			self.peerlock.acquire()
			pln = self.peer_count()
			if pln > 0 and pln < 3 and self.timers["integration"] <= 0 :
				if self.integrated:
					self.integrated = False
					self.logger.info("I lost integration!")

				if len(self.possible_peers) == 0:
					rpid = random.choice(list(self.peers.keys()))
					self.peer_get(rpid).oqueue += i2b(REQUESTPEER_BYTE)

				else:
					npeer = random.choice(self.possible_peers)
					self.peerlock.release()
					pid = self.peer_add(npeer)
					self.peerlock.acquire()

					if type(pid) == type(0):
						self.possible_peers.remove(npeer)

				self.timers["integration"] = random.randrange(10, 20)
				# FIXME: Later : differenciate urgent integration from convenient integration

			elif not self.integrated and pln >= 3:
				self.logger.info("I became integrated!")
				self.integrated = True

			self.peerlock.release()


			try:
				data, pid = self.iqueue.get(timeout=0)
			except queue.Empty:
				continue

			if data[0] == HELLO_BYTE: # Hello Byte
				self.peer_get(pid).version = data[1]
				self.logger.debug("Peer {0} is running version {1}".format(pid, data[1]))

			elif data[0] == GOODBYE_BYTE: # Peer Disconnect Byte
				self.peer_del(pid)

			elif data[0] == SHAREPEER_BYTE: # Peer share byte
				addr_len = data[1]
				port = b2i(data[-2:])

				ip = data[2:2+addr_len].decode("utf8")
				if not self.__is_already_known((ip, port)):
					self.possible_peers.append((ip, port))

			elif data[0] == REQUESTPEER_BYTE:
				# We were requested a peer, so...
				peer = None
				if len(self.peers) == 0 or not self.is_alive():
					# We don't participate in the network if we're gonna shut down
					continue

				self.peerlock.acquire()
				possibles = [peer for peer in self.peers if self.peers[peer].listen != None]
				if possibles == []:
					self.peerlock.release()
					self.peer_send(pid, i2b(SHAREPEER_BYTE) + b"\0" * 3)
					continue

				rpid = random.choice(possibles)
				peer = self.peer_get(rpid)
				self.peerlock.release()
				if peer and rpid != pid and peer.iqueue != None:
					peer.datalock.acquire()
					verbinfo = peer.listen
					addr_len = i2b(len(verbinfo[0]))

					port = i2b(verbinfo[1], 2)
					self.peer_send(pid, i2b(SHAREPEER_BYTE) + addr_len + verbinfo[0].encode("utf8") + port)
					peer.datalock.release()
				else:
					self.logger.info("Refused to send {0}".format(rpid))
					self.peer_send(pid, i2b(SHAREPEER_BYTE) + b"\0" * 3)

			elif data[0] == MESSAGE_BYTE: # Message Arrival Byte
				payload_len = b2i(data[1:3])
				msg = data[3:3+payload_len].decode("utf8")
				self.logger.info("Received '{0}' from {1}".format(msg, pid))
				self.imessages.put(("message", msg))
				self.peer_send(pid, i2b(MESSAGEACK_BYTE) + i2b(payload_len, 2))

			elif data[0] == MESSAGEACK_BYTE: # Message acknowledgement
				self.imessages.put(("ack", b2i(data[1:])))

			elif data[0] == MALFORMED_DATA: # Malformed data alert
				self.imessages.put(("malformed", b2i(data[1:])))

			elif data[0] == ADVERTISE_BYTE: # Advertising byte
				addr_len = data[1]
				port = b2i(data[-2:])

				ip = data[2:2+addr_len].decode("utf8")
				peer = self.peer_get(pid)

				listen = (ip if ip != "" else peer.verbinfo[0], port)

				self.peer_get(pid).listen = listen
				#FIXME: Drop peer if we realize we already had them
				self.logger.info("Peer {0}'s listen is revealed to be {1}".format(pid, listen))

			elif data[0:56] == self.death_sequence: # Death Sequence
				self.stop()

			self.iqueue.task_done()

		# Summoning the peers for deletion. We may not want to wait for them to
		# end but at the same time we can't safely parse the list, since it may
		# change size during execution. We'll just take all indices right now, since the listener stopped,
		# and, for each peer, initiate its deletion.
		self.peerlock.acquire()
		peers = list(self.peers.keys())
		for pid in peers:
			if self.peers.get(pid, None) == None:
				continue
			self.peer_del(pid)
		self.peerlock.release()
		self.logger.debug("Stopped")
