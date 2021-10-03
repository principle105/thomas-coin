import threading
import hashlib
import socket
import time
import logging
import random
import json
from .node_connection import Node_Connection
from blockchain import Blockchain, Transaction, Block
from config import UNL_PATH, MIN_TIP

logger = logging.getLogger("node")


def get_unl():
    with open(UNL_PATH, "r") as f:
        return json.load(f)


def compare_chains(other_chain: Blockchain, our_chain: Blockchain):
    other_chain, our_chain = other_chain.blocks, our_chain.blocks
    """
    Validates another blockchain against ours
    """
    for i in range(len(our_chain)):
        if other_chain[i] != our_chain[i]:
            return False

    return True


# Based on https://github.com/macsnoeren/python-p2p-network
class Node(threading.Thread):
    main_node = None

    def __init__(
        self,
        host: str,
        port: int,
        chain: Blockchain,
        max_connections: int = 0,
        full_node: bool = True,
    ):

        self.__class__.main_node = self

        super(Node, self).__init__()

        self.terminate_flag = threading.Event()

        self.host = host
        self.port = port

        # Main blockchain
        self.chain = chain

        # If the other node initiated the connection
        self.nodes_inbound = []

        # If we initiated the connection
        self.nodes_outbound = []

        self.id = self.generate_id()

        # Max number of connections
        self.max_connections = max_connections

        # If the node is a full node
        self.full_node = full_node

        # Start the TCP/IP server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_server()

    def init_server(self):
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.settimeout(10.0)
        self.sock.listen(1)

    def generate_id(self):
        id = hashlib.sha512()
        t = self.host + str(self.port) + str(random.randint(1,999))
        id.update(t.encode("ascii"))
        return id.hexdigest()

    def stop(self):
        self.terminate_flag.set()

    def delete_closed_connections(self):

        for n in self.nodes_inbound:
            if n.terminate_flag.is_set():
                n.join()
                del self.nodes_inbound[self.nodes_inbound.index(n)]

        for n in self.nodes_outbound:
            if n.terminate_flag.is_set():
                n.join()
                del self.nodes_outbound[self.nodes_inbound.index(n)]

    def get_connected_unl(self) -> list:
        """
        List of unl nodes that you are connected to
        """
        unl = get_unl()

        nodes = []
        for node in self.nodes_inbound + self.nodes_outbound:
            if {"host": node.host, "port": node.port} in unl:
                nodes.append(node)

        return nodes

    def send_data_to_nodes(self, msg_type: str, msg_data, exclude=[]):

        for n in self.nodes_inbound:

            if n not in exclude:
                try:
                    self.send_data_to_node(n, msg_type, msg_data)
                except:
                    pass

        for n in self.nodes_outbound:

            if n not in exclude:
                try:
                    self.send_data_to_node(n, msg_type, msg_data)
                except:
                    pass

    def send_data_to_node(self, n, msg_type: str, msg_data):

        data = {"type": msg_type, "data": msg_data}

        self.delete_closed_connections()
        if n in self.nodes_inbound or n in self.nodes_outbound:
            try:
                n.send(data)

            except:
                logging.warning("Error while sendingdata")
        else:
            print("Node not found")

    def connect_to_unl_nodes(self):
        logging.info("Trying to connect to unl nodes")

        connected = False

        my_node = {"host": self.host, "port": self.port}

        for node in get_unl():
            if node != my_node:
                if self.connect_to_node(**node):
                    connected = True

        return connected

    def connect_to_node(self, host, port):
        # Making sure you can't connect with yourself
        if host == self.host and port == self.port:
            logging.warning("You can't connect with yourself")
            return False

        # Checking if you are already connected to this node
        for node in self.nodes_outbound:
            if node.host == host and node.port == port:
                logger.warning("You are already connected to this node")
                return False

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))

            sock.send(self.id.encode("utf-8"))
            connected_node_id = sock.recv(4096).decode("utf-8")

            thread_client = self.create_a_new_connection(
                sock, connected_node_id, host, port
            )
            thread_client.start()

            logging.info(f"Connected with node")

            self.nodes_outbound.append(thread_client)

            return True

        except:
            return False

    def create_a_new_connection(self, connection, id, host, port):
        return Node_Connection(self, connection, id, host, port)

    def run(self):

        while not self.terminate_flag.is_set():
            # Accepting incoming connections
            try:
                connection, client_address = self.sock.accept()

                # Disconnecting if maxiumum connections is reachd
                if (
                    self.max_connections == 0
                    or len(self.nodes_inbound) < self.max_connections
                ):

                    connected_node_id = connection.recv(4096).decode("utf-8")
                    connection.send(self.id.encode("utf-8"))

                    thread_client = self.create_a_new_connection(
                        connection,
                        connected_node_id,
                        client_address[0],
                        client_address[1],
                    )
                    thread_client.start()

                    self.nodes_inbound.append(thread_client)
                else:
                    connection.close()
            except socket.timeout:
                pass

            except Exception as e:
                raise e

            time.sleep(0.01)

        logger.info("Node stopping")

        for t in self.nodes_inbound:
            t.stop()

        for t in self.nodes_outbound:
            t.stop()

        time.sleep(1)

        for t in self.nodes_inbound:
            t.join()

        for t in self.nodes_outbound:
            t.join()

        self.sock.settimeout(None)
        self.sock.close()
        logger.info("Node stopped")

    def request_chain(self):
        # Getting nodes that we are connected to from unl
        unl_list = self.get_connected_unl()
        if unl_list:
            # Requesting block from first unl node
            self.send_data_to_node(unl_list[0], "sendchain", {})

    def send_chain(self, node):
        # Sending the entire blockchain minus the genesis block
        self.send_data_to_node(node, "chain", self.chain.get_json()[1:])

    def send_transaction(self, data: dict):
        logger.info("Broadcasting transaction")
        # Sending the transaction data to all the nodes
        self.send_data_to_nodes("newtrans", data)

    def receive_new_transaction(self, node, data: dict):
        # Validating the new transaction against current chain
        try:
            t = Transaction.from_json(**data)
        except:
            logger.warning("Malformed transaction data")
        else:
            # Not accepting transaction if under configured minimum tip
            if t.tip < MIN_TIP:
                logger.warning("Transaction under minimum tip")
                return

            # Adding to pending transactions and checking if it's valid
            if self.chain.add_pending(t):

                # Broadcasting new transaction and other pending ones to nodes
                self.send_data_to_nodes("pending", self.chain.pending)

    def receive_new_block(self, node, data: dict):
        try:
            block = Block.from_json(**data)
        except Exception as e:
            logger.warning("Malformed block data")
        else:
            if self.chain.add_block(block):
                # Sending new block to other nodes except original
                self.send_data_to_nodes("block", data, [node])

    def send_pending(self, node):
        self.send_data_to_node(node, "pending", self.chain.pending)

    def receive_pending(self, node, data):
        if data == self.chain.pending:
            return

        added_new = False

        for m in data:
            try:
                t = Transaction.from_json(**m)
            except:
                pass
            else:
                if self.chain.add_pending(t):
                    added_new = True

        if added_new:
            # Broadcasting valid pending transaction to other nodes except original
            self.send_data_to_nodes("pending", self.chain.pending, [node])

    def receive_chain(self, data):
        try:
            chain = Blockchain.from_json(data, validate=True)
        except Exception as e:
            logger.warning("Invalid chain data")
        else:
            # Checking if chain is more recent
            if len(self.chain.blocks) > len(chain.blocks):
                if compare_chains(self.chain, chain.blocks):
                    logger.info("Setting new main chain")
                    chain.save_locally()
                else:
                    logger.info("Invalid chain data")

    def message_from_node(self, node, data):
        if list(data.keys()) != ["type", "data"]:
            return

        if data["type"] == "chain":
            unl = get_unl()

            # Checking if node is in unl
            if {"host": node.host, "port": node.port} not in unl:
                return

            logger.info("Received chain from unl node")

            self.receive_chain(data["data"])

        elif data["type"] == "newtrans":
            logger.info("Received a new transaction")
            self.receive_new_transaction(node, data["data"])

        elif data["type"] == "block":
            logger.info("Received a new block")
            self.receive_new_block(node, data["data"])

        elif data["type"] == "pending":
            logger.info("Received a new pending transaction")
            self.receive_pending(node, data["data"])

        # Checking if node is a full node
        if self.full_node == True:
            if data["type"] == "sendchain":
                # Checking if node is pruned
                if self.chain.pruned:
                    return

                logger.info("Sending chain to node")
                self.send_chain(node)

            elif data["type"] == "sendpending":
                logger.info("Sending pending transaction to node")
                self.send_pending(node)
