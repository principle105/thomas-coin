import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .node import Node

from tcoin.constants import SCHEDULING_RATE
from tcoin.tangle.messages import Message

from .threaded import Threaded


class Scheduler(Threaded):
    def __init__(self, node: "Node"):
        self.node = node

        self.queue: dict[
            str, dict[str, list[Message]]
        ] = {}  # {node_id: [message, ...]}

    def queue_msg(self, msg: Message):
        ...

    def get_next_node(self):
        ...

    def get_next_message(self) -> Message:
        # TODO: Choose node based on the balance / amount of messages
        ...

    def process_next_message(self):
        msg = self.get_next_message()

        # Processing the message
        self.node.add_msg_from_queue(msg)

        # Unqueueing the message
        del self.queue[msg.node_id][msg.hash]

    def run(self):
        while not self.terminate_flag.is_set():
            self.process_queue()
            time.sleep(SCHEDULING_RATE)
