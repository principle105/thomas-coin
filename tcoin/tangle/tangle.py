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
        self, strong_tips: dict = {}, weak_tips: dict = {}, wallets: dict = {}
    ):
        self.strong_tips = strong_tips  # hash: timestamp
        self.weak_tips = weak_tips  # hash: timestamp

        self.wallets = wallets  # address: balance

        self.invalid_msg_pool = {}  # hash: timestamp of last access

    def add_invalid_msg(self, msg_hash: str):
        self.invalid_msg_pool[msg_hash] = time.time()

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

        return {
            _id: age
            for _id, age in tips.items()
            if age + MAX_TIP_AGE >= current_time or _id == genesis_msg.hash
        }

    @property
    def all_tips(self):
        return {**self.strong_tips, **self.weak_tips}

    def select_tips(self):
        # Purging tips that are too old
        self.strong_tips = self.purge_tips(self.strong_tips)
        self.weak_tips = self.purge_tips(self.weak_tips)

        if self.all_tips == []:
            return [genesis_msg.hash]

        amt = min(len(self.all_tips), MAX_PARENTS)

        tip_ids = random.sample(self.all_tips.keys(), amt)

        # Mapping the tips to their tip type
        return {_id: int(_id in self.weak_tips) for _id in tip_ids}

    def get_balance(self, address: str):
        return self.wallets.get(address, 0)

    def add_transaction(self, msg: Transaction):
        t = msg.get_transaction()

        sender_bal = self.get_balance(msg.node_id)
        receiver_bal = self.get_balance(t.receiver)

        # Checking if it is a genesis message
        if msg.node_id != "0":
            new_balance = sender_bal - t.amt

            if new_balance == 0:
                del self.wallets[msg.node_id]
            else:
                self.wallets[msg.node_id] = new_balance

        self.wallets[t.receiver] = receiver_bal + t.amt


class Tangle:
    def __init__(self, msgs: dict[str, Message] = {}, state: TangleState = None):
        if state is None:
            state = TangleState()

        self.state = state

        self.msgs = msgs

        if not self.msgs:
            self.add_msg(genesis_msg)

    @property
    def get_balance(self):
        return self.state.get_balance

    def add_msg(self, msg: Message, invalid_parents: list[str] = []):
        self.msgs[msg.hash] = msg

        # Updating the tangle with the message
        msg.update_state(self)

        # Only validating tips if the message does not contain invalid parents
        if not invalid_parents:
            for p, t in msg.parents.items():
                # Getting the total amount of children of the parent tip
                total_children = sum(1 for m in self.msgs.values() if p in m.parents)

                if total_children > 1:
                    if t == 0 and p in self.state.strong_tips:
                        del self.state.strong_tips[p]

                    elif t == 1 and p in self.state.weak_tips:
                        del self.state.weak_tips[p]

            self.state.strong_tips[msg.hash] = msg.timestamp

        else:
            # If there are invalid parents, the tip is added to the weak pool
            self.state.weak_tips[msg.hash] = msg.timestamp

    def get_msg(self, hash_str: str):
        return self.msgs.get(hash_str, None)

    def get_direct_children(self, msg_id: str) -> dict[str, Message]:
        if msg_id not in self.msgs:
            return None

        return {_id: m for _id, m in self.msgs.items() if msg_id in m.parents}

    def get_transaction_index(self, address: str) -> int:
        return sum(1 for m in self.msgs.values() if m.address == address)

    def find_msg_from_id(self, msg_id: str):
        if msg_id not in self.msgs:
            return None

        return self.msgs[msg_id]

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
