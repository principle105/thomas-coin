import logging
import random
import socket
import string
import time

from tcoin.config import request_children_after
from tcoin.tangle import Tangle
from tcoin.tangle.messages import Message, message_lookup
from tcoin.utils import load_storage_file, save_storage_file
from tcoin.wallet import Wallet

from ..requests import DiscoverPeers, GetMsgs, Request, request_lookup
from .node_connection import NodeConnection
from .scheduler import Scheduler
from .threaded import Threaded

KNOWN_PEERS_FILE_NAME = "known_peers"


class Node(Threaded):
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

        self.host = host
        self.port = port

        self.tangle = tangle

        self.wallet = wallet

        # Connections
        self.nodes_inbound = {}
        self.nodes_outbound = {}

        # Other nodes that are known about
        self.other_nodes = {}

        self.max_connections = max_connections
        self.full_node = full_node

        # Initializing the TCP/IP server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_server()

        self.scheduler = Scheduler(self)

    @property
    def all_nodes(self):
        return {**self.nodes_inbound, **self.nodes_outbound}

    @property
    def id(self):
        return self.wallet.address

    def init_server(self):
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.settimeout(10.0)
        self.sock.listen(1)

    def send_to_nodes(self, data: dict, exclude: list[str] = []):
        for _id, n in self.all_nodes.items():
            if _id not in exclude:
                self.send_to_node(n, data)

    def send_to_node(self, node: NodeConnection, data: dict):
        if node.id in self.all_nodes:
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

    def create_message(self, msg_cls, index: int, payload: dict):
        return msg_cls(node_id=self.id, index=index, payload=payload)

    def create_request(self, request_cls, **payload):
        request = request_cls(node_id=self.id, payload=payload)

        request.add_hash()
        request.sign(self.wallet)

        return request

    def save_all_nodes(self):
        outbound_data = {
            _id: [n.host, n.port] for _id, n in self.nodes_outbound.items()
        }

        save_storage_file(
            KNOWN_PEERS_FILE_NAME, {**outbound_data, **self.other_nodes}
        )

    def connect_to_node(self, host: str, port: int):
        if host == self.host and port == self.port:
            logging.info("You cannot connect with yourself")
            return False

        if any(
            n.host == host and n.port == port
            for n in self.nodes_outbound.values()
        ):
            logging.info("You are already connected with that node")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            logging.debug(f"Connecting to {host} port {port}")
            sock.connect((host, port))

            connected_node_id = self.receive_connection(sock)

            if connected_node_id is None:
                return

            thread_client = self.create_new_connection(
                sock, connected_node_id, host, port
            )
            thread_client.start()

            self.nodes_outbound[connected_node_id] = thread_client

        except Exception:
            logging.debug("Could not connect with node")

        else:
            # Peer discovery
            request = self.create_request(DiscoverPeers)

            self.send_to_node(thread_client, request.to_dict())

    def create_new_connection(
        self, sock: socket.socket, id: str, host: str, port: int
    ):
        return NodeConnection(
            main_node=self, sock=sock, id=id, host=host, port=port
        )

    def node_disconnected(self, node: NodeConnection):
        if node.id in self.nodes_inbound:
            del self.nodes_inbound[node.id]

        if node.id in self.nodes_outbound:
            del self.nodes_outbound[node.id]

    def message_from_node(self, node: NodeConnection, data: dict):
        # Handling if the data is a request
        if self.handle_new_request(node, data):
            return

        # Handling if the data is a message
        self.handle_new_message(data, node=node)

    def request_msgs(
        self, msgs: list[str], initial: Message = None, history=False
    ):
        self.scheduler.add_pending(initial, msgs)

        request = self.create_request(
            GetMsgs,
            initial=initial.to_dict(),
            msgs=msgs,
            history=history,
        )

        self.send_to_nodes(request.to_dict())

    def handle_new_request(self, node: NodeConnection, data: dict):
        request: Request = request_lookup(data)

        if request is None:
            return False

        if request.is_valid() is False:
            return True

        if request.response is None:
            request.response = request.respond(self, node)

            if request.response is not None:
                self.send_to_node(node, request.to_dict())
            return True

        # Checking if the our node sent the request
        if self.id != request.node_id:
            return True

        request.receive(self, node)

        return True

    def handle_new_message(self, data: dict, node: NodeConnection = None):
        if (msg := self.serialize_msg(data)) is False:
            return False

        if msg.hash in self.tangle.all_msgs:
            return True

        # Queueing the message
        self.scheduler.queue_msg(msg)

        if node is None:
            return True

        # Propagating message to other nodes
        self.send_to_nodes(data, exclude=[node.id])

        return True

    def serialize_msg(self, data: dict):
        msg = message_lookup(data)

        if msg is None:
            return False

        # Semantically validate the message
        is_sem_valid = msg.is_sem_valid()

        if is_sem_valid is False:
            return False

        return msg

    def add_new_msg(self, msg: Message):
        if msg.hash in self.tangle.all_msgs:
            return

        result = msg.is_valid(self.tangle)

        if result is False:
            return

        invalid_parents = []
        occurs = []

        if result is not True:
            invalid_parents, unknown_parents = result

            # Checking if the message is not weak
            if not invalid_parents:
                age = time.time() - msg.timestamp

                # Getting the children of a message if the message is past a certain age
                if age >= request_children_after:
                    all_tips = list(self.tangle.all_tips)
                    self.request_msgs(initial=msg, msgs=all_tips, history=True)

                    return

                # Checking if the unknown messages are part of a branch
                occurs = self.tangle.find_occurs_in_branch(
                    set(unknown_parents)
                )

                unknown_parents = set(unknown_parents)

                parents_in_branch = set(
                    sum(
                        [
                            list(set(r.branch.msgs) & unknown_parents)
                            for r in occurs
                        ],
                        [],
                    )
                )

                still_unknown = unknown_parents - parents_in_branch

                if still_unknown:
                    # Only requesting messages that are still unknown (not part of a branch)
                    self.request_msgs(initial=msg, msgs=list(still_unknown))

                    return

        # Checking if any conflicts with the parents were already resolved
        if self.tangle.is_message_finalized(msg) is False:
            found_duplicate = self.tangle.find_duplicates_from_branches(
                msg, occurs
            )

            if found_duplicate:
                return

            if occurs:
                # Updating the conflicting branches
                for r in occurs:
                    # Genearating the state of the conflicting branch
                    new_state = self.tangle.get_state(r)

                    # Checking if the payload is valid with the new state
                    if msg.is_payload_valid(new_state):
                        r.branch.add_msg(msg, invalid_parents)
                    else:
                        # Adding to invalid messages in the branch
                        r.branch.state.add_invalid_msg(msg.hash)

                    # Updating the branch
                    self.tangle.branches[r.manager.id].update_conflict(
                        self.tangle, r.branch
                    )

                return

        # Checking if the message is already in the tangle
        if msg.hash in self.tangle.all_msgs:
            return

        # Checking if the payload is valid
        if msg.is_payload_valid(self.tangle) is False:
            self.tangle.state.add_invalid_msg(msg.hash)
            return

        index = self.tangle.get_transaction_index(msg.node_id)

        # Checking if the transaction index is correct
        if index != msg.index:
            return

        # Adding the message to the tangle if it doesn't exist yet
        self.tangle.add_msg(msg, invalid_parents)

    def receive_connection(self, sock: socket.socket):
        try:
            random_string = "".join(random.choices(string.ascii_letters, k=16))

            # Sending our id to other node
            sock.send(f"{self.id}:{random_string}".encode("utf-8"))

            # Receiving the other node's id and random string
            result = sock.recv(4096).decode("utf-8")

            connected_node_id, other_random_string = result.split(":")

            # Signing the random string
            signature = self.wallet.sign(other_random_string)

            # Sending the signature
            sock.send(signature.encode("utf-8"))

            # Receiving the other node's signature
            random_string_signature = sock.recv(4096).decode("utf-8")

            # Checking if the node id is valid
            if (
                Wallet.is_signature_valid(
                    connected_node_id, random_string_signature, random_string
                )
                is False
            ):
                return None

            return connected_node_id

        except Exception:
            return None

    def run(self):
        # Starting the scheduler
        self.scheduler.start()

        while not self.terminate_flag.is_set():
            try:
                logging.debug("Waiting for incoming connections...")
                connection, client_address = self.sock.accept()

                if (
                    self.max_connections != 0
                    and len(self.nodes_inbound) >= self.max_connections
                ):
                    logging.debug("Reached maximum connection limit")
                    connection.close()

                connected_node_id = self.receive_connection(connection)

                if connected_node_id is None:
                    return

                thread_client = self.create_new_connection(
                    connection,
                    connected_node_id,
                    client_address[0],
                    client_address[1],
                )
                thread_client.start()

                self.nodes_inbound[connected_node_id] = thread_client

            except socket.timeout:
                logging.debug("Connection timed out")

            except Exception as e:
                logging.exception(e)

            time.sleep(0.01)

        # Stopping the scheduler
        self.scheduler.stop()

        for node in self.all_nodes.values():
            node.stop()

        time.sleep(1)

        for node in self.all_nodes.values():
            node.join()

        self.sock.settimeout(None)
        self.sock.close()

        logging.info("Node stopped")
