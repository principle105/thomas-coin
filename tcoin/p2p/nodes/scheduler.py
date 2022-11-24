import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .node import Node

from typing import Literal

from tcoin.constants import SCHEDULING_RATE
from tcoin.tangle.messages import Message

from .threaded import Threaded


class PendingMessage:
    def __init__(
        self,
        msg: Message,
        missing: dict[str, dict[str, Literal[True] | Message | None]],
    ):
        self.msg = msg
        self.missing = missing  # {msg_id: {node_id: vote / msg}}

    def add_vote(self, node_id: str, msg_id: str, msg: Message | None):
        self.missing[msg_id][node_id] = False if msg is None else msg

    def update_missing(self, node: "Node"):
        not_verified = len(self.missing)

        for _id, v in self.missing.items():
            # TODO: check if at least every single parent has a vote
            # TODO: Look at votes on an individual basis for each parent

            if not v:
                continue

            if _id in node.tangle.all_msgs:
                not_verified -= 1
                continue

            # TODO: properly implement both of these
            is_valid = sum(1 for v in v.values() if v)
            final_msg = list(v.values())[0]

            if is_valid:
                # Adding parent to the tangle
                node.add_new_msg(final_msg)

                not_verified -= 1

                continue

            invalid_decided = False  # TODO: actually calculate this

            if not invalid_decided:
                continue

            # Adding main state's invalid message pool
            node.tangle.state.add_invalid_msg(v)

            not_verified += 1

        if not_verified == 0:
            node.handle_new_message(self.msg.to_dict())


class Scheduler(Threaded):
    def __init__(self, node: "Node"):
        super().__init__()

        self.node = node

        self.queue: dict[
            str, dict[str, dict[str, Message]]
        ] = {}  # {node_id: {msg_id: message}}

        # Pending parent messages
        self.p_pending: dict[
            str, PendingMessage
        ] = {}  # {msg_id: PendingMessage}

        self.scores = {}  # {node_id: score}

    def update_missing(self, pending: PendingMessage):
        remove = pending.update_missing(self.node)

        if remove:
            del self.p_pending[pending.msg.hash]

    def add_vote(
        self,
        pending: PendingMessage,
        node_id: str,
        msg_id: str,
        msg: Message | None,
    ):
        pending.add_vote(node_id, msg_id, msg)

        self.update_missing(pending)

    def update_pending(self, pending: PendingMessage):
        self.p_pending[pending.msg.hash] = pending

        self.update_missing(pending)

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

    def add_pending(self, msg: Message, missing: list[str]):
        p_msgs = self.p_pending.get(msg.hash, None)

        new_missing = {m: {} for m in missing}

        if p_msgs is None:
            pending = PendingMessage(msg=msg, missing=new_missing)

        else:
            p_msgs.missing = {**p_msgs.missing, **new_missing}
            pending = p_msgs

        self.update_pending(pending)

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
