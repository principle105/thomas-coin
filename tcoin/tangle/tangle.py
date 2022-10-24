import random
import time
from functools import lru_cache

from tcoin.config import invalid_msg_pool_purge_time, invalid_msg_pool_size
from tcoin.constants import (
    BASE_DIFFICULTY,
    GAMMA,
    MAX_PARENTS,
    MAX_TIP_AGE,
    TIME_WINDOW,
)
from tcoin.utils import load_storage_file, save_storage_file

from .messages import Message, Transaction, genesis_msg, message_lookup

TANGLE_PATH = "tangle"


class TangleState:
    """Keeps track of the tangle's current state"""

    def __init__(
        self,
        strong_tips: dict[str, Message] = {},
        weak_tips: dict[str, Message] = {},
        wallets: dict[str, int] = {},
    ):
        self.strong_tips = strong_tips  # hash: msg
        self.weak_tips = weak_tips  # hash: msg

        self.wallets = wallets  # address: balance

        self.invalid_msg_pool: dict[str, int] = {}  # hash: timestamp of last access

    def add_invalid_msg(self, msg_hash: str):
        self.invalid_msg_pool[msg_hash] = int(time.time())

    def in_invalid_pool(self, msg_hash: str):
        in_pool = msg_hash in self.invalid_msg_pool

        if in_pool:
            # Updating the access time
            self.add_invalid_msg(msg_hash)

        # Purging invalid messages that haven't been accessed in a while
        self.invalid_msg_pool = {
            _id: t
            for _id, t in self.invalid_msg_pool.items()
            if t + invalid_msg_pool_purge_time >= time.time()
        }

        # Purging the oldest invalid messages
        self.invalid_msg_pool = dict(
            sorted(self.invalid_msg_pool, key=lambda m: m[1])[invalid_msg_pool_size:]
        )

        return in_pool

    def purge_tips(self, tips):
        current_time = time.time()

        purged_tips = {
            _id: msg
            for _id, msg in tips.items()
            if msg.timestamp + MAX_TIP_AGE >= current_time
        }

        # Checking for the genesis message only once per purge
        if genesis_msg.hash in tips:
            purged_tips[genesis_msg.hash] = tips[genesis_msg.hash]

        return purged_tips

    @property
    def all_tips(self):
        return {**self.strong_tips, **self.weak_tips}

    def select_tips(self):
        # Purging tips that are too old
        self.strong_tips = self.purge_tips(self.strong_tips)
        self.weak_tips = self.purge_tips(self.weak_tips)

        if self.all_tips == {}:
            return {genesis_msg.hash: 0}

        amt = min(len(self.all_tips), MAX_PARENTS)

        tip_ids = random.sample(self.all_tips.keys(), amt)

        # Mapping the tips to their tip type
        return {_id: int(_id in self.weak_tips) for _id in tip_ids}

    def get_raw_balance(self, address: str) -> list:
        return self.wallets.get(address, [])

    def get_balance(self, address: str):
        return self.wallets.get(address, 0)

    def add_transaction(self, msg: Transaction):
        t = msg.get_transaction()

        sender_bal = self.get_balance(msg.node_id) - t.amt
        receiver_bal = self.get_balance(t.receiver) + t.amt

        # Checking if it is a genesis message
        if msg.node_id != "0":
            if sender_bal == 0:
                del self.wallets[msg.node_id]
            else:
                self.wallets[msg.node_id] = sender_bal

        self.wallets[t.receiver] = receiver_bal


class Tangle:
    def __init__(
        self,
        msgs: dict[str, Message] = {},
        branches: dict[tuple[str, int], list[dict[str, Message]]] = {},
        state: TangleState = None,
    ):
        if state is None:
            state = TangleState()

        # State of the main tangle
        self.state = state

        # Main branch messages
        self.msgs = msgs

        # Conflicting branches
        self.branches = branches  # (node_id, index): [{msg_hash: Message, ...}, ...]

        if not self.msgs:
            self.add_msg(genesis_msg)

    @property
    def get_balance(self):
        return self.state.get_balance

    @property
    def all_msgs(self):
        return {**self.msgs, **self.state.all_tips}

    def add_approved_msg(self, msg: Message):
        self.msgs[msg.hash] = msg
        msg.update_state(self)

    def find_children(
        self,
        msg_id: str,
        *,
        stop: int = None,
        total: dict[str, Message] = {},
    ) -> list[Message]:
        # Recursively finding all the children

        children = {_id: m for _id, m in self.all_msgs.items() if msg_id in m.parents}

        total.update(children)

        if stop is not None:
            stop -= 1

            if stop == 0:
                return total

        for c in children:
            total = self.find_children(c, stop=stop, total=total)

        return total

    def add_msg(self, msg: Message, invalid_parents: list[str] = []):
        # Updating the state without approval if it's the genesis message
        if msg.hash == genesis_msg.hash:
            self.add_approved_msg(msg)
            return

        # Only validating tips if the message does not contain invalid parents
        if not invalid_parents:
            # The branches that the message is part of
            branches = []

            for p, t in msg.parents.items():
                if p == genesis_msg.hash:
                    continue

                p_msg: Message = self.get_msg(p)

                # Getting the total amount of children of the parent tip
                # TODO: cache the child count
                total_children = len(self.find_children(p))

                if total_children > 1:
                    if t == 0:
                        del self.state.strong_tips[p]

                    else:
                        del self.state.weak_tips[p]

                    self.add_approved_msg(p_msg)

                for _id in self.branches:
                    branches += self.find_occurs_in_branch(_id, p)

            if branches:
                ...

            self.state.strong_tips[msg.hash] = msg

        else:
            # If there are invalid parents, the tip is added to the weak pool
            self.state.weak_tips[msg.hash] = msg

    def get_msg(self, hash_str: str):
        msg = self.msgs.get(hash_str, None)

        if msg is not None:
            return msg

        return self.state.all_tips.get(hash_str, None)

    def get_direct_children(self, msg_id: str) -> dict[str, Message]:
        if msg_id not in self.msgs:
            return None

        return {_id: m for _id, m in self.msgs.items() if msg_id in m.parents}

    def find_msg_from_index(self, address: str, index: int) -> Message | None:
        return next(
            (
                m
                for m in self.all_msgs.values()
                if m.address == address and m.index == index
            ),
            None,
        )

    def get_transaction_index(self, address: str) -> int:
        return sum(1 for m in self.all_msgs.values() if m.address == address)

    def find_occurs_in_branch(self, branch_id: tuple[str, int], msg_id: str) -> list:
        occurs = [b for b in self.branches[branch_id] if msg_id in b]

        return occurs

    def create_new_branch(self, msg: Message, conflict: Message):
        branch_id = (msg.node_id, msg.index)

        if branch_id in self.branches:
            occurs = self.find_occurs_in_branch(branch_id, msg.hash)

            if occurs:
                return

            if occurs == []:
                self.branches[branch_id].append({msg.hash: msg})
                return

        # TODO: check if the conflicting branch is already finalized

        # Recursively finding the conflicting branch
        conflict_branch = {
            conflict.hash: conflict,
            **self.find_children(conflict.node_id),
        }

        self.branches[branch_id] = [
            {msg.hash: msg},
            {conflict.hash: conflict_branch},
        ]

    @lru_cache(maxsize=64)
    def get_difficulty(self, msg: Message):
        def _in_window(m):
            return (
                m.node_id == msg.node_id
                and m.timestamp > msg.timestamp - TIME_WINDOW
                and m.timestamp < msg.timestamp
            )

        # Amount of messages in the last time window
        msg_count = len(list(filter(_in_window, self.msgs.values())))

        return BASE_DIFFICULTY + int(GAMMA * msg_count)

    def get_msgs_as_dict(self):
        return [m.to_dict() for m in self.msgs.values()]

    @classmethod
    def from_dict(cls, tangle_data: list):
        tangle = cls()

        for m_data in reversed(tangle_data):
            msg = message_lookup(m_data)

            if msg is None:
                continue

            if msg.hash in tangle.msgs:
                continue

            # Not validating the message as it is already in the tangle
            tangle.add_msg(msg)

        return tangle

    def save(self):
        save_storage_file(TANGLE_PATH, self.get_msgs_as_dict())

    @classmethod
    def from_save(cls):
        tangle_data = load_storage_file(TANGLE_PATH)

        return cls.from_dict(tangle_data)
