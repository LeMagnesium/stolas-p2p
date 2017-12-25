#!/usr/bin/python3
#
# Unisocket Model for P2P networking
#	Project Stolas, ßý Lymkwi
#

# Modules
import threading	# `threading.Thread`
import socket		# `socket.socket`
import queue		# `queue.Queue`, `queue.Empty`
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

	def __repr__(self):
		return "Peer(pid={0}, verbinfo={1}, version={2})".format(self.pid, self.verbinfo, self.version)

class PhantomLogger:
	def debug(msg, *args, **kwargs):
		pass

	def warning(msg, *args, **kwargs):
		pass

	def info(msg, *args, **kwargs):
		pass


# Model of UniSocket P2P manager
class UnisocketModel:
	"""Unisocket Model for the P2P instance of our project."""
	def __init__(self, port, **kwargs):
		"""Initialization requires a port and, optionally, a name and the listen option"""
		# Configuration
		self.port = port
		self.listen = kwargs.get("listen", True)
		if self.listen:
			self.listen_addr = "127.0.0.1" # Will change later
		self.name = kwargs.get("name", None)
		if self.name == None:
			self.name = hex(random.randrange(7800000,78000000))[2:10]
		self.max_clients = 50
		self.death_sequence = DEATH_SEQUENCE

		# Dynamic status fields
		self.integrated = False
		self.running = False
		self.now = time.time()
		self.timers = {
			"integration": 0
		}

		# Data Storage Structures
		self.peers = {}
		self.possible_peers = []

		# Communication Structures
		self.listen_socket = None
		if self.listen:
			self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.iqueue = queue.Queue()
		self.oqueue = queue.Queue()
		self.imessages = queue.Queue()
		self.omessages = queue.Queue()

		# Control Structures
		self.peerlock = threading.Lock()

		# The logger
		self.logger = kwargs.get("logger", PhantomLogger())
		# Since logging has been moved upwards to the Stolas object, we can
		# only log stuff if we're passed the logging object it has created.
		# Thus, and as to not break the possibility of seeing the emitting
		# line and file from the verbose logs, we created a PhantomLogger
		# class meant to implement hollow versions of the logging methods we
		# used so far.

		self.processor = threading.Thread(
			target = self.__processor_unit,
			name = "Processor" + self.__nametag()
		)

	def __del__(self):
		self.logger.debug("UniSocket model deleted")

	def __nametag(self):
		"""Return the nametag for our object, appended to the Thread Name Roots"""
		return "::{0}".format(self.name) if self.name != None else ""

	def start(self):
		"""Start the Unisocket Networker. This is where threads are created."""
		self.running = True
		if self.listen:
			self.__start_listen() # There might be errors here, so we don't start anything
		self.processor.start()

	def __is_already_peer(self, verbinfo):
		return (self.listen and verbinfo == (self.listen_addr, self.port)) or verbinfo in (self.peers[peer].listen for peer in self.peers if self.peers[peer].listen != None)

	def __is_already_known(self, verbinfo):
		return self.__is_already_peer(verbinfo) or verbinfo in self.possible_peers

	def __peer_both_ways(self, sock, pid):
		"""Internal. Runs the network exchange logic between a Peer and our UniSocket Model."""
		# We want a non blocking socket to be able to alternative without stopping between I and O
		sock.settimeout(0)
		self.logger.debug("Started peer {0}".format(pid))
		peer = self.peers[pid] # Peer object access is faster
		while peer.running or peer.oqueue != b"":
			self.peer_lock(pid)
			# If output must be sent, then so be it
			if len(peer.oqueue) > 0:
				try:
					sock.send(peer.oqueue)
				except BrokenPipeError:
					self.logger.warning("BROKEN Pipe! Connection with peer {0} broken".format(pid))
					self.peer_unlock(pid)
					break
				except ConnectionResetError:
					self.logger.warning("Connection Reset with Peer {0}".format(pid))
					self.peer_unlock(pid)
					break

				self.logger.debug("[{0}] << {1}".format(pid, peer.oqueue))
				peer.oqueue = b""
			elif not peer.running:
				self.peer_unlock(pid)
				break

			# No iqueue means we're being deleted; no need to recv, or parse
			if peer.iqueue == None:
				self.peer_unlock(pid)
				continue

			# Create the Differed Delta Frame, fancy word for "Data that's new"
			ddf = b""
			try:
				ddf += sock.recv(1024)
			except BlockingIOError:
				pass
			except ConnectionResetError:
				self.logger.warning("Connection Reset with Peer {0}".format(pid))
				self.peer_unlock(pid)
				break
			except ConnectionAbortedError:
				self.logger.warning("Connection Aborted with Peer {0}".format(pid))
				self.peer_unlock(pid)
				break

			# No news is good news
			if ddf == b"":
				self.peer_unlock(pid)
				continue

			peer.iqueue += ddf
			self.logger.debug("[{0}] >> {1}".format(pid, ddf))

			self.parse_packets(pid)
			self.peer_unlock(pid)

		sock.close()
		# Only the UniSocket Peer Thread of a specific Peer can eventually erase itself
		# That ensures we never run into a situation where a semi-ghost peer thread runs
		self.peerlock.acquire()
		self.peer_lock(pid)
		del self.peers[pid]
		peer.datalock.release() # The peer isn't registered any more
		self.peerlock.release()
		self.logger.debug("Stopped peer {0}".format(pid))

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
			except OSError:
				continue # Happens with ERRno24 : too many files open


			npid = self.peer_add(pinfo, psock)
		try:
			self.listen_socket.shutdown(socket.SHUT_RDWR)
		except OSError:
			pass # Happens on Windows when the socket tried to send data
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

			try:
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				sock.connect(verbinfo)
			except Exception as e:
				self.logger.warning("Will not add new Peer : couldn't connect to {0} ({1})".format(verbinfo, type(e)))
				self.peerlock.release()
				return False
			except OSError:
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
		self.peers[npid].thread.start()
		if advertise and self.listen:
			self.peers[npid].listen = verbinfo
			self.peer_send(npid, i2b(ADVERTISE_BYTE) + b"\0" + i2b(self.port, 2))
		self.peerlock.release()

		return npid

	def peer_del(self, pid):
		"""Initiate the deletion of a peer. In the end, most of the data remains until the thread ends."""
		peer = self.peer_get(pid)
		if not peer:
			return

		self.peer_lock(pid)
		peer.iqueue = None # Drop all data
		peer.running = False # Stop the peer's thread
		peer.oqueue += i2b(GOODBYE_BYTE)
		self.peer_unlock(pid)

	def peer_get(self, npid):
		return self.peers.get(npid, None)

	def peer_lock(self, npid):
		peer = self.peer_get(npid)
		if not peer:
			return False
		peer.datalock.acquire()

	def peer_unlock(self, npid):
		peer = self.peer_get(npid)
		if not peer:
			return False
		peer.datalock.release()

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
		self.logger.debug("Initiated Killing Process")

	def is_alive(self):
		return self.running

	def join(self):
		# Waiting individually for each category of threads
		self.logger.debug("Entered the join process")
		# Stop the source of new connections
		if self.listen and self.listener.is_alive():
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

	def integrate(self):
		# Detect a lack of network integration and ask for peers
		self.peerlock.acquire()
		pln = self.peer_count()
		if pln > 0 and self.is_alive():
			if pln < MIN_INTEGRATION:
				if self.integrated:
					self.integrated = False
					self.logger.info("I lost integration!")
					self.timers["integration"] = random.randrange(2, 5)

				if len(self.possible_peers) != 0:
					npeer = random.choice(self.possible_peers)
					self.peerlock.release()
					pid = self.peer_add(npeer)
					self.peerlock.acquire()
					self.possible_peers.remove(npeer)

				elif self.timers["integration"] <= 0:
					rpid = random.choice(list(self.peers.keys()))
					self.peer_get(rpid).oqueue += i2b(REQUESTPEER_BYTE)

					self.timers["integration"] = random.randrange(2, 5)

			elif pln >= MIN_INTEGRATION and pln < self.max_clients:
				if not self.integrated:
					self.logger.info("I became integrated!")
					self.integrated = True

				if self.timers["integration"] <= 0:
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

					dd = 100 # seconds
					mx = self.max_clients # clients
					# Parabolic integration timer
					self.timers["integration"] = (lambda x: (dd/(mx**2)) * (x**2))(pln) # x->(dd/mx^2)*x^2
					#self.timers["integration"] = (lambda x: -(dd/ ((MIN_INTEGRATION - self.max_clients) ** 2)) * (x - self.max_clients) ** 2 + dd)(pln)

		self.peerlock.release()

	def __processor_unit(self):
		"""Internal. Processing unit. Must be modified for the handling of packets according to the protocol though."""
		self.now = time.time()
		while self.is_alive():
			then = time.time() - self.now
			self.now = time.time()
			for timer in self.timers:
				self.timers[timer] -= then

			self.integrate()

			try:
				data, pid = self.iqueue.get(timeout=0)
			except queue.Empty:
				continue

			#FIXME: Reorganize and make some tasks unresponsive during shutdown

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
					#self.peer_send(pid, i2b(SHAREPEER_BYTE) + b"\0" * 3)
					# For now do not respond
					continue

				rpid = random.choice(possibles)
				peer = self.peer_get(rpid)
				self.peerlock.release()
				if peer and rpid != pid and peer.iqueue != None:
					self.peer_lock(rpid)
					verbinfo = peer.listen
					addr_len = i2b(len(verbinfo[0]))

					port = i2b(verbinfo[1], 2)
					self.peer_send(pid, i2b(SHAREPEER_BYTE) + addr_len + verbinfo[0].encode("utf8") + port)
					self.peer_unlock(rpid)
				else:
					self.logger.info("Refused to send {0}".format(rpid))
					#self.peer_send(pid, i2b(SHAREPEER_BYTE) + b"\0" * 3) See 517

			elif data[0] == MESSAGE_BYTE: # Message Arrival Byte
				payload_len = b2i(data[1:3])
				msg = data[3:3+payload_len]
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
				self.peer_lock(pid)
				peer = self.peer_get(pid)
				if peer == None:
					# There was never any peer locking anyways,
					# If it returns None now, the peer was deleted before our locking
					continue

				listen = (ip if ip != "" else peer.verbinfo[0], port)

				if self.__is_already_peer(listen):
					self.logger.info("Dropping peer {0}, they were already connected to us".format(pid, listen))
					self.peer_unlock(pid)
					self.peer_del(pid)
					continue
				peer.listen = listen

				self.logger.info("Peer {0}'s listen is revealed to be {1}".format(pid, listen))
				self.peer_unlock(pid)

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
