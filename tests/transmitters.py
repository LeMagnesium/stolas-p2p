#!/usr/bin/python3
# -*- encoding: utf-8 -*-
#

from sys import argv
import random
import os.path
import hashlib
import time

import stolas.stolas
import stolas.protocol
from stolas.betterui import pprint as print

from network import manual_stolas_prompt
from common import network_collapse

def network_random(port, quantity = None):
	ports = []
	cport = port
	objects = []
	if quantity == None:
		quantity = random.randrange(5,7)

	for n in range(quantity):
		while True:
			try:
				stols = stolas.stolas.Stolas(port = cport)
				stols.start()
				if len(ports) > 0:
					rport = random.choice(ports)
					pid = stols.networker.peer_add(("127.0.0.1", rport))

				print("Created model {0}/{1}...".format(n+1, quantity), end = "\r")
				ports.append(cport)
				cport += 1
				objects.append(stols)
				break

			except OSError:
				cport += 1
				continue

	# Assert that every single object is connected to another one
	assert(len([x for x in objects if len(x.networker.peers) == 0]) == 0)
	return objects

def create_ctrlfile():
	controlfile = "{0}_cluster.ctrl".format(hashlib.sha1(str(time.time()+random.randrange(-10000, 10000)).encode("utf8")).hexdigest()[:8])
	print("Creating control file : {0}".format(controlfile))
	open(controlfile, "w")
	print("~<s:bright]Remove the control file at any time to collapse the cluster.~<s:reset_all]")
	return controlfile

def stolas_cluster():
	rport = random.randrange(1024, 65400)
	controlfile = create_ctrlfile()
	print("Starting from port ~<s:bright]~<f:red]{0}~<s:reset_all]".format(rport))
	cluster = network_random(rport)
	print("~<s:bright]Network is ready! ~<f:green]\u2713~<s:reset_all]")

	mm = [x.port for x in cluster if x.is_alive()]
	while len(mm) > 0 and os.path.isfile(controlfile):
		print("AvgInt: {0:.2f}; FiPort: {1}".format(sum([len(m.networker.peers) for m in cluster if m.is_alive()])/len(mm), mm[0]), end = "  	\r")
		time.sleep(1)
		mm = [x.port for x in cluster if x.is_alive()]
		#print([m for m in cluster if m.is_alive()][0].networker.peers)

	if os.path.isfile(controlfile):
		os.remove(controlfile)
	print("\n~<s:bright]~<f:blue]Cluster collapsing~<s:reset_all]")
	network_collapse(cluster)
	print("Done")

def stolas_gigacluster():
	rport = random.randrange(1024, 65400)
	controlfile = create_ctrlfile()
	print("Starting from port ~<s:bright]~<f:red]{0}~<s:reset_all]".format(rport))
	cluster = network_random(rport, random.randrange(15,20))
	print("~<s:bright]Network is ready! ~<f:green]\u2713~<s:reset_all]")

	mm = [x.port for x in cluster if x.is_alive()]
	while len(mm) > 0 and os.path.isfile(controlfile):
		print("AvgInt: {0:.2f}; FiPort: {1}".format(sum([len(m.networker.peers) for m in cluster if m.is_alive()])/len(mm), mm[0]), end = "  	\r")
		time.sleep(1)
		mm = [x.port for x in cluster if x.is_alive()]
		#print([m for m in cluster if m.is_alive()][0].networker.peers)

	if os.path.isfile(controlfile):
		os.remove(controlfile)
	print("\n~<s:bright]~<f:blue]Cluster collapsing~<s:reset_all]")
	network_collapse(cluster)
	print("Done")

def stolas_simple():
	slobj = stolas.stolas.Stolas(logdown = True)
	slobj.start()
	print("Port is {0}".format(slobj.port))
	manual_stolas_prompt(slobj)
	slobj.stop()
	slobj.join()
	print("Done")

def average(lst):
	return sum(lst)/len(lst)

def generate_random_payload():
	return os.urandom(random.randrange(10, 65000))

def cluster_average_integration(cluster):
        return average([len(x.networker.peers) for x in cluster if x.is_alive()])

def test_transmission():
	print("~<s:bright]Starting Message Transmission Test~<s:reset_all]")
	controlfile = create_ctrlfile()

	sender = stolas.stolas.Stolas()
	receiver = stolas.stolas.Stolas()
	print("\t=> Ends created ~<sf:bright,green]\u2713~<s:reset_all]")

	sender.start()
	receiver.start()
	print("\t=> Ends started ~<sf:bright,green]\u2713~<s:reset_all]")

	cluster = network_random(sender.port+1, random.randrange(10,12))
	print("\n\t=> Done creating the cluster ~<sf:bright,green]\u2713~<s:reset_all]")
	sender.networker.peer_add(("localhost", random.choice(cluster).port))
	receiver.networker.peer_add(("localhost", random.choice(cluster).port))
	print("\t=> Connected the Receiver and Sender")

	i, sint, cint, mint, rint = 0, 0, 0, 0, 0
	while not sender.networker.integrated or not receiver.networker.integrated or len([x for x in cluster if x.networker.integrated]) < len(cluster):
		print("[{0}|{1:.2f}|{2}] Integrating{3}{4}".format(
			sint, mint, rint,
			'.' * i,
			' ' * (5-i)
		), end = "\r")
		sint = len(sender.networker.peers)
		mint = min([len(x.networker.peers) for x in cluster + [sender] if x.is_alive()])
		rint = len(receiver.networker.peers)
		i = (i+1)%6
		time.sleep(0.5)

	print("=> Integrated ~<s:bright]~<f:green]\u2713~<s:reset_all]" + 17 * ' ')
	assert(receiver.networker.integrated)
	assert(sender.networker.integrated)
	assert(len([True for x in cluster if x.networker.integrated]) == len(cluster))

	ttlt = 120

	globalpayload = generate_random_payload()
	msgobj = stolas.protocol.Message(ttl = ttlt, channel = "")
	msgobj.set_payload(globalpayload)
	print("Sending out: {0}".format(msgobj))
	sender.message_broadcast(msgobj)

	then = time.time()
	i = 1
	worked_out_fine = False
	while True:
		if len(receiver.mpile) > 0:
			print(" " * 10, end = "\r")
			print("\t=> Message Received ~<f:green]~<s:bright]\u2713~<s:reset_all]       ")
			worked_out_fine = True
			break
		print("[{0}|{1:.2f}|{2}>{3}] Waiting{4}{5}".format(
			sint, cint, rint, len([x for x in cluster + [receiver] if len(x.mpile) > 0]),
			'.' * i,
			' ' * (5-i)
		), end = "\r")
		time.sleep(0.5)

		sint = len(sender.networker.peers)
		cint = average([len(x.networker.peers) for x in cluster + [sender] if x.is_alive()])
		rint = len(receiver.networker.peers)

		i = (i+1)%5
		if time.time() - then >= ttlt or not os.path.isfile(controlfile):
			print("~<s:bright]~<f:red]Failed sending the message \u2717~<s:reset_all]")
			print("\t=> Leaving anyways ~<s:bright]~<f:red]\u2717~<s:reset_all]")
			break

	network_collapse(cluster)

	sender.stop()
	sender.join()

	receiver.stop()
	receiver.join()

	if os.path.isfile(controlfile):
		os.remove(controlfile)
	print("Done")
	return worked_out_fine # We're a unit test

if __name__ == '__main__':
	if len(argv) == 1:
		print("Tell me?")
		pass

	if argv[1] == "cluster":
		stolas_cluster()

	elif argv[1] == "gigacluster":
		stolas_gigacluster()

	elif argv[1] == "simple":
		stolas_simple()

	elif argv[1] == "transmission":
		test_transmission()

	else:
		print("¯\_(ツ)_/¯")
