import threading
import hashlib
import random
import socket
import time
from .node_utils import node_is_unl, get_unl_nodes
from .node_connection import Node_Connection

# Based on https://github.com/macsnoeren/python-p2p-network
class Node(threading.Thread):
    main_node = None

    def __init__(self, host: str, port: int):

        self.__class__.main_node = self

        super(Node, self).__init__()

        self.terminate_flag = threading.Event()

        self.host = host
        self.port = port

        self.nodes_inbound = []

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
        t = self.host + str(self.port) + str(random.randint(1, 99999999))
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

    def send_data_to_nodes(self, data, exclude=[]):

        self.message_count_send = self.message_count_send + 1

        for n in self.nodes_inbound:

            if n not in exclude:
                try:
                    self.send_data_to_node(n, data)
                except:  # lgtm [py/catch-base-exception]
                    pass

        for n in self.nodes_outbound:

            if n not in exclude:
                try:
                    self.send_data_to_node(n, data)
                except:  # lgtm [py/catch-base-exception]
                    pass

    def send_data_to_node(self, n, data):

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
        for node in get_unl_nodes():
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

            # Basic information exchange (not secure) of the id's of the nodes!
            sock.send(self.id.encode("utf-8"))  # Send my id to the connected node!
            connected_node_id = sock.recv(4096).decode(
                "utf-8"
            )  # When a node is connected, it sends the id

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

    def message_from_node(self, node, data):
        pass
