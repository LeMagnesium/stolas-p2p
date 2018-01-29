#!/usr/bin/python3
# -*- encoding: utf8 -*-

import time
import os, os.path
import threading
import random
import socket

from stolas.betterui import pprint as print

from stolas.stolas import Stolas
from stolas.unisocket import UnisocketModel
from stolas.protocol import Message

def run_stolas():
	port = None
	if len(sys.argv) >= 3:
		port = int(sys.argv[2])
		eh = Stolas(port = port)
	else:
		eh = Stolas()
	eh.start()
	print(eh.port)
	manual_stolas_prompt(eh)
	eh.stop()
	eh.join()


def __send_shutdown(obj):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect(('127.0.0.1', obj.port))
	s.send(obj.networker.death_sequence + b"\x02")
	s.close()
	print("Network is about to collapse...")

def __trigger_connection(n, host):
	import time
	time.sleep(1)
	try:
		n.peer_add(host)
	except:
		pass

def build_network(start_port, total = None):
	models = []
	ports = [start_port]
	port = start_port
	total = total or random.randrange(5, 10)
	for progress in range(total):
		while True:
			n = UnisocketModel(port, name = str(port-start_port)) # Should fail the first time
			try:
				n.start()
			except OSError:
				n.stop() # FFS just let any ghost thread die, in case
				port += 1
				continue
			else:
				if port > start_port:
					tr = threading.Thread(target = __trigger_connection, args = (n, ("127.0.0.1", random.choice(ports))))
					tr.start()
				ports.append(port)
				break
		print("Connected peer {0}/{1}  ".format(progress+1, total), end = "\r")
		port += 1

		models.append(n)
	print("")

	return models

def prepare_logging_locations():
	logfile, portfile = "/tmp/unisocket_logs", "/tmp/unisocket_port"
	if os.name == "nt":
		# Windows
		logfile, portfile = "unisocket_logs", "unisocket_port"
	elif os.name == "java":
		# I have no fucken' idea. Android?
		print("I don't know that system")
		assert(False)

	return portfile, logfile

def collapse_network(models):
	i = 1
	for obj in models:
		print("Sending termination to model {0}".format(i), end = "\r")
		obj.stop()
		print("Joining model {0} ({1})...".format(i, type(obj)), end = "\r")
		obj.join()
		print("Model {0} terminated".format(i), end = "\r")
		i += 1
	print()

def test_network_integration_and_collapsing():
	import time
	portfile, logfile = prepare_logging_locations()

	threading.current_thread().setName("Main__")
	port = random.randrange(1024, 65500)
	open(portfile, "w").write(str(port))
	open(logfile, "w")

	print("Started on port {0}".format(port))

	models = build_network(port, random.randrange(10, 20))

	print("Readying...")
	print("Ready! ~<f:green]~<s:bright]\u2713~<s:reset_all]")
	now = time.time()
	print("Now is : {0}".format(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(now))))
	maxtime = now + len(models) * 5 # Maximum time allowed
	# We shall wait for all peers to be integrated
	i = 0
	while False in [m.integrated for m in models]:
		print("Awaiting integration" + (i * ".") + (5-i) * " ", end = "\r")
		time.sleep(1)
		i = (i+1)%6

	total_time = time.time() - now
	print("Network has fully integrated ~<s:bright]~<f:green]\u2713~<s:reset_all]")
	print("It took : {0:.2f}s ({1}s per peer)".format(total_time, total_time/len(models)))
	worked_out_fine = total_time <= maxtime - now
	if not worked_out_fine:
		print("~<s:bright]~<f:red]Network took too long. \u2717~<s:reset_all]")
	print("Now killing all models")
	collapse_network(models)
	print("Stopped")
	assert(threading.active_count() == 1)
	os.remove(portfile)

	return worked_out_fine # We're a test unit

def manual_stolas_prompt(eh):
	while eh.running and eh.networker.running:
		try:
			print("~<s:bright]", end = "")
			command = input("[-]> ")
			print("~<s:reset_all]", end = "")
		except Exception as err:
			print("<~s:bright]<~f:red]" + str(err) + "<~s:reset_all]")
			eh.running = False
			continue

		if command == "shutdown":
			eh.running = False

		csplit = command.split(" ")
		if csplit[0] == "connect" and len(csplit) == 3 and csplit[2].isdecimal():
			csplit[1] = socket.gethostbyname(csplit[1])
			pid = eh.networker.peer_add((csplit[1], int(csplit[2])))
			if type(pid) != type(0) and pid == False:
				print("En error occured...")
				continue
			else:
				print("Added peer {0} => PID {1}".format(csplit[1:3], pid))

		elif csplit[0] == 'ppeers':
			print(eh.networker.possible_peers)

		elif csplit[0] == "broadcast" and len(csplit) > 1:
			msgobj = Message()
			msgobj.set_payload(" ".join(csplit[1:]).encode("utf8"))
			msgobj.set_timestamp(time.time())
			msgobj.set_ttl(70)
			msgobj.set_channel("")

			eh.message_broadcast(msgobj)

		elif csplit[0] == "haddaway":
			eh.networker.peerlock.acquire()
			for peer in eh.networker.peers:
				eh.networker.raw_peer_send(peer, eh.networker.death_sequence)
			eh.networker.peerlock.release()
			time.sleep(1)

		elif csplit[0] == "peers":
			eh.networker.peerlock.acquire()
			colors = ["red", "yellow", "green", "cyan", "blue", "magenta"]
			col = random.randrange(0,len(colors))
			for peer in sorted(list(eh.networker.peers.keys())):
				print("~<s:bright]{0}~<s:reset_all] => ~<f:{1}]{2}~<s:reset_all]".format(
					peer,
					colors[col],
					eh.networker.peers[peer].listen or eh.networker.peers[peer].verbinfo
				))
				col = (col+1)%len(colors)
			eh.networker.peerlock.release()

		elif csplit[0] == "fpeers":
			eh.networker.peerlock.acquire()
			for peer in [eh.networker.peers[peer] for peer in eh.networker.peers if eh.networker.peers[peer].listen != None]:
				print("~<s:bright]{0}~<s:reset_all] => ~<s:bright]{1}~<s:reset_all]".format(peer.pid, peer.listen))
			eh.networker.peerlock.release()

		elif csplit[0] == "port":
			print("Port is : {0}".format(eh.port))

		elif csplit[0] == "messages":
			print("Inbox:")
			msgs = eh.mpile.list()
			for mid in sorted(msgs):
				msg = msgs[mid]
				print("[{0}] {1}".format(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(msg.timestamp)), msg.get_payload()))


	print("Prompt terminated")
	print("<[~]" + "-" * 40 + "[~]>")


def test_manual_network_manipulation():
	portfile, logfile = prepare_logging_locations()

	threading.current_thread().setName("Main__")
	eh = Stolas()
	open(portfile, "w").write(str(eh.port))
	open(logfile, "w")

	print("Started on port {0}".format(eh.port))
	print("Building network...")

	models = build_network(eh.port, random.randrange(15, 20))

	print("Ready ~<f:green]~<s:bright]\u2713~<f:reset]~<s:reset_all]")
	eh.start()

	manual_stolas_prompt(eh)

	eh.stop()
	eh.join()

	print("Collapsing Network...")
	collapse_network(models)
	print("Network collapsed ~<s:bright]~<f:green]\u2713~<s:reset_all]")
	assert(threading.active_count() == 1)
	if os.path.isfile(portfile):
		os.remove(portfile)

def create_ponderation(ran):
	d = []
	for e in range(ran)[::-1]:
		d += [e+1] * (ran-e)
	return d

import hashlib
def run_cluster():
	threading.current_thread().setName("Main__")
	port = random.randrange(1024, 65400)

	print("Main Stolas object started")

	controlfile = "{0}_cluster.ctrl".format(hashlib.sha1(str(time.time()+random.randrange(-10000, 10000)).encode("utf8")).hexdigest()[:8])

	print("Creating control file : {0}".format(controlfile))
	open(controlfile, "w")
	print("~<s:bright]Remove the control file at any time to collapse the cluster.~<s:reset_all]")
	print("Creating network cluster from port {0}...".format(port))
	models = build_network(port, random.randrange(5, 20))
	print("Running ~<f:green]~<s:bright]\u2713~<s:reset_all]")

	mm = [m for m in models if m.is_alive()]
	while len(mm) > 0 and os.path.isfile(controlfile):
		print("Current count: {0} (0port: {1})".format(len(mm), min([m.port for m in mm])), end = "  \r")
		mm = [m for m in mm if m.is_alive()]

	if os.path.isfile(controlfile):
		os.remove(controlfile)

	print("\n~<f:blue]~<s:bright]Cluster Collapsing~<s:reset_all]")
	collapse_network(models)
	assert(threading.active_count() == 1)

def average_cluster_integration():
	threading.current_thread().setName("Main__")
	port = random.randrange(1024, 65400)

	controlfile = "{0}_cluster.ctrl".format(hashlib.sha1(str(time.time()+random.randrange(-10000, 10000)).encode("utf8")).hexdigest()[:8])

	print("Creating control file : {0}".format(controlfile))
	open(controlfile, "w")

	print("Creating network cluster from port {0}...".format(port))
	models = build_network(port, random.randrange(10, 20))
	print("Running ~<f:green]~<s:bright]\u2713~<s:reset_all]")

	mm = [m for m in models if m.is_alive()]
	while len(mm) > 0 and os.path.isfile(controlfile):
		print("Avg. integration is : {0:.2f} (0port: {1}) ".format(sum([len(m.peers) for m in mm]) / len(mm), min([m.port for m in mm])), end = " \r")
		mm = [m for m in mm if m.is_alive()]
		time.sleep(1)

	print()
	print("~<f:blue]~<s:bright]Cluster Collapsing~<s:reset_all]")
	collapse_network(models)
	assert(threading.active_count() == 1)

if __name__ == "__main__":
	import sys
	if len(sys.argv) > 1:
		if sys.argv[1] == "integration":
			print("~<s:bright]Launching Network Integration and Collapsing Model~<s:reset_all]")
			for e in range(random.choice(create_ponderation(10))):
				print("TEST NUMBER {0}".format(e+1))
				test_network_integration_and_collapsing()
				print("<(~)" + "-" * 50 + "(~)>")

		elif sys.argv[1] == "simple":
			run_stolas()

		elif sys.argv[1] == "cluster":
			print("~<s:bright][ Lauching Cluster of Unisocket Models")
			print("[" + "-" * 50 + "]~<s:reset_all]")
			run_cluster()

		elif sys.argv[1] == "average":
			average_cluster_integration()

	else:
		print("~<s:bright]Launching Manual Control System~<s:reset_all]")
		test_manual_network_manipulation()
