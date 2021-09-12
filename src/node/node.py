import threading
import hashlib
import random
import socket
import time
from .node_connection import Node_Connection


# Based on https://github.com/macsnoeren/python-p2p-network
class Node(threading.Thread):
    def __init__(self, host, port, callback=None):

        super(Node, self).__init__()

        self.terminate_flag = threading.Event()

        self.host = host
        self.port = port

        self.callback = callback

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
        print("Initializing node ")
        print(
            "Node System: Initialisation of the Node on port: "
            + str(self.port)
            + " on node ("
            + self.id
            + ")"
        )
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
                self.inbound_node_disconnected(n)
                n.join()
                del self.nodes_inbound[self.nodes_inbound.index(n)]

        for n in self.nodes_outbound:
            if n.terminate_flag.is_set():
                self.outbound_node_disconnected(n)
                n.join()
                del self.nodes_outbound[self.nodes_inbound.index(n)]

    def send_data_to_nodes(self, data, exclude=[]):

        self.message_count_send = self.message_count_send + 1
        for n in self.nodes_inbound:
            if n in exclude:
                print(
                    "Node System: Node send_data_to_nodes: Excluding node in sending the message"
                )
            else:
                try:
                    self.send_data_to_node(n, data)
                except:  # lgtm [py/catch-base-exception]
                    pass

        for n in self.nodes_outbound:
            if n in exclude:
                print(
                    "Node System: Node send_data_to_nodes: Excluding node in sending the message"
                )
            else:
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

            except Exception as e:
                print(
                    "Node System: Node send_data_to_node: Error while sending data to the node ("
                    + str(e)
                    + ")"
                )
        else:
            print(
                "Node System: Node send_data_to_node: Could not send the data, node is not found!"
            )

    def connect_to_node(self, host, port):

        if host == self.host and port == self.port:
            print("Node System: connect_to_node: Cannot connect with yourself!!")
            return False

        # Check if node is already connected with this node!
        for node in self.nodes_outbound:
            if node.host == host and node.port == port:
                print("Node System: connect_to_node: Already connected with this node.")
                return True

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print("Node System: connecting to %s port %s" % (host, port))
            sock.connect((host, port))

            # Basic information exchange (not secure) of the id's of the nodes!
            sock.send(self.id.encode("utf-8"))  # Send my id to the connected node!
            connected_node_id = sock.recv(4096).decode(
                "utf-8"
            )  # When a node is connected, it sends it id!

            if node_is_unl(connected_node_id):
                thread_client = self.create_the_new_connection(
                    sock, connected_node_id, host, port
                )
                thread_client.start()

                self.nodes_outbound.append(thread_client)
                self.outbound_node_connected(thread_client)
            else:
                print(
                    "Node System: Could not connect with node because node is not unl node."
                )
        except Exception as e:
            print(
                "Node System: TcpServer.connect_to_node: Could not connect with node. ("
                + str(e)
                + ")"
            )

    def create_the_new_connection(self, connection, id, host, port):

        return Node_Connection(self, connection, id, host, port)

    def disconnect_to_node(self, node):

        if node in self.nodes_outbound:
            self.node_disconnect_to_outbound_node(node)
            node.stop()
            node.join()
            del self.nodes_outbound[self.nodes_outbound.index(node)]

        else:
            print(
                "Node System: Node disconnect_to_node: cannot disconnect with a node with which we are not connected."
            )

    def run(self):

        while not self.terminate_flag.is_set():
            try:
                connection, client_address = self.sock.accept()

                connected_node_id = connection.recv(4096).decode("utf-8")
                connection.send(self.id.encode("utf-8"))
                if node_is_unl(connected_node_id):
                    thread_client = self.create_the_new_connection(
                        connection,
                        connected_node_id,
                        client_address[0],
                        client_address[1],
                    )
                    thread_client.start()

                    self.nodes_inbound.append(thread_client)

                    self.inbound_node_connected(thread_client)
                else:
                    print(
                        "Node System: Could not connect with node because node is not unl node."
                    )

            except socket.timeout:
                pass

            except Exception as e:
                raise e

            time.sleep(0.01)

        print("Node System: Node stopping...")
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
        print("Node System: Node stopped")

    def outbound_node_connected(self, node):
        print("Node System: outbound_node_connected: " + node.id)

    def inbound_node_connected(self, node):
        print("Node System: inbound_node_connected: " + node.id)

    def inbound_node_disconnected(self, node):
        print("Node System: inbound_node_disconnected: " + node.id)

    def outbound_node_disconnected(self, node):
        print("Node System: outbound_node_disconnected: " + node.id)

    def message_from_node(self, node, data):
        print("Node System: message_from_node: " + node.id + ": " + str(data))
        if self.callback is not None:
            self.callback("message_from_node", self, node, data)

    def node_disconnect_to_outbound_node(self, node):
        print(
            "Node System: node wants to disconnect with oher outbound node: " + node.id
        )

    def node_request_to_stop(self):
        print("Node System: node is requested to stop!")

    def __str__(self):
        return "Node: {}:{}".format(self.host, self.port)

    def __repr__(self):
        return "<Node {}:{} id: {}>".format(self.host, self.port, self.id)
