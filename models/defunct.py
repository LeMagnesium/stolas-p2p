#!/usr/bin/python3

def death_timer(arg):
	from time import sleep
	ttt = 0
	while ttt < 3000 and arg.is_alive():
		ttt+=1
		time.sleep(1)
	arg.stop()

def old_sorter_garbage():
	while self.dataqueue != b"":

		# Packet Hello : Expecting 1 header byte and 1 version byte
		if self.dataqueue[0] == 1:
			if len(self.dataqueue) < 2:
				break
			packets.append(self.dataqueue[0:2])
			self.dataqueue = self.dataqueue[1:]


		# Packet Goodbye : Expecting 1 header byte
		elif self.dataqueue[0] == 2:
			if len(self.dataqueue) < 1:
				break
			packets.append(b"\x02")
			self.dataqueue = self.dataqueue[1:]


		elif self.dataqueue[0] == 3: # Share Peer
			if len(self.dataqueue) < 8:
				break
			if self.dataqueue[1] == 4: # IPv4
				packets.append(self.dataqueue[0:8])
				self.dataqueue = self.dataqueue[8:]
			elif self.dataqueue[1] == 6: # IPv6
				if len(self.dataqueue) < 10:
					break
				packets.append(self.dataqueue[0:10])
				self.dataqueue = self.dataqueue[10:]
			else:
				self.dataqueue = self.dataqueue[1:] # Ignore ; FIXME: Add error here
		elif self.dataqueue[0] == 255: # Exit
			packets.append(b"\xff")
			self.dataqueue = self.dataqueue[1:]
		else:
			break

	return packets

# The proto client used to be the only mean of testing network protocol modifications.
# It is now defunct
def protoclient(port):
	ip = "127.0.0.1" #"10.187.84.191"

	print("Starting Proto Client towards port {0}".format(port))
	d = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	d.connect((ip, port))
	print("Connected")
	d.settimeout(0)
	try:
		print(d.recv(2014))
	except:
		pass
	d.send(b"\x01\x00\x03\x04\x0A\xBB\x54\xd8\x1a\x0a") # Payload (Hello+Peer)
	d.send(b"\x02") # Exit
	d.close()
	print("Disconnected")
