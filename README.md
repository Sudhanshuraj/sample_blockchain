# Description of code
## seed.py
- It maintains a list of clients. 
- On acquiring a connection request from a client, it first verifies the client and sends it the client list. 
- It then waits till the client is initialized and then adds the client to client list. 
- This process is repeated forever until a SIGINT is sent.
- After it receives SIGINT, it sends a message to all the connected clients to start mining.
- After sending the message, it exits.

## client.py
- Client first connects to the seed node and gets client list. From that it selects few neighbours and connects to them. 
- This is the initialization part of client after which it informs the seed but doesn't close the connection as the seed sends the message to start mining.
- Then the client waits for incomming connections from new clients until it receives a message to start mine from the seed.
- After receiving the message from the seed to start mine, it starts mining following the protocol.

# Code usage
- Initialization - 
Change IP in seed_node.txt to IP of machine with seed node

- For seed node -
    `python3 seed.py` 

- For client node - (each on a different machine)
    `python3 client.py --hashPower [0-100] --seed [any random seed] --port [port number of miner] --adversary [0/1] --drawGraph [0/1] --simulationTime [simulation time in sec] --interArrivalTime [time in sec]`

# After Simulation
- After simulation is over two files will be generated 
    
    - `blockchain_[port].txt` : containing the serialized blockchain with a creator bool for each block representing whether that block is mined by that miner or not.
    
    - `stats_[port].txt` : containing the stats of the blockchain along with the forks.
        - First line representing the length of longest chain in the blockchain
        -  Second line represents the total number of blocks including the forks
        -  Third line represents the number of blocks in the largest chain of block mined by that miner

    - `PublicBlockChainFor_[port].png` : this will only be generated when the showGraph is true. It shows the graphical image of the public blockchain
    - `AdverserialBlockChainFor_[port].png` : this will be created when the miner is adversary and showGraph is true.
  
