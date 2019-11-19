import os
import argparse
import json
from socket import *
import pdb
import signal

socs = []

def signal_handler(sig, frame):

	for c in socs[1:]:
		c.sendall(b'start mining')
	print("Message to start mining sent to all clients")	
	print('Exiting Safely')
	for c in socs:
		c.close()
	exit()

signal.signal(signal.SIGINT, signal_handler)

def get_ip():
	# gives the ip of this machine
	s = socket(AF_INET, SOCK_DGRAM)
	s.connect(("8.8.8.8", 80))
	ip = str(s.getsockname()[0])
	s.close()
	return ip

def main():
	# make Seed nodes
	seed = socket(AF_INET, SOCK_STREAM)
	
	file_seed = open("seed_node.txt",'r')
	seed_info = file_seed.readline()
	seed_info = seed_info.split("\t")
	seed_ip = seed_info[0]
	seed_port = int(seed_info[1])

	seed.bind((seed_ip, seed_port))
	socs.append(seed)
	seed.listen(5)
	CL = []

	while True: # accept clients eternally
		c,a = seed.accept()
		socs.append(c)
		req = c.recv(10000)
		if req != b'send CL': # validate client
			print("invalid request from", a)
		else:
			print("sending CL") # send CL
			c.sendall(json.dumps(CL).encode('ASCII'))
			print("CL sent")
			while True: # confirm client has initialized
				data = c.recv(10000)
				if data != b'':
					# recieve from client the socket on which it will accept connections
					# from other clients and add it to CL
					data = json.loads(data.decode('ASCII'))
					CL.append(data)
					break
			print("connected to", CL[-1])
		
if __name__ == "__main__":
	main()