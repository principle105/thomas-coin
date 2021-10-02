import threading
import hashlib
import socket
import time
import json
from .node_connection import Node_Connection
from blockchain import Blockchain, Transaction, Block
from config import UNL_PATH


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
        self, host: str, port: int, chain: Blockchain, max_connections: int = 0
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
        t = self.host + str(self.port)
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
                except:  # lgtm [py/catch-base-exception]
                    pass

        for n in self.nodes_outbound:

            if n not in exclude:
                try:
                    self.send_data_to_node(n, msg_type, msg_data)
                except:  # lgtm [py/catch-base-exception]
                    pass

    def send_data_to_node(self, n, msg_type: str, msg_data):

        data = {"type": msg_type, "data": msg_data}

        self.delete_closed_connections()
        if n in self.nodes_inbound or n in self.nodes_outbound:
            try:
                n.send(data)

            except:
                print("Error while sending data")
        else:
            print("Node not found")

    def connect_to_unl_nodes(self):
        print("connecting to nodes from unl")

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
            print("You can't connect to yourself")
            return False

        # Checking if you are already connected to this node
        for node in self.nodes_outbound:
            if node.host == host and node.port == port:
                print("You are already connected to this node")
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
        print("Node stopping")

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
        print("Node stoped")

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
        print("Sending transaction")
        # Sending the transaction data to all the nodes
        self.send_data_to_nodes("newtrans", data)

    def receive_new_transaction(self, node, data: dict):
        # Validating the new transaction against current chain
        try:
            t = Transaction.from_json(**data)
        except:
            print("Invalid transaction given")
        else:
            # Adding to pending transactions
            result = self.chain.add_pending(t)

            # If valid
            if result:
                # Broadcasting new transaction and other pending ones to nodes
                self.send_data_to_nodes("pending", self.chain.pending)

    def receive_new_block(self, node, data: dict):
        try:
            block = Block.from_json(**data)

            Node.main_node.add_block(block)

        except Exception as e:
            print("block invalid", str(e))

        else:
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

    def message_from_node(self, node, data):
        if list(data.keys()) != ["type", "data"]:
            print("Incorrect fields")
            return

        if data["type"] == "chain":
            unl = get_unl()

            # Checking if node is in unl
            if {"host": node.host, "port": node.port} not in unl:
                return

            print("Received a chain")

            try:
                chain = Blockchain.from_json(data["data"], validate=True)
            except Exception as e:
                print("Invalid chain data", str(e))
            else:
                # Checking if chain is more recent
                if len(self.chain.blocks) > len(chain.blocks):
                    if compare_chains(self.chain, chain.blocks):
                        print("setting new main chain")
                        chain.save_locally()
                    else:
                        print("Invalid chain")

        elif data["type"] == "sendchain":
            # Checking if node is pruned
            if self.chain.pruned:
                return

            print("Sending chain")
            self.send_chain(node)

        elif data["type"] == "newtrans":
            print("Received a new transaction from another node")
            self.receive_new_transaction(node, data["data"])

        elif data["type"] == "block":
            print("recieved a block")
            self.receive_new_block(node, data["data"])

        elif data["type"] == "sendpending":
            print("Sending pending transactions another node")
            self.send_pending(node)

        elif data["type"] == "pending":
            print("recieved pending transactions")
            self.receive_pending(node, data["data"])
