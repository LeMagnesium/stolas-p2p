#!/usr/bin/python3

import time
import os
import threading
import random
import socket

from stolas.betterui import pprint as print

from stolas.stolas import Stolas
from stolas.unisocket import UnisocketModel

def run_stolas():
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

def build_network(stolobj, total = None):
	models = []
	port = stolobj.port
	total = total or random.randrange(5, 20)
	for progress in range(total):
		while True:
			n = UnisocketModel(port, str(port)) # Should fail the first time
			try:
				n.start()
			except OSError:
				n.stop() # FFS just let any ghost thread die, in case
				port += 1
				continue
			else:
				#n.peer_add(("127.0.0.1", stolobj.port))
				n.peer_add(("127.0.0.1", port-1))
				break
		print("Connected peer {0}/{1}".format(progress+1, total), end = "\r")
		port += 1

		models.append(n)
	print()

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
		obj.stop()
		obj.join()
		print("Model {0} terminated".format(i), end = "\r")
		i += 1
	print()

def test_network_integration_and_collapsing():
	portfile, logfile = prepare_logging_locations()

	threading.current_thread().setName("Main__")
	eh = Stolas()
	eh.start()
	open(portfile, "w").write(str(eh.port))
	open(logfile, "w")

	print("Started on port {0}".format(eh.port))

	models = build_network(eh, random.randrange(10, 20))

	print("Readying...")
	#tr = threading.Timer(random.randrange(1, 10), lambda: __send_shutdown(eh))
	#tr.start()
	print("Ready!")
	# We shall wait for all peers to be integrated
	i = 0
	while eh.running and False in [m.integrated for m in models + [eh.networker]]:
		print("Awaiting integration" + (i * ".") + (5-i) * " ", end = "\r")
		time.sleep(1)
		i = (i+1)%6

	print("Network has fully integrated ~<s:bright]~<f:green]\u2713~<s:reset_all]")
	eh.stop()
	eh.join()
	print("Now killing all models")
	collapse_network(models)
	print("Stopped")
	assert(threading.active_count() == 1)
	os.remove(portfile)

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
		if csplit[0] == "connect":
			pid = eh.networker.peer_add((csplit[1], int(csplit[2])))
			if type(pid) != type(0) and pid == False:
				continue
			else:
				print("Added peer {0} => PID {1}".format(csplit[1:3], pid))

		elif csplit[0] == "broadcast" and len(csplit) > 1:
			eh.message_broadcast(" ".join(csplit[1:]).encode("utf8"))

		elif csplit[0] == "haddaway":
			eh.networker.peerlock.acquire()
			for peer in eh.networker.peers:
				eh.networker.peer_send(peer, eh.networker.death_sequence)
			eh.networker.peerlock.release()
			time.sleep(1)

		elif csplit[0] == "peers":
			eh.networker.peerlock.acquire()
			for peer in eh.networker.peers:
				print("~<s:bright]{0}~<s:reset_all] => ~<f:{1}]{2}~<s:reset_all]".format(
					peer,
					random.choice(["red", "green", "cyan", "yellow", "magenta", "blue"]),
					eh.networker.peers[peer].listen or eh.networker.peers[peer].verbinfo
				))
			eh.networker.peerlock.release()

		elif csplit[0] == "fpeers":
			eh.networker.peerlock.acquire()
			for peer in [eh.networker.peers[peer] for peer in eh.networker.peers if eh.networker.peers[peer].listen != None]:
				print("~<s:bright]{0}~<s:reset_all] => ~<s:bright]{1}~<s:reset_all]".format(peer.pid, peer.listen))
			eh.networker.peerlock.release()


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

	models = build_network(eh, random.randrange(15, 30))

	print("Ready ~<f:green]~<s:bright]\u2713~<f:reset]~<s:reset_all]")
	eh.start()

	manual_stolas_prompt(eh)

	eh.stop()
	eh.join()

	print("Collapsing Network...")
	collapse_network(models)
	print("Network collapsed \u2713")
	assert(threading.active_count() == 1)
	os.remove(portfile)

def create_ponderation(ran):
	d = []
	for e in range(ran)[::-1]:
		d += [e+1] * (ran-e)
	return d


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

	else:
		print("~<s:bright]Launching Manual Control System~<s:reset_all]")
		test_manual_network_manipulation()
