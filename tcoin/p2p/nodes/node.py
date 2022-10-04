import logging
import random
import socket
import time
from threading import Event, Thread

from tcoin.config import request_children_after
from tcoin.tangle import Tangle
from tcoin.tangle.messages import Message, message_lookup
from tcoin.utils import load_storage_file, save_storage_file
from tcoin.wallet import Wallet

from ..requests import DiscoverPeers, GetMsgs, Request, request_lookup
from .node_connection import NodeConnection

KNOWN_PEERS_FILE_NAME = "known_peers"


class Node(Thread):
    def __init__(
        self,
        *,
        host: str,
        port: int,
        tangle: Tangle,
        wallet: Wallet,
        full_node: bool = False,
        max_connections: int = 30,
    ):
        super().__init__()

        self.terminate_flag = Event()

        self.host = host
        self.port = port

        self.tangle = tangle

        self.wallet = wallet

        # Connections
        self.nodes_inbound = []
        self.nodes_outbound = []

        # Other nodes that are known about
        self.other_nodes = {}

        self.max_connections = max_connections
        self.full_node = full_node

        self.request_callback_pool = {}  # hash: callback

        # Initializing the TCP/IP server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_server()

    @property
    def all_nodes(self):
        return self.nodes_inbound + self.nodes_outbound

    @property
    def id(self):
        return self.wallet.address

    def init_server(self):
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.settimeout(10.0)
        self.sock.listen(1)

    def stop(self):
        self.terminate_flag.set()

    def send_to_nodes(self, data: dict, exclude: list[str] = []):
        for n in self.all_nodes:
            if n not in exclude:
                self.send_to_node(n, data)

    def send_to_node(self, node: NodeConnection, data: dict):
        if node in self.all_nodes:
            node.send(data)

    def get_known_nodes(self):
        return load_storage_file(KNOWN_PEERS_FILE_NAME)

    def connect_to_known_nodes(self):
        saved_nodes = self.get_known_nodes()

        # Trying to connect with up to 30 saved nodes
        if saved_nodes:
            amt = min(max(len(saved_nodes), 1), 30)

            for host, port in random.sample(list(saved_nodes.values()), amt):
                self.connect_to_node(host, port)

    def sync_tangle(self):
        ...

    def create_message(self, msg_cls, payload: dict):
        return msg_cls(node_id=self.id, payload=payload)

    def create_request(self, request_cls, **payload):
        request = request_cls(node_id=self.id, payload=payload)

        request.add_hash()
        request.sign(self.wallet)

        return request

    def save_all_nodes(self):
        data = self.get_known_nodes()

        for n in self.nodes_outbound:
            data[n.id] = [n.host, n.port]

        for i, (host, port) in self.other_nodes.items():
            data[i] = [host, port]

        save_storage_file(KNOWN_PEERS_FILE_NAME, data)

    def connect_to_node(self, host: str, port: int):
        if host == self.host and port == self.port:
            logging.info("You cannot connect with yourself")
            return False

        if any(n.host == host and n.port == port for n in self.nodes_outbound):
            logging.info("You are already connected with that node")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            logging.debug(f"Connecting to {host} port {port}")
            sock.connect((host, port))

            # Sending our id to other node
            sock.send(self.id.encode("utf-8"))

            # Receiving the node id once complete
            connected_node_id = sock.recv(4096).decode("utf-8")

            thread_client = self.create_new_connection(
                sock, connected_node_id, host, port
            )
            thread_client.start()

            self.nodes_outbound.append(thread_client)

        except Exception:
            logging.debug("Could not connect with node")

        else:
            # Peer discovery
            request = self.create_request(DiscoverPeers)

            self.send_to_node(thread_client, request.to_dict())

    def create_new_connection(self, sock: socket.socket, id: str, host: str, port: int):
        return NodeConnection(main_node=self, sock=sock, id=id, host=host, port=port)

    def node_disconnected(self, node):
        if node in self.nodes_inbound:
            self.nodes_inbound.remove(node)

        if node in self.nodes_outbound:
            self.nodes_outbound.remove(node)

    def message_from_node(self, node: NodeConnection, data: dict):
        # Handling if the data is a request
        if self.handle_new_request(node, data):
            return

        # Handling if the data is a message
        self.handle_new_message(node, data)

    def request_msgs(self, msgs: list, initial: Message = None, history=False):
        request = self.create_request(
            GetMsgs,
            initial=initial.to_dict(),
            msgs=msgs,
            history=history,
        )

        if initial is not None:
            callback = lambda node: self.handle_new_message(
                node, initial.to_dict(), propagate=False
            )

            self.request_callback_pool[request.hash] = callback

        self.send_to_nodes(request.to_dict())

    def handle_new_request(self, node: NodeConnection, data: dict):
        request: Request = request_lookup(data)

        if request is None:
            return False

        if request.is_valid() is False:
            return False

        if request.response is None:
            request.response = request.respond(self, node)

            if request.response is not None:
                self.send_to_node(node, request.to_dict())
            return True

        # Checking if the our node sent the request
        if self.id != request.node_id:
            return False

        request.receive(self, node)

        # Executing the request callback if there is one
        callback = self.request_callback_pool.get(request.hash, None)

        if callback is not None:
            callback(node)

    def handle_new_message(self, node: NodeConnection, data: dict, propagate=True):
        msg = message_lookup(data)

        if msg is None:
            return

        result = msg.is_valid(self.tangle)

        if result is False:
            return

        invalid_parents = []

        if result is not True:
            invalid_parents, unknown_parents = result

            # Checking if the message is not weak
            if not invalid_parents:
                age = time.time() - msg.timestamp

                # Getting the children of a message if the message is past a certain age
                if age >= request_children_after:
                    all_tips = list(self.tangle.state.all_tips)
                    self.request_msgs(initial=msg, msgs=all_tips, history=True)

                else:
                    self.request_msgs(initial=msg, msgs=unknown_parents)

                return True

        if self.tangle.get_msg(msg.hash) is None:
            # Checking if the payload is valid all parents are known about
            if msg.is_payload_valid(self.tangle) is False:
                self.tangle.state.add_invalid_msg(msg.hash)
                return False

            # Adding the message to the tangle if it doesn't exist yet
            self.tangle.add_msg(msg, invalid_parents)

            # Propagating message to other nodes
            if propagate:
                self.send_to_nodes(data, exclude=[node])

        return True

    def run(self):
        while not self.terminate_flag.is_set():
            try:
                logging.debug("Waiting for incoming connections...")
                connection, client_address = self.sock.accept()

                if (
                    self.max_connections == 0
                    or len(self.nodes_inbound) < self.max_connections
                ):

                    connected_node_id = connection.recv(4096).decode("utf-8")

                    connection.send(self.id.encode("utf-8"))

                    thread_client = self.create_new_connection(
                        connection,
                        connected_node_id,
                        client_address[0],
                        client_address[1],
                    )
                    thread_client.start()

                    self.nodes_inbound.append(thread_client)

                else:
                    logging.debug("Reached maximum connection limit")
                    connection.close()

            except socket.timeout:
                logging.debug("Connection timed out")

            except Exception as e:
                logging.exception(e)

            time.sleep(0.01)

        for node in self.all_nodes:
            node.stop()

        time.sleep(1)

        for node in self.all_nodes:
            node.join()

        self.sock.settimeout(None)
        self.sock.close()

        logging.info("Node stopped")
