import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .node import Node

from tcoin.constants import SCHEDULING_RATE
from tcoin.tangle.messages import Message

from .threaded import Threaded


class Scheduler(Threaded):
    def __init__(self, node: "Node"):
        super().__init__()

        self.node = node

        self.queue: dict[
            str, dict[str, dict[str, Message]]
        ] = {}  # {node_id: [message, ...]}

    def queue_msg(self, msg: Message):
        node_queue = self.queue.get(msg.node_id, {})

        node_queue[msg.hash] = msg

        self.queue[msg.node_id] = node_queue

    def get_next_node(self) -> str:
        # Chossing node based on the balance / amount
        return max(
            self.queue.keys(),
            key=lambda n: len(self.queue[n]) / self.node.tangle.get_balance(n),
        )

    def get_next_message(self) -> Message:
        msgs = self.queue[self.get_next_node()]

        # Getting the oldest message
        oldest_msg = sorted(msgs.values(), key=lambda m: m.timestamp)[0]

        return oldest_msg

    def process_next_message(self):
        msg = self.get_next_message()

        # Processing the message
        self.node.add_msg_from_queue(msg)

        # Unqueueing the message
        del self.queue[msg.node_id][msg.hash]

        if self.queue[msg.node_id] == {}:
            del self.queue[msg.node_id]

    def run(self):
        while not self.terminate_flag.is_set():
            if self.queue:
                self.process_next_message()

            time.sleep(SCHEDULING_RATE)
