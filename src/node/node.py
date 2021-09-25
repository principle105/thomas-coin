import threading
import hashlib
import socket
import time
import json
from .node_connection import Node_Connection
from blockchain import Blockchain
from config import UNL_PATH

def get_unl():
    with open(UNL_PATH, "r") as f:
        return json.load(f)

def get_connected_unl():
    unl = get_unl()

    print(unl)

    nodes = []
    for node in Node.main_node.nodes_inbound + Node.main_node.nodes_outbound:
        print({"host": node.host, "port": node.port})
        if {"host": node.host, "port": node.port} in unl:
            nodes.append(node)

    return nodes


def node_is_unl(host, port):
    return {"host": host, "port": port} in get_unl()

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

    def __init__(self, host: str, port: int):

        self.__class__.main_node = self

        super(Node, self).__init__()

        self.terminate_flag = threading.Event()

        self.host = host
        self.port = port

        # If the other node initiated the connection
        self.nodes_inbound = []

        # If we initiated the connection
        self.nodes_outbound = []

        self.id = self.generate_id()

        # Start the TCP/IP server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_server()

        # Message counters to make sure everyone is able to track the total messages
        self.message_count_send = 0
        self.message_count_recv = 0
        self.message_count_rerr = 0

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

    def send_data_to_nodes(self, msg_type: str, msg_data, exclude=[]):

        self.message_count_send = self.message_count_send + 1

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

        data = {
            "type": msg_type,
            "data": msg_data
        }

        self.message_count_send = self.message_count_send + 1
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
        my_node = {"host": self.host, "port": self.port}
        for node in get_unl():
            if node != my_node:
                self.connect_to_node(**node)

    def connect_to_node(self, host, port):
        # Making sure you can't connect with yourself
        if host == self.host and port == self.port:
            print("You can't connect to yourself")
            return False

        # Checking if you are already connected to this node
        for node in self.nodes_outbound:
            if node.host == host and node.port == port:
                print("You are already connected to this node")
                return True

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))

            sock.send(self.id.encode("utf-8"))
            connected_node_id = sock.recv(4096).decode("utf-8")

            thread_client = self.create_the_new_connection(
                sock, connected_node_id, host, port
            )
            thread_client.start()

            self.nodes_outbound.append(thread_client)

        except Exception as e:
            print(str(e))
            print("Could not connect with node")

    def create_the_new_connection(self, connection, id, host, port):
        return Node_Connection(self, connection, id, host, port)

    def disconnect_to_node(self, node):

        if node in self.nodes_outbound:
            node.stop()
            node.join()
            del self.nodes_outbound[self.nodes_outbound.index(node)]

        else:
            print("Not connected with node")

    def run(self):

        while not self.terminate_flag.is_set():
            # Accepting incoming connections
            try:
                connection, client_address = self.sock.accept()

                connected_node_id = connection.recv(4096).decode("utf-8")
                connection.send(self.id.encode("utf-8"))

                thread_client = self.create_the_new_connection(
                    connection,
                    connected_node_id,
                    client_address[0],
                    client_address[1],
                )
                thread_client.start()

                self.nodes_inbound.append(thread_client)

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
        unl_list = get_connected_unl()
        if unl_list:
            # Requesting block from first unl node
            self.send_data_to_node(unl_list[0], "sendchain", {})

    def send_chain(self, node):
        # Sending the entire blockchain minus the genesis block
        self.send_data_to_node(node, "chain", Blockchain.main_chain.get_json()[1:])

    def send_transaction(self, data: dict):
        print("Sending transaction")
        # Sending the transaction data to all the nodes
        self.send_data_to_nodes("newtrans", data)

    def message_from_node(self, node, data):
        print("message received")
        try:

            if list(data.keys()) != ["type", "data"]:
                print("Incorrect fields")
                return

            # TODO: check if unl
            if data["type"] == "chain":
                print("Received a chain")
                try:
                    chain = Blockchain.from_json(data["data"], validate=True)
                except Exception as e:
                    print("Invalid chain data", str(e))
                else:
                    # Checking if chain is more recent
                    if len(Blockchain.main_chain.blocks) > len(chain.blocks):
                        if compare_chains(Blockchain.main_chain, chain.blocks):
                            print("setting new main chain")
                            Blockchain.set_main(chain)
                        else:
                            print("Invalid chain")

            elif data["type"] == "sendchain":
                print("Sending chain")
                self.send_chain(node)

            elif data["type"] == "newtrans":
                print("Received a new transaction froma another node")

            elif data["type"] == "block":
                print("recieved a block")
                pass

            else:
                print(node, data)
        
        except Exception as e:
            print(str(e))
