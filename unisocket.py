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

# Some constants
# Network Protocol Constants
HELLO_BYTE = 1
GOODBYE_BYTE = 2
SHAREPEER_BYTE = 3
REQUESTPEER_BYTE = 4
MESSAGE_BYTE = 5
MESSAGEACK_BYTE = 6
MALFORMED_DATA = 7
DEATH_SEQUENCE = b"\x57\x68\x61\x74\x20\x69\x73\x20\x6c\x6f\x76\x65\x3f\x20\x42\x61\x62\x79\x20\x64\x6f\x6e\x27\x74\x20\x68\x75\x72\x74\x20\x6d\x65\x2c\x20\x64\x6f\x6e\x27\x74\x20\x68\x75\x72\x74\x20\x6d\x65\x2c\x20\x6e\x6f\x20\x6d\x6f\x72\x65"

# Some conversion things
def i2b(n):
	"""Integer to Bytes"""
	if n == 0:
		return b"\0"
	b = b""
	while n > 0:
		neon = n & 255
		b += chr(neon).encode("utf8")
		n = n >> 8
	return b

def b2i(b):
	"""Bytes to Integers"""
	n = 0
	for bt in b:
		n += bt
		n = n << 8
	return n >> 8

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

# Model of UniSocket P2P client
# Should be tweaked/inherited to be modified
class UnisocketModel:
	"""Unisocket Model for the P2P instance of our project."""
	def __init__(self, port, name = None):
		"""Initialization requires a port and, optionally, a name"""
		self.port = port
		self.running = False
		self.peers = {}
		self.possible_peers = []
		self.name = name

		self.__logging_setup()

		self.death_sequence = DEATH_SEQUENCE

		self.iqueue = queue.Queue()
		self.oqueue = queue.Queue()

		self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.processor = threading.Thread(
			target = self.__processor_unit,
			name = "Processor" + self.__nametag()
		)


	def __nametag(self):
		"""Return the nametag for our object, appended to the Thread Name Roots"""
		return "::{0}".format(self.name) if self.name != None else ""

	def __logging_setup(self):
		"""Internal. Setup logging and logging handlers."""
		# Create a console handler
		self.logger = logging.Logger("UniSocket" + self.__nametag())
		console = logging.StreamHandler()
		console.setLevel(logging.INFO)
		c_formatter = logging.Formatter('%(message)s') # Keep it simple
		console.setFormatter(c_formatter)
		self.logger.addHandler(console)

		# Create the file handler.
		# FIXME: On os.platform() == __windows__, don't use /tmp
		file_lo = logging.handlers.RotatingFileHandler(filename = "/tmp/unisocket_logs")
		file_lo.setLevel(logging.DEBUG)
		f_formatter = logging.Formatter('[%(asctime)s][%(levelname)7s][%(name)20s:%(funcName)25s:%(lineno)3s][%(threadName)10s] %(message)s')
		file_lo.setFormatter(f_formatter)
		self.logger.addHandler(file_lo)

		self.logger.debug("Logger Ready")

	def start(self):
		"""Start the Unisocket Networker. This is where threads are created."""
		self.running = True
		self.__start_listen() # There might be errors here, so we don't start anything
		self.processor.start()

	def __peer_both_ways(self, sock, pid):
		"""Internal. Runs the network exchange logic between a Peer and our UniSocket Model."""
		# We want a non blocking socket to be able to alternative without stopping between I and O
		sock.settimeout(0)
		self.logger.debug("Started peer {0}".format(pid))
		peer = self.peers[pid] # Peer object access is faster
		while peer.running:
			# If output must be sent, then so be it
			if len(peer.oqueue) > 0:
				sock.send(peer.oqueue)
				self.logger.debug("[{0}] << {1}".format(pid, peer.oqueue))
				peer.oqueue = b""

			# No iqueue means we're being deleted; no need to recv, or parse
			if peer.iqueue == None:
				continue

			# Create the Differed Delta Frame, fancy word for "Data that's new"
			ddf = b""
			try:
				ddf += sock.recv(1024)
			except BlockingIOError:
				pass

			# No news is good news
			if ddf == b"":
				continue

			peer.iqueue += ddf
			self.logger.debug("[{0}] >> {1}".format(pid, ddf))

			self.parse_packets(pid)

		sock.close()
		# Only the UniSocket Peer Thread of a specific Peer can eventually erase itself
		# That ensures we never run into a situation where a semi-ghost peer thread runs
		del self.peers[pid]
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
				if len(data) < 8:
					break
				if data[1] == 6: #IPV6
					if len(data) < 6:
						break
					self.iqueue.put((data[:6], peerid))
					data = data[6:]
				elif data[1] == 4: # IPV4
					self.iqueue.put((data[:8], peerid))
					data = data[8:]

			elif data[0] == MESSAGE_BYTE:
				if len(data) < 3:
					break

				payload_len = b2i(data[1:3])
				if len(data) < 3 + payload_len:
					break

				self.iqueue.put((data[:3+payload_len], peerid))
				data = data[3 + payload_len:]

			elif data[0] == MALFORMED_DATA:
				self.iqueue.put((data[0:1], peerid))
				data = data[1:]

			elif data[0:56] == self.death_sequence:
				self.logger.warning("Found the Death Sequence")
				self.iqueue.put((self.death_sequence, peerid))
				data = b""

			else:
				peer.oqueue += i2b(MALFORMED_DATA) + i2b(len(data))
				data = b"" # FIXME: Remember to send "MALFORMED_DATA" packet

		peer.iqueue = data # Actualize the data from our modified snapshot

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
			self.peers[npid].thread.start()
		self.logger.debug("Stopped")

	def peer_add(self, verbinfo, sock = None):
		"""Add a peer, either from an info tuple, or an info tuple and a socket.
		If the socket is None, then this means initiating a connection, creating sock,
		connecting it, and eventually creating and storing the informations of the peer."""
		# New PeerID
		npid = 0
		while self.peer_get(npid):
			npid += 1

		# Initiating the connection
		if sock == None:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			try:
				sock.connect(verbinfo)
			except Exception as e:
				self.logger.warning("Will not add new Peer : couldn't connect ({0})".format(type(e)))
				return False

		# New Peer Attached to their Thread
		trd = threading.Thread(
			target = self.__peer_both_ways,
			args = (sock, npid),
			name = "Peer::{0}".format(npid)
		)

		self.peers[npid] = Peer(npid, trd)
		return npid

	def peer_del(self, pid):
		"""Initiate the deletion of a peer. In the end, most of the data remains until the thread ends."""
		peer = self.peer_get(pid)
		if not peer:
			return

		peer.iqueue = None # Drop all data
		peer.running = False # Stop the peer's thread


	def peer_get(self, npid):
		return self.peers.get(npid, None)

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

	def __processor_unit(self):
		"""Internal. Processing unit. Must be modified for the handling of packets according to the protocol though."""
		while self.is_alive():
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
				af_inet = data[1]
				port = b2i(data[-2:])

				if af_inet == 4:
					ip = "{0}.{1}.{2}.{3}".format(data[2], data[3], data[4], data[5])
				elif af_inet == 6:
					ip = "{0}:{1}:{2}:{3}:{4}:{5}".format(data[2], data[3], data[4], data[5], data[6], data[7])
				if not (ip, port) in self.possible_peers:
					self.possible_peers.append((ip, port))

			elif data[0] == MESSAGE_BYTE: # Message Arrival Byte
				payload_len = b2i(data[1:3])
				msg = data[3:3+payload_len].decode("utf8")
				self.logger.info("Received '{0}' from {1}".format(msg, pid))
				self.peer_get(pid).oqueue += i2b(MESSAGEACK_BYTE) + i2b(payload_len)

			elif data[0:56] == self.death_sequence: # Death Sequence
				self.stop()

			self.iqueue.task_done()

		# Summoning the peers for deletion. We may not want to wait for them to
		# end but at the same time we can't safely parse the list, since it may
		# change size during execution. We'll just remember what peers we shut down.
		# Other thing that sucks : indices may not be linear, and iterating over keys just sucks.
		dunzo = []
		while len(self.peers) - len(dunzo) > 0:
			neox = [x for x in self.peers.keys() if not x in dunzo][0]
			self.peer_get(neox).oqueue += i2b(GOODBYE_BYTE)
			self.peer_del(neox)
			dunzo.append(neox)
		self.logger.debug("Stopped")
