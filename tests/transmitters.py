#!/usr/bin/python3
# -*- encoding: utf-8 -*-
#

from sys import argv
import random
import os.path
import hashlib
import time

import stolas.stolas
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

				print("Created model {0}...".format(n), end = "\r")
				ports.append(cport)
				cport += 1
				break

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

if __name__ == '__main__':
	if len(argv) == 1:
		pass

	if argv[1] == "cluster":
		stolas_cluster()

	elif argv[1] == "gigacluster":
		stolas_gigacluster()

	elif argv[1] == "simple":
		stolas_simple()
