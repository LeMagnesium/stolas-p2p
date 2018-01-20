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
			except OSError:
				cport += 1
				continue
			else:
				if len(ports) > 0:
					rport = random.choice(ports)
					pid = stols.networker.peer_add(("127.0.0.1", rport))

				print("Created model {0}...".format(n+1), end = "\r")
				break

		cport += 1
		ports.append(cport)
		objects.append(stols)

	return objects

def create_ctrlfile():
	controlfile = "{0}_cluster.ctrl".format(hashlib.sha1(str(time.time()+random.randrange(-10000, 10000)).encode("utf8")).hexdigest()[:8])
	print("Creating control file : {0}".format(controlfile))
	open(controlfile, "w")
	print("~<s:bright]Remove the control file at any time to collapse the cluster.~<s:reset_all]")
	return controlfile

def network_collapse(cluster):
	i = 1
	for obj in cluster:
		obj.stop()
		obj.join()
		print("Terminating model {0}...".format(i), end = "\r")
		i += 1
	print("\nAll models terminated")

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

def transmission_test():
	print("~<s:bright]Starting Message Transmission Test~<s:reset_all]")
	controlfile = create_ctrlfile()

	sender = stolas.stolas.Stolas(logdown=True)
	receiver = stolas.stolas.Stolas()
	print("\t=> Ends created ~<s:bright]~<f:green]\u2713~<s:reset_all]")

	sender.start()
	receiver.start()
	print("\t=> Ends started ~<s:bright]~<f:green]\u2713~<s:reset_all]")

	cluster = network_random(sender.port, random.randrange(10,12))
	print("\n\t=> Done creating the cluster ~<s:bright]~<f:green]\u2713~<s:reset_all]")
	sender.networker.peer_add(("localhost", random.choice(cluster).port))
	receiver.networker.peer_add(("localhost", random.choice(cluster).port))
	print("\t=> Connected the Receiver and Sender")

	ttlt = 180

	msgobj = stolas.protocol.Message(ttl = ttlt, channel = "")
	msgobj.set_payload(b"Moo")
	print("Sending out: {0}".format(msgobj))
	sender.message_broadcast(msgobj)

	sint = len(sender.networker.peers)
	cint = average([len(x.networker.peers) for x in cluster if x.is_alive()])
	rint = len(receiver.networker.peers)

	j = 1
	i = 1
	while os.path.isfile(controlfile):
		if len(receiver.mpile) > 0:
			break
		print("[{0}|{1:.2f}|{2}] Waiting{3}{4}".format(sint, cint, rint, '.' * i, ' ' * (5-i)), end = "\r")
		time.sleep(0.5)

		sint = len(sender.networker.peers)
		cint = average([len(x.networker.peers) for x in cluster if x.is_alive()])
		rint = len(receiver.networker.peers)

		j += 1
		i = (j%5)
		if j%ttlt == 0:
			print("~<s:bright]~<f:red]Failed sending the message \u2717~<s:reset_all]")
			break

	if j%ttlt != 0 and os.path.isfile(controlfile):
		print(" " * 10, end = "\r")
		print("\t=> Message Received ~<f:green]~<s:bright]\u2713~<s:reset_all]       ")
	else:
		print("\t=> Leaving anyways ~<s:bright]~<f:red]\u2717~<s:reset_all]")
	network_collapse(cluster)

	sender.stop()
	sender.join()

	receiver.stop()
	receiver.join()

	if os.path.isfile(controlfile):
		os.remove(controlfile)
	print("Done")

def stolas_caching():
	from stolas.diskcachemanager import GlobalDiskCacheManager as gdcm

	cache = gdcm.create_access()
	print(cache)

	cache.write(b"moo")
	cache.seek(-3, 1)
	print(cache.read())

if __name__ == '__main__':
	if len(argv) == 1:
		print("Tell me?")
		pass

	if argv[1] == "cache":
		stolas_caching()

	elif argv[1] == "cluster":
		stolas_cluster()

	elif argv[1] == "gigacluster":
		stolas_gigacluster()

	elif argv[1] == "simple":
		stolas_simple()

	elif argv[1] == "transmission":
		transmission_test()

	else:
		print("¯\_(ツ)_/¯")
