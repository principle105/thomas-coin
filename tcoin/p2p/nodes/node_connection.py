import json
import logging
import socket
import time
import zlib
from base64 import b64decode, b64encode
from threading import Event, Thread
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .node import Node

EOT_CHAR = 0x04.to_bytes(1, "big")


class NodeConnection(Thread):
    def __init__(
        self, *, main_node: "Node", sock: socket.socket, id: str, host: str, port: int
    ):
        super().__init__()

        self.terminate_flag = Event()

        self.main_node = main_node

        self.host = host
        self.port = port

        self.id = id

        self.sock = sock

        self.sock.settimeout(10.0)

    def compress(self, data):
        return b64encode(zlib.compress(data, 6))

    def decompress(self, compressed):
        return zlib.decompress(b64decode(compressed))

    def send(self, data: dict):
        send_data = self.compress(json.dumps(data).encode()) + EOT_CHAR

        try:
            self.sock.sendall(send_data)
        except Exception:
            self.stop()

    def parse_packet(self, packet):
        packet = self.decompress(packet)

        try:
            data = packet.decode("utf-8")

            try:
                return json.loads(data)

            except json.decoder.JSONDecodeError:
                return data

        except UnicodeDecodeError:
            return packet

    def stop(self):
        self.terminate_flag.set()

    def run(self):
        buffer = b""

        while not self.terminate_flag.is_set():
            chunk = b""

            try:
                chunk = self.sock.recv(4096)

            except socket.timeout:
                logging.debug("Node timeout")

            except Exception as e:
                if not isinstance(e, ConnectionResetError):
                    logging.exception(e)

                self.terminate_flag.set()

            if chunk != b"":
                buffer += chunk
                eot_pos = buffer.find(EOT_CHAR)

                while eot_pos > 0:
                    packet = buffer[:eot_pos]
                    buffer = buffer[eot_pos + 1 :]

                    self.main_node.message_from_node(self, self.parse_packet(packet))

                    eot_pos = buffer.find(EOT_CHAR)

            time.sleep(0.01)

        self.sock.settimeout(None)
        self.sock.close()

        self.main_node.node_disconnected(self)

        logging.debug("Node connection stopped")
