import threading
import json
import socket
import time
from .node_utils import save_connected_node

# Based on https://github.com/macsnoeren/python-p2p-network
class Node_Connection(threading.Thread):
    def __init__(self, main_node, sock, id, host: str, port: int):

        super(Node_Connection, self).__init__()

        self.host = host
        self.port = port
        self.main_node = main_node
        self.sock = sock
        self.terminate_flag = threading.Event()

        self.id = id

        self.candidate_block = None
        self.candidate_block_hash = None

        self.EOT_CHAR = 0x04 .to_bytes(1, "big")

        self.info = {}

        save_connected_node(host, port, id)

    def send(self, data, encoding_type="utf-8"):

        if isinstance(data, str):
            self.sock.sendall(data.encode(encoding_type) + self.EOT_CHAR)

        elif isinstance(data, dict):
            try:
                json_data = json.dumps(data)
                json_data = json_data.encode(encoding_type) + self.EOT_CHAR
                self.sock.sendall(json_data)

            except TypeError:
                print("Invalid json")

            except:
                print("Unexpected error while sending")

        elif isinstance(data, bytes):
            bin_data = data + self.EOT_CHAR
            self.sock.sendall(bin_data)

        else:
            print("invalid data type")

    def stop(self):
        self.terminate_flag.set()

    def parse_packet(self, packet):
        try:
            packet_decoded = packet.decode("utf-8")

            try:
                return json.loads(packet_decoded)

            except json.decoder.JSONDecodeError:
                return packet_decoded

        except UnicodeDecodeError:
            return packet

    def run(self):
        self.sock.settimeout(10.0)
        buffer = b""

        while not self.terminate_flag.is_set():
            chunk = b""

            try:
                chunk = self.sock.recv(4096)

            except socket.timeout:
                print("socket timeout")

            except:
                self.terminate_flag.set()
                print("Node System: Unexpected error")

            if chunk != b"":
                buffer += chunk
                eot_pos = buffer.find(self.EOT_CHAR)

                while eot_pos > 0:
                    packet = buffer[:eot_pos]
                    buffer = buffer[eot_pos + 1 :]

                    self.main_node.message_count_recv += 1
                    self.main_node.message_from_node(self, self.parse_packet(packet))

                    eot_pos = buffer.find(self.EOT_CHAR)

            time.sleep(0.01)

        self.sock.settimeout(None)
        self.sock.close()

    def set_info(self, key, value):
        self.info[key] = value

    def get_info(self, key):
        return self.info[key]
