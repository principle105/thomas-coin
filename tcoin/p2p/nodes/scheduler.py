import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .node import Node

from typing import Literal

from tcoin.constants import PENDING_THRESHOLD, PENDING_WINDOW, SCHEDULING_RATE
from tcoin.tangle.messages import Message

from .threaded import Threaded


class PendingMessage:
    def __init__(
        self,
        msg: Message,
        missing: dict[str, dict[str, Literal[False] | Message | None]],
    ):
        self.msg = msg
        self.missing = missing  # {msg_id: {node_id: vote / msg}}

        self.creation = time.time()

    def add_vote(self, node_id: str, msg_id: str, msg: Message | None):
        self.missing[msg_id][node_id] = False if msg is None else msg

    def update_missing(self, node: "Node", scheduler: "Scheduler"):
        decide_now = time.time() > self.creation + PENDING_WINDOW

        for _id, v in list(self.missing.items()):
            if not v:
                continue

            if _id in scheduler.p_pending:
                # Trying to update the missing parent
                remove = scheduler.update_missing(scheduler.p_pending[_id])

                if remove:
                    del self.missing[_id]

                continue

            if _id in node.tangle.all_msgs:
                del self.missing[_id]
                continue

            # Making sure it has at least one vote
            if not any(v.values()):
                continue

            score = sum(
                node.get_rep(n_id) * (1 if v else -1) for n_id, v in v.items()
            )

            if decide_now:
                is_valid = bool(score)
            else:
                is_valid = score >= PENDING_THRESHOLD

            # Getting the message with the highest score
            msgs: dict[str, Message] = {}
            scores: dict[str, int] = {}

            for n_id, m in v.items():
                if not m:
                    continue

                scores[m.hash] = scores.get(m.hash, 0) + node.get_rep(n_id)
                msgs[m.hash] = m

            final_msg = msgs[max(scores, key=scores.get)]

            if is_valid:
                # Adding parent to the tangle
                scheduler.queue_msg(final_msg)
                del self.missing[_id]

                continue

            invalid_decided = decide_now or score <= -PENDING_THRESHOLD

            if not invalid_decided:
                continue

            # Adding main state's invalid message pool
            node.tangle.state.add_invalid_msg(v)

        if not self.missing:
            node.handle_new_message(self.msg.to_dict())
            return True

        scheduler.update_pending(self, update=False)
        return False


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
        remove = pending.update_missing(self.node, self)

        if remove:
            del self.p_pending[pending.msg.hash]

        return remove

    def add_vote(
        self,
        pending: PendingMessage,
        node_id: str,
        msg_id: str,
        msg: Message | None,
    ):
        pending.add_vote(node_id, msg_id, msg)

        if msg is not None:
            self.add_pending(msg, list(msg.parents))
            self.update_pending()

        self.update_missing(pending)

    def update_pending(self, pending: PendingMessage, update=True):
        self.p_pending[pending.msg.hash] = pending

        if update:
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
