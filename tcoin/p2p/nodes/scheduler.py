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

        self.scores = {}  # {node_id: score}

    def queue_msg(self, msg: Message):
        node_queue = self.queue.get(msg.node_id, {})

        node_queue[msg.hash] = msg

        self.queue[msg.node_id] = node_queue

        self.update_score(msg.node_id)

    def update_score(self, node_id: str):
        if node_id not in self.queue:
            if node_id in self.scores:
                del self.scores[node_id]
            return

        now = time.time()

        # Disregarding messages with timestamps in the future
        valid_msgs = sum(
            1 for m in self.queue[node_id].values() if m.timestamp <= now
        )

        if valid_msgs == 0:
            del self.scores[node_id]
            return

        score = self.node.tangle.get_balance(node_id) / valid_msgs

        self.scores[node_id] = score

    def get_next_message(self) -> Message:
        node_id = max(self.scores)

        msgs = self.queue[node_id]

        # Getting the oldest message
        oldest_msg = sorted(msgs.values(), key=lambda m: m.timestamp)[0]

        return oldest_msg

    def process_next_message(self):
        msg = self.get_next_message()

        # Unqueueing the message
        del self.queue[msg.node_id][msg.hash]

        if self.queue[msg.node_id] == {}:
            del self.queue[msg.node_id]

        # Processing the message
        self.node.add_new_msg(msg)

        self.update_score(msg.node_id)

    def run(self):
        while not self.terminate_flag.is_set():
            if self.scores:
                self.process_next_message()

            time.sleep(SCHEDULING_RATE)
