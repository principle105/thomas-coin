import random
import time
from collections import Counter
from functools import lru_cache

from tcoin.config import invalid_msg_pool_purge_time, invalid_msg_pool_size
from tcoin.constants import (
    BASE_DIFFICULTY,
    GAMMA,
    MAX_PARENTS,
    MAX_TIP_AGE,
    TIME_WINDOW,
)
from tcoin.utils import get_raw_hash, load_storage_file, save_storage_file
from tcoin.wallet import Wallet

from .messages import Message, Transaction, genesis_msg, message_lookup
from .signed import Signed

TANGLE_PATH = "tangle"


class TangleState:
    """Keeps track of the tangle's current state"""

    def __init__(
        self, wallets: dict[str, int] = None, invalid_msg_pool: dict[str, int] = None
    ):
        if wallets is None:
            wallets = {}

        if invalid_msg_pool is None:
            invalid_msg_pool = {}

        self.wallets = wallets  # address: balance

        self.invalid_msg_pool = invalid_msg_pool  # hash: timestamp of last access

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

    def get_raw_balance(self, address: str) -> list:
        return self.wallets.get(address, [])

    def get_balance(self, address: str):
        return self.wallets.get(address, 0)

    def update_tx_on_tangle(self, msg: Transaction, add: bool = True):
        t = msg.get_transaction()

        # Simulating removing the transaction from the tangle
        if add is False:
            t.amt *= -1

        sender_bal = self.get_balance(msg.node_id) - t.amt
        receiver_bal = self.get_balance(t.receiver) + t.amt

        # Checking if it is a genesis message
        if msg.node_id != "0":
            if sender_bal == 0:
                del self.wallets[msg.node_id]
            else:
                self.wallets[msg.node_id] = sender_bal

        self.wallets[t.receiver] = receiver_bal

    def add_dict_states(self, x: dict, y: dict, add=True) -> dict:
        if add:
            return {k: x.get(k, 0) + y.get(k, 0) for k in x | y}

        return {k: x.get(k, 0) - y.get(k, 0) for k in x | y}

    def merge(self, state: "TangleState", add=True):
        # Merging the wallet states
        wallets = self.add_dict_states(self.wallets, state.wallets, add)

        # Merging the invalid message pool
        invalid_msg_pool = self.add_dict_states(
            self.invalid_msg_pool, state.invalid_msg_pool, add
        )

        return TangleState(wallets, invalid_msg_pool)


class Branch:
    def __init__(
        self,
        msgs: dict[str, Message] = None,
        state: "TangleState" = None,
    ):
        if msgs is None:
            msgs = {}

        if state is None:
            state = TangleState()

        self.msgs = msgs
        self.state = state

    def add_msgs(self, data: list[Message]):
        for d in data:
            self.add_msg(d)

    def add_msg(self, msg: Message, invalid_parents: list[str] = []):
        # TODO: add support for tips
        self.msgs[msg.hash] = msg

        msg.update_state(self.state)

    def to_dict(self):
        return {"msgs": [m.to_dict() for m in self.msgs.values()]}

    @classmethod
    def from_dict(cls, data: dict):
        branch = cls()

        for msg in data["msgs"]:
            msg = message_lookup(msg)

            if msg is None:
                continue

            branch.add_msg(msg)

        return branch


class BranchManager:
    def __init__(
        self, node_id: str, index: int, conflicts: list[Branch], main_branch: Branch
    ):
        self.node_id = node_id
        self.index = index

        self.conflicts = conflicts
        self.main_branch = main_branch

    def add_conflict(self, branch: Branch):
        self.conflicts.append(branch)

    @property
    def id(self):
        return (self.node_id, self.index)

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "index": self.index,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "main_branch": self.main_branch.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            node_id=data["node_id"],
            index=data["index"],
            conflicts=[Branch.from_dict(c) for c in data["conflicts"]],
            main_branch=Branch.from_dict(data["main_branch"]),
        )


class BranchReference:
    def __init__(self, branch: Branch, manager: BranchManager):
        self.branch = branch
        self.manager = manager


class Tangle(Signed):
    def __init__(
        self,
        *,
        msgs: dict[str, Message] = {},
        branches: dict[tuple[str, int], BranchManager] = {},
        strong_tips: dict[str, Message] = {},
        weak_tips: dict[str, Message] = {},
        state: TangleState = None,
        hash: str = None,
        signature: str = None,
    ):

        super().__init__(hash=hash, signature=signature)

        if state is None:
            state = TangleState()

        # State of the main tangle
        self.state = state

        self.strong_tips = strong_tips  # hash: msg
        self.weak_tips = weak_tips  # hash: msg

        # Main branch messages
        self.msgs = msgs

        # Conflicting branches
        self.branches = branches  # (node_id, index): BranchManager

        if not self.msgs:
            self.add_msg(genesis_msg)

    @property
    def all_tips(self):
        return {**self.strong_tips, **self.weak_tips}

    @property
    def all_msgs(self):
        return {**self.msgs, **self.all_tips}

    @property
    def get_balance(self):
        return self.state.get_balance

    def purge_tips(self, tips):
        current_time = time.time()

        valid_tips, invalid_tips = {}, {}

        for _id, msg in tips.items():
            if msg.timestamp + MAX_TIP_AGE >= current_time:
                valid_tips[_id] = msg
            else:
                invalid_tips[_id] = msg

        # Updating the state to reflect the removal of the invalid tips
        for _id, msg in invalid_tips.items():
            self.state.update_tx_on_tangle(msg, add=False)

        # Checking for the genesis message only once per purge
        if genesis_msg.hash in tips:
            valid_tips[genesis_msg.hash] = tips[genesis_msg.hash]

        return valid_tips

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

    def add_approved_msg(self, msg: Message):
        self.msgs[msg.hash] = msg
        msg.update_state(self.state)

    def find_children(
        self,
        msg_id: str,
        *,
        stop: int = None,
        total: dict[str, Message] = {},
    ) -> dict[str, Message]:
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
            for p, t in msg.parents.items():
                if p == genesis_msg.hash:
                    continue

                p_msg: Message = self.get_msg(p)

                if p in self.all_tips:
                    # Getting the total amount of children of the parent tip
                    # TODO: cache the child count
                    total_children = len(self.find_children(p))

                    if total_children > 1:
                        if t == 0:
                            del self.strong_tips[p]
                        else:
                            del self.weak_tips[p]

                        self.add_approved_msg(p_msg)

            self.strong_tips[msg.hash] = msg

        else:
            # If there are invalid parents, the tip is added to the weak pool
            self.weak_tips[msg.hash] = msg

        # Updating the state
        self.state.update_tx_on_tangle(msg)

    def get_msg(self, hash_str: str):
        msg = self.msgs.get(hash_str, None)

        if msg is not None:
            return msg

        return self.all_tips.get(hash_str, None)

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

    def find_occurs_in_branch(
        self, msg_ids: set[str], branch_id: tuple[str, int] = None
    ) -> list[BranchReference]:
        if branch_id is None:
            occurs = []

            for _id in self.branches:
                occurs += self.find_occurs_in_branch(msg_ids, _id)

            return occurs

        manager = self.branches.get(branch_id, None)

        if manager is None:
            return []

        occurs = [
            BranchReference(b, manager)
            for b in manager.conflicts
            if msg_ids & set(b.msgs)
        ]

        return occurs

    def create_new_branch(self, msg: Message, conflict: Message):
        branch_id = (msg.node_id, msg.index)

        if branch_id in self.branches:
            msg_ids = {
                msg.hash,
            }

            # Finding which conflicts the message is part of
            occurs = self.find_occurs_in_branch(msg_ids, branch_id=branch_id)

            if occurs:
                return

            if occurs == []:
                branch = Branch()
                branch.add_msg(msg)

                self.branches[branch_id].add_conflict(branch)

                return

        # TODO: check if the conflicting branch is already finalized

        children = self.find_children(conflict.node_id)

        # Recursively finding the conflicting branch
        conflict_branch = [conflict] + list(children.values())

        branch, c_branch = Branch(), Branch()

        branch.add_msg(msg)
        c_branch.add_msgs(conflict_branch)

        self.branches[branch_id] = BranchManager(
            node_id=msg.node_id,
            index=msg.index,
            conflicts=[branch],
            main_branch=c_branch,
        )

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

    def get_tips_as_dict(self, tips: dict[str, Message]):
        # Converts the tips to a dict
        return [msg.to_dict() for msg in tips.values()]

    def get_branches_as_dict(self):
        return [m.to_dict() for m in self.branches.values()]

    def to_dict(self):
        return {
            "msgs": self.get_msgs_as_dict(),
            "branches": self.get_branches_as_dict(),
            "strong_tips": self.get_tips_as_dict(self.strong_tips),
            "weak_tips": self.get_tips_as_dict(self.weak_tips),
            "signature": self.signature,
        }

    def add_hash(self):
        self.hash = get_raw_hash("".join(str(s) for s in self.to_dict()))

    @classmethod
    def from_dict(cls, data: dict, wallet: Wallet):
        # TODO: save the branches
        tangle_data = data.get("msgs", None)
        strong_tips_data = data.get("strong_tips", None)
        weak_tips_data = data.get("weak_tips", None)
        branch_data = data.get("branches", None)

        signature = data.get("signature", None)

        if None in (tangle_data, strong_tips_data, weak_tips_data, signature):
            return cls()

        tangle = cls(signature=signature)

        # Adding the messages to the tangle
        for m_data in list(reversed(tangle_data)) + strong_tips_data + weak_tips_data:
            msg = message_lookup(m_data)

            if msg is None:
                continue

            if msg.hash in tangle.msgs:
                continue

            # Not validating the message as it is already in the tangle
            tangle.add_msg(msg)

        # Adding the branches
        tangle.branches = {(m := BranchManager.from_dict(b)).id: m for b in branch_data}

        tangle.add_hash()

        # Checking if the data was tampered
        if (
            Wallet.is_signature_valid(
                address=wallet.address, signature=tangle.signature, msg=tangle.hash
            )
            is False
        ):
            return cls()

        return tangle

    def save(self, wallet: Wallet):
        # Signing the tangle to prevent tampering
        self.add_hash()
        self.sign(wallet)

        # Saving the tangle to a file
        save_storage_file(TANGLE_PATH, self.to_dict())

    @classmethod
    def from_save(cls, wallet: Wallet):
        tangle_data = load_storage_file(TANGLE_PATH)

        return cls.from_dict(tangle_data, wallet)
