from socket import *
import os
import argparse
import json
import random
import pdb
import time
import select
import hashlib
import signal
import numpy
import traceback
import copy
import sys

# parser arguments
parser = argparse.ArgumentParser()
parser.add_argument("--hashPower", help="Hashing power of this node")
parser.add_argument("--seed", help="Seed for randomness")
parser.add_argument("--port", help="Port for connection")
parser.add_argument("--adversary", help="Whether is adversary or not")
parser.add_argument("--drawGraph", help="Whether blockchain to be drawn or not")
parser.add_argument("--simulationTime", help="Time for simulation(in secs)")
parser.add_argument("--interArrivalTime", help="Time for inter arrival of blocks(in secs)")
args = parser.parse_args()
port = int(args.port)
nodeHashPower = float(args.hashPower)
_seed = int(args.seed)
random.seed(_seed)
adversary = False if int(args.adversary) == 0 else True
draw_graph = False if int(args.drawGraph) == 0 else True
simulation_time = int(args.simulationTime)
interarrivaltime = float(args.interArrivalTime)

block_header_size = 30

# files for printing stats and blockchain at termination
f = open('block_chain_%d.txt'%(port), 'w')
f.close()
f = open('stats_%d.txt'%(port), 'w')
f.close()

class BlockHeader:
	def __init__(self, previous_hash, merkel_root, time_stamp, creator_ = 0):
		self.previousHash = previous_hash
		self.merkelRoot = merkel_root
		self.timeStamp = time_stamp
		self.creator = creator_
	
	# creates a string from blockHeader for sending over network
	def serializeBlock(self):
		merkel_len = len(str(self.merkelRoot))
		serialized_block = str(self.previousHash) + ":" + (5-merkel_len)*'0' + str(self.merkelRoot) + ":" + str(self.timeStamp)[0:17]
		block_len = len(serialized_block)
		if block_len != block_header_size:
			serialized_block + (block_header_size-block_len)*'0'
		return serialized_block

	# returns the hash of the blockheader
	def hashOfBlock(self):
		hashObject = hashlib.sha3_256((self.serializeBlock()).encode('ASCII'))
		return "0x" + hashObject.hexdigest()[-4:]
	
	# returns whether the two blocks are same or not (it could be created by anyone)
	def same_block(self, block2):
		if self.previousHash == block2.previousHash and self.merkelRoot == block2.merkelRoot and self.timeStamp == block2.timeStamp:
			return True
		return False
	

class BlockChain:
	def __init__(self, blockHeader_):
		self.blockHeader = blockHeader_
		self.children = []
	
	# preety prints the blockchain with proper spaces and tabbing 
	def print_chain(self, spacing = 0, print_file=sys.stdout):
		print("\t"*spacing , self.blockHeader.previousHash, self.blockHeader.merkelRoot, self.blockHeader.timeStamp, self.blockHeader.creator, file=print_file)
		for child in self.children:
			child.print_chain(spacing+1, print_file)

	# inserts a block to the blockchain if it already doesn't exist
	def validate_and_insert(self, recvd, creator_):
		recvd_split = recvd.split(":")
		previousHash = recvd_split[0]
		merkelRoot = recvd_split[1]
		timeStamp = (recvd_split[2])[0:17]
		x_pos = timeStamp.find('0x')
		if x_pos >= 0:
			timeStamp = timeStamp[:x_pos]
		timenow = time.time()
		delta = 60 * 60
		if not(timenow - delta <= float(timeStamp) <= timenow + delta):
			return False

		if self.blockHeader.hashOfBlock() == previousHash or previousHash == genesis_block_hash:
			block = BlockHeader(previousHash, int(merkelRoot), float(timeStamp), creator_)
			for child in self.children:
				if block.same_block(child.blockHeader):
					return False
			child = BlockChain(block)
			(self.children).append(child)
		else:
			if self.children == []:
				return False
			else:
				insert_child = False
				for child in self.children:
					insert_child = child.validate_and_insert(recvd, creator_) or insert_child
				return insert_child
		return True

	# finds the longest chain in the blockchain and returns the hash of its last block
	def last_hash_of_longest_chain(self):
		if self.children == []:
			return self.blockHeader.previousHash, self.blockHeader.hashOfBlock()
		else:
			curr_hash = "0x0000"
			priv_hash = "0x0000"
			max_len = 0
			for child in self.children:
				if max_len < child.len_chain():
					priv_hash, curr_hash = child.last_hash_of_longest_chain()
			return priv_hash, curr_hash

	# returns the length of the longest chain of the blockchain
	def len_chain(self):
		if self.children == []:
			return 1
		else:
			max_ = 0
			for child in self.children:
				max_ = max(child.len_chain(), max_)
			return max_ + 1

	# returns the number of blocks in the blockchain including the forks
	def size_of_chain(self):
		if self.children == []:
			return 1
		else:
			sum_ = 0
			for child in self.children:
				sum_ += child.size_of_chain()
			return sum_ + 1

	# returns the number of blocks created by the miner in the longest chain of the blockchain
	def client_contribution(self):
		length = self.len_chain()
		if self.children == []:
			if self.blockHeader.creator == 1:
				return 1
			else:
				return 0
		for child in self.children:
			if child.len_chain() == length-1:
				temp = child.client_contribution()
				if self.blockHeader.creator == 1:
					return 1 + temp
				else:
					return temp

	# calculates the average interval time in the longest chain of the blockchain (not required now)
	def averageInterArrivalTime(self):
		sum_ = 0
		count = 0
		if self .children == []:
			return sum_, count
		for child in self.children:
			if self.blockHeader.previousHash != "genesisBlock":
				sum_ += (child.blockHeader.timeStamp - self.blockHeader.timeStamp)
				count += 1
			a,b = child.averageInterArrivalTime()
			sum_ += a
			count += b
		return sum_, count

	# Used for adversary: returns the list of blocks to be published after the length specified
	def publishable_blocks(self, length_already_published):
		publishableBlocks = []
		max_len = self.len_chain()
		if length_already_published <= 0:
			block_serialized = self.blockHeader.serializeBlock()
			publishableBlocks.append(block_serialized)
		for child in self.children:
			if child.len_chain() == max_len - 1:
				publishableBlocks += child.publishable_blocks(length_already_published-1)
				break
		return publishableBlocks
	
	# create graph of blockchain for its graphcal representation
	def build_graph(self, Graph, color_map):
		for child in self.children:
			Graph.add_node(child.blockHeader.serializeBlock()[:-18])
			if child.blockHeader.creator == 1:
				color_map.append('green')
			else:
				color_map.append('blue')
			Graph.add_edge(self.blockHeader.serializeBlock()[:-18], child.blockHeader.serializeBlock()[:-18])
			child.build_graph(Graph, color_map)

	# prints the statistics of the blockchain : its length, size and etc
	def print_stats(self, stats_file=sys.stdout):
		print(self.len_chain() - 1, file=stats_file)
		print(self.size_of_chain() - 1, file=stats_file)
		print(self.client_contribution(), file=stats_file)
	
	# draws the blockchain 
	def drawBlockChain(self, title):
		import networkx as nx  
		import matplotlib.pyplot as plt
		G = nx.DiGraph()
		color_map = []
		G.add_node(self.blockHeader.serializeBlock()[:-18])
		if self.blockHeader.creator == 1:
			color_map.append('green')
		else:
			color_map.append('blue')
		self.build_graph(G, color_map)
		nx.draw(G, with_labels=True, node_color=color_map, font_weight='bold')
		plt.savefig(title)
		plt.suptitle(title)
		plt.show()

def signal_handler(sig, frame):
	exit_function()
	exit()

def get_ip():
	# gives the ip of this machine
	s = socket(AF_INET, SOCK_DGRAM)
	s.connect(("8.8.8.8", 80))
	ip = str(s.getsockname()[0])
	s.close()
	return ip

def send_to_all(n_socs, msg_to_send):
	# send the message to all the sockets in n_socs
	for soc in n_socs:
		soc.sendall(msg_to_send.encode("ASCII"))


socs = []
genesis_block = BlockHeader("genesisBlock", random.getrandbits(16), time.time())
genesis_block_hash = '0x9e1c'
blockChainForked = BlockChain(genesis_block)
if adversary:
	adversarialBlockChain = BlockChain(genesis_block)
	after_length = 1
signal.signal(signal.SIGINT, signal_handler)

def simulate():
	global adversarialBlockChain
	global blockChainForked
	global after_length
	# make Seed nodes
	file_seed = open("seed_node.txt",'r')
	seed_info = file_seed.readline()
	seed_info = seed_info.split("\t")
	seed_ip = seed_info[0]
	seed_port = int(seed_info[1])
	
	cmd = "rm -f ./outputfile*"
	os.system(cmd)
	
	client = socket(AF_INET, SOCK_STREAM) # client node
	socs.append(client)

	listener = socket(AF_INET, SOCK_STREAM) # client will accept other clients on listner socket
	listener.bind((get_ip(), port))
	socs.append(listener)
	listener.listen(5)

	# open("outputfile.txt", 'w', 1)

	while True: # connect to seed
		try:
			client.connect((seed_ip, seed_port))
			print("connected to seed", client.getsockname())
			break
		except:
			print("refused connection to seed sleeping for 5 seconds", client.getsockname())
			time.sleep(5)

	# validate itself as client and get CL
	client.sendall(b'send CL')
	CL = client.recv(10000)
	CL = json.loads(CL.decode('ASCII'))
	# print("CL RECVD: ", CL,  file=open("outputfile.txt", 'a', 1))

	n_socs = [] # message sockets
	if CL == []: # if first client
		print("first client", listener.getsockname())
		pass
	else:
		random.shuffle(CL) # get neighbours from CL
		neighbours = CL[:random.randrange(1, 5)]

		for n in neighbours: # estabilish connection with neighbours
			s = socket(AF_INET, SOCK_STREAM)
			while True:
				try:
					s.connect((n[0], n[1])) # CL had listener sockets of clients
					break
				except:
					print("refused connection to neighbour", n, "sleeping for 5 seconds", listener.getsockname())
					time.sleep(5)

			s.sendall(b'hey neighbour') # validate itself to neighbour client
			data = b''
			while True: # recieve from neighbour its reciever
				data = s.recv(10000)
				if data != b'':
					data = json.loads(data.decode('ASCII')) # get a message socket from neighbour
					s_con = socket(AF_INET, SOCK_STREAM)
					n_socs.append(s_con) # make new message socket
					socs.append(s_con)
					break

			while True:
				try:
					n_socs[-1].connect((n[0],data[1])) # connect to the message socket of neighbour
					break
				except:
					print("refused connection to neighbour's receiver", data, "sleeping for 5 seconds", listener.getsockname())
					time.sleep(5)

			s.shutdown(SHUT_RDWR) # close connection socket to neighbour
			s.close()
			print(listener.getsockname(), "connected to neighbour", n)

			# test message connection
			n_socs[-1].sendall(b'mike check! new client')
			first_recvd = n_socs[-1].recv(10000)
		print("connected with all neighbours")					

	client.sendall(json.dumps(listener.getsockname()).encode('ASCII')) # close connection with seed

	listener.setblocking(0)
	print("accepting", listener.getsockname())

	while True: # accept connections from other clients
		ready_to_read, ready_to_write, in_error = select.select([client], [client], [], 0)	# returns whether anything to read from the sockets in CL
		try:	# checks whether any connection is waiting to be connected on the listener socket
			c,a = listener.accept()
			req = c.recv(10000)
			if req != b'hey neighbour': # validate client
				print(listener.getsockname(), "invalid request from", a)
				pass
			else:
				s = socket(AF_INET, SOCK_STREAM) # make new message socket and send to new neighbour
				s.listen(5)
				c.sendall(json.dumps(s.getsockname()).encode('ASCII'))
				c1,a1 = s.accept() # connect to the message socket of neighbour
				n_socs.append(c1)
				socs.append(c1)

				s.shutdown(SHUT_RDWR)
				s.close()

			print(listener.getsockname(), "connected to new neighbour")
			c.shutdown(SHUT_RDWR)
			c.close()

			# test message connection
			test_msg_recvd = n_socs[-1].recv(10000)
			n_socs[-1].sendall(b'mike check! old client')
		except:
			pass

		if ready_to_read != []:	# something to read from the sockets
			soc = ready_to_read[0]
			recvd = soc.recv(10000)
			if recvd == b'start mining':
				break

	listener.shutdown(SHUT_RDWR)
	listener.close()
	print("="*5+"Mining started"+"="*5)
	simulation_start = time.time()
	try:
		while time.time() < simulation_start + simulation_time:
			# calculation of waiting time
			globalLambda = 1.0/interarrivaltime
			_lambda = nodeHashPower * globalLambda/100.0
			timenow = time.time()
			waitingTime = (numpy.random.exponential()/_lambda)
			
			# wait to receive blocks from peers
			while time.time() < simulation_start + simulation_time:
				ready_to_read, ready_to_write, in_error = select.select(n_socs, n_socs, [], 0)
				if ready_to_read != []:	# something to read from the sockets
					priv_length = blockChainForked.len_chain()
					if adversary:
						priv_adverserial_length = adversarialBlockChain.len_chain()
					for soc in ready_to_read:
						recvd = (soc.recv(block_header_size)).decode("ASCII")
						if blockChainForked.validate_and_insert(recvd, 0):
							send_to_all(n_socs, recvd)
					new_length = blockChainForked.len_chain()
					if new_length > priv_length and not adversary:
						break
					
					if adversary and priv_adverserial_length == new_length:
						publishableBlocks = adversarialBlockChain.publishable_blocks(after_length)
						for serialized_blocks in publishableBlocks:
							blockChainForked.validate_and_insert(serialized_blocks, 1)
							send_to_all(n_socs, serialized_blocks)
						after_length = new_length
					elif adversary and new_length > priv_adverserial_length:
						adversarialBlockChain = copy.deepcopy(blockChainForked)
						after_length = new_length
						break

				# create block itself if time expires and new block is not received
				if time.time() > timenow + waitingTime:
					if adversary:
						hashInLastBlock, lastBlockHashVal = adversarialBlockChain.last_hash_of_longest_chain()
					else:
						hashInLastBlock, lastBlockHashVal = blockChainForked.last_hash_of_longest_chain()
					block = BlockHeader(lastBlockHashVal, random.getrandbits(16), time.time())
					if hashInLastBlock == "genesisBlock":
						block = BlockHeader(genesis_block_hash, random.getrandbits(16), time.time())
					block_serialized = block.serializeBlock()
					if not adversary:
						blockChainForked.validate_and_insert(block_serialized, 1)		
						send_to_all(n_socs, block_serialized)
					else:
						adversarialBlockChain.validate_and_insert(block_serialized, 1)		
					break
		exit_function()
	except Exception:
		print("="*5+"ERROR"+"="*5)
		traceback.print_exc()
		exit_function()

def exit_function():
	print("="*5+'Exiting Safely'+"="*5)
		
	print("="*5+'Public Blockchain'+"="*5, file=open('block_chain_%d.txt'%(port), 'a', 1))
	blockChainForked.print_chain(print_file=open('block_chain_%d.txt'%(port), 'a', 1))
	
	print("="*5+'Stats of Public Blockchain'+"="*5, file=open("stats_%d.txt"%(port), 'a', 1))
	blockChainForked.print_stats(stats_file=open("stats_%d.txt"%(port), 'a', 1))
	
	if adversary:
		print("="*5+'Adverserial Blockchain'+"="*5, file=open('block_chain_%d.txt'%(port), 'a', 1))
		adversarialBlockChain.print_chain(print_file=open('block_chain_%d.txt'%(port), 'a', 1))
		
		print("="*5+'Stats of Adverserial Blockchain'+"="*5, file=open("stats_%d.txt"%(port), 'a', 1))
		adversarialBlockChain.print_stats(stats_file=open("stats_%d.txt"%(port), 'a', 1))

	#======================================================================================================
	if draw_graph:
		blockChainForked.drawBlockChain("PublicBlockChainFor_%d.png"%(port))
	if draw_graph and adversary:
		adversarialBlockChain.drawBlockChain("AdversarialBlockChainFor_%d.png"%(port)) 
	#======================================================================================================

	for c in socs:
		c.close()

if __name__ == "__main__":
	simulate()
	exit()