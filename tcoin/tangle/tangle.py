import random
import time
from functools import lru_cache
from typing import Callable

from tcoin.config import (
    invalid_msg_pool_purge_time,
    invalid_msg_pool_size,
    secure_storage,
)
from tcoin.constants import (
    BASE_DIFFICULTY,
    FINALITY_SCORE,
    GAMMA,
    MAIN_THRESHOLD,
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
        self,
        wallets: dict[str, int] = None,
        invalid_msg_pool: dict[str, int] = None,
    ):
        if wallets is None:
            wallets = {}

        if invalid_msg_pool is None:
            invalid_msg_pool = {}

        self.wallets = wallets  # address: balance

        self.invalid_msg_pool = (
            invalid_msg_pool  # hash: timestamp of last access
        )

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
            sorted(self.invalid_msg_pool, key=lambda m: m[1])[
                invalid_msg_pool_size:
            ]
        )

        return in_pool

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


class BranchReference:
    def __init__(self, branch: "Branch", manager: "BranchManager"):
        self.branch = branch
        self.manager = manager


class Branch:
    def __init__(
        self,
        founder: Message,
        msgs: dict[str, Message] = None,
        branches: dict[tuple[str, int], "BranchManager"] = None,
        state: "TangleState" = None,
    ):
        if msgs is None:
            msgs = {}

        if branches is None:
            branches = {}

        if state is None:
            state = TangleState()

        self.founder = founder
        self.msgs = msgs
        self.branches = branches
        self.state = state

        self.add_msg(founder)

    @property
    def id(self):
        return self.founder.hash

    @property
    def approval_weight(self):
        return sum(m.approval_weight for m in self.msgs.values())

    def find_children(self, msg: Message) -> dict[str, Message] | None:
        def _search(msg_ids: list[str]):
            results = {}
            for _id, m in self.msgs.items():
                if _id in msg_ids:
                    results[_id] = m

            if results:
                return _search(results)

            return {}

        return _search([msg.hash])

    def add_branch(self, branch: "BranchManager"):
        if self.id is None:
            self.id = branch.id

        self.branches[branch.id] = branch

    def find_new_duplicate(self, msg: Message):
        for _id, m in self.msgs.items():
            if _id == msg.id:
                return m

        return None

    def find_existing_duplicate(self, msg: Message):
        for _id in self.branches:
            if _id == msg.id:
                return _id

        return None

    def get_conflict_msgs(self, msg_hashes: set[str]) -> set[str]:
        # TODO: cache this
        shared_msgs = msg_hashes & set(self.msgs)

        for m in self.branches.values():
            for b in m.conflicts.values():
                shared_msgs |= b.get_conflict_msgs(msg_hashes)

        return shared_msgs

    @property
    def is_final(self):
        return self.approval_weight >= FINALITY_SCORE

    def remove_msg(self, msg: Message):
        if msg.hash in self.msgs:
            del self.msgs[msg.hash]

            msg.update_state(self.state, add=False)

    def add_msgs(self, data: list[Message]):
        for d in data:
            self.add_msg(d)

    def add_msg(self, msg: Message, invalid_parents: list[str] = []):
        # TODO: add support for weak parents
        self.msgs[msg.hash] = msg

        msg.update_state(self.state)

    def to_dict(self):
        return {
            "founder": self.founder.to_dict(),
            "msgs": [m.to_dict() for m in self.msgs.values()],
            "branches": [b.to_dict() for b in self.branches.values()],
        }

    @classmethod
    def from_dict(cls, data: dict):
        founder_msg = Message.from_dict(data["founder"])

        branch = cls(founder_msg)

        for msg in data["msgs"]:
            msg = message_lookup(msg)

            if msg is None:
                continue

            branch.add_msg(msg)

        for b in data["branches"]:
            m = BranchManager.from_dict(b)

            branch.add_branch(m)

        return branch


class BranchManager:
    def __init__(
        self,
        node_id: str,
        index: int,
        main_branch: Branch,
        conflicts: dict[str, Branch] = None,
        nesting: list[list[str]] = None,
    ):
        if conflicts is None:
            conflicts = {}

        if nesting is None:
            nesting = []

        self.node_id = node_id
        self.index = index

        self.conflicts = conflicts
        self.main_branch = main_branch

        self.nesting = nesting

    def add_conflict(self, branch: Branch):
        self.conflicts[branch.id] = branch

    def remove_conflict(self, branch: Branch):
        if branch.id in self.conflicts:
            del self.conflicts[branch.id]

    def get_heaviest_branch(self):
        heaviest = max(
            self.conflicts.values(), key=lambda c: c.approval_weight
        )

        if self.main_branch.is_final:
            return None

        if heaviest.is_final:
            return heaviest

        if heaviest.approval_weight >= self.main_branch.approval_weight * (
            1 + MAIN_THRESHOLD
        ):
            return heaviest

        return None

    def update_conflict(self, tangle: "Tangle", branch: Branch):
        all_branch_msgs = set(branch.msgs)

        # Checking if the parents of each message are known
        for msg in branch.msgs.values():
            valid_parents = {_id for _id, t in msg.parents.items() if t == 0}

            if valid_parents - all_branch_msgs:
                return

        self.conflicts[branch.id] = branch

        # Findind the heaviest branch
        heaviest = self.get_heaviest_branch()

        if heaviest is None:
            return

        # Swapping the main branch with the heaviest branch
        self.remove_conflict(heaviest)
        self.add_conflict(self.main_branch)

        # Removing the main branch messages from the tangle
        for msg in self.main_branch.msgs.values():
            tangle.remove_msg(msg)

        # Updating the main branch
        self.main_branch = branch

        # Adding in reverse order so that each message has an existing parent
        for msg in list(branch.msgs.values())[::-1]:
            tangle.add_msg(msg)

        # Checking if the new main branches is final
        if self.main_branch.is_final:
            tangle.remove_branch(self.id)

    @property
    def id(self):
        return (self.node_id, self.index)

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "index": self.index,
            "conflicts": [c.to_dict() for c in self.conflicts.values()],
            "main_branch": self.main_branch.to_dict(),
            "nesting": self.nesting,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            node_id=data["node_id"],
            index=data["index"],
            conflicts=[Branch.from_dict(c) for c in data["conflicts"]],
            main_branch=Branch.from_dict(data["main_branch"]),
            nesting=data["nesting"],
        )


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

    def remove_msg(self, msg: Message):
        removed = True

        if msg.hash in self.msgs:
            del self.msgs[msg.hash]

        elif msg.hash in self.strong_tips:
            del self.strong_tips[msg.hash]

        elif msg.hash in self.weak_tips:
            del self.weak_tips[msg.hash]

        else:
            removed = False

        if removed:
            self.state.update_tx_on_tangle(msg, add=False)

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
        stop: Callable[[dict[str, Message]], bool] = None,
        total: dict[str, Message] = {},
    ) -> dict[str, Message]:
        # Recursively finding all the children
        children = {
            _id: m for _id, m in self.all_msgs.items() if msg_id in m.parents
        }

        total.update(children)

        if stop is not None:
            if stop(total):
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

    def find_msg_from_index(self, msg_id: tuple[str, int]) -> Message | None:
        return next(
            (m for m in self.all_msgs.values() if m.id == msg_id), None
        )

    def get_transaction_index(self, address: str) -> int:
        return sum(1 for m in self.all_msgs.values() if m.address == address)

    def find_occurs_in_branch(
        self, msg_hashes: set[str], branch_id: tuple[str, int] = None
    ) -> list[BranchReference]:
        """Finding all the branches that contain a set of messages"""

        if branch_id is None:
            occurs = []

            for _id in self.branches:
                occurs += self.find_occurs_in_branch(msg_hashes, branch_id=_id)

            return occurs

        manager = self.branches.get(branch_id, None)

        if manager is None:
            return []

        occurs = [
            BranchReference(b, manager)
            for b in manager.conflicts.values()
            if b.get_conflict_msgs(msg_hashes)
        ]

        return occurs

    def is_message_finalized(self, msg: Message):
        total_weight = 0

        def add_approval_weight(t: dict[str, Message]):
            nonlocal total_weight

            weight = sum(m.approval_weight for m in t.values())
            total_weight += weight

            return total_weight >= FINALITY_SCORE

        # Getting the total weight of the children
        self.find_children(msg.hash, stop=add_approval_weight)

        # Checking nif the weight makes the message final
        if total_weight >= FINALITY_SCORE:
            return True

        return False

    def _is_message_finalized(self, msg: Message, total: int = None):
        if total is None:
            total = 0

        for p in msg.parents:
            total

    def remove_branch(self, branch_id: tuple[str, int]):
        if branch_id in self.branches:
            del self.branches[branch_id]

    def find_duplicates_from_branches(
        self, msg: Message, parent_branches: list[BranchReference]
    ) -> bool:
        if not parent_branches:
            # Creating a new base branch
            duplicate = self.find_msg_from_index(msg.id)

            if duplicate:
                # Creating a new branch
                self.create_new_branch(msg, duplicate)

                return True

            return False

        # Finding the deepest parent branch manager
        deep_ref = max(parent_branches, key=lambda b: len(b.manager.nesting))

        duplicate = deep_ref.branch.find_existing_duplicate(msg)

        if duplicate:
            # Adding the to the branch
            branch = Branch(msg)
            deep_ref.branch.branches[msg.id].add_conflict(branch)

        else:
            duplicate = deep_ref.branch.find_new_duplicate(msg)

            if duplicate is None:
                return False

            # TODO: group the messages that are part of each branch
            children = deep_ref.branch.find_children(duplicate)

            # Removing the branches from the branch
            for p in children.values():
                deep_ref.branch.remove_msg(p)

            # Creating a branch from the duplicate
            c_branch = Branch(duplicate)
            c_branch.add_msgs(list(children.values()))

            # Creating the new branch
            branch = Branch(msg)

            new_nesting_layer = [deep_ref.manager.id, deep_ref.branch.id]

            manager = BranchManager(
                node_id=msg.node_id,
                index=msg.index,
                main_branch=c_branch,
                nesting=deep_ref.manager.nesting + [new_nesting_layer],
            )
            manager.add_conflict(branch)

            deep_ref.branch.add_branch(manager)

        # Updating the branch manager in the tangle
        self.update_branch_manager(deep_ref.manager)

        # Updating the branch in the manager
        deep_ref.manager.update_conflict(self, deep_ref.branch)

        return True

    def update_branch_manager(self, manager: BranchManager):
        def update(
            bm: dict[tuple[str, int], BranchManager], nest: list[list[str]]
        ):
            if len(nest):
                m, b = nest[0]

                bm[m].conflicts[b].branches = update(
                    bm[m].conflicts[b].branches, nest[1:], manager
                )
            else:
                bm[manager.id] = manager

            return bm

        self.branches = update(self.branches, manager.nesting)

    def get_state(self, ref: BranchReference):
        def get_branch_state(
            nest: list[list[str]],
            main: bool = False,
            state: TangleState = None,
        ):
            m, b = (
                nest[0] if len(nest) else ref.manager.id,
                ref.branch.id,
            )

            branch = self.branches[m].conflicts[b]

            new_branch = self.branches[m].main_branch if main else branch

            if state is None:
                state = new_branch.state
            else:
                state = state.merge(new_branch.state)

            if len(nest):
                return get_branch_state(branch.branches, nest[1:], state)

            return state

        branch_state = get_branch_state(ref.manager.nesting)
        main_state = get_branch_state(ref.manager.nesting, main=True)

        return self.state.merge(branch_state).merge(main_state, add=False)

    def create_new_branch(self, msg: Message, conflict: Message):
        if msg.id in self.branches:
            msg_ids = {
                msg.hash,
            }

            # Finding which conflicts the message is part of
            occurs = self.find_occurs_in_branch(msg_ids, branch_id=msg.id)

            if occurs == []:
                branch = Branch(msg)

                self.branches[msg.id].update_conflict(self, branch)

            return

        children = self.find_children(conflict.hash)

        branch, c_branch = Branch(msg), Branch(conflict)

        c_branch.add_msgs(list(children.values()))

        manager = BranchManager(
            node_id=msg.node_id, index=msg.index, main_branch=c_branch
        )
        manager.add_conflict(branch)

        self.branches[msg.id] = manager

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
        tangle_data = data.get("msgs", None)
        strong_tips_data = data.get("strong_tips", None)
        weak_tips_data = data.get("weak_tips", None)
        branch_data = data.get("branches", None)

        signature = data.get("signature", None)

        if None in [tangle_data, strong_tips_data, weak_tips_data]:
            return cls()

        if secure_storage:
            if signature is None:
                return cls()
        else:
            signature = None

        tangle = cls(signature=signature)

        # Adding the messages to the tangle
        for m_data in (
            list(reversed(tangle_data)) + strong_tips_data + weak_tips_data
        ):
            msg = message_lookup(m_data)

            if msg is None:
                continue

            if msg.hash in tangle.msgs:
                continue

            # Not validating the message as it is already in the tangle
            tangle.add_msg(msg)

        # Adding the branches
        tangle.branches = {
            (m := BranchManager.from_dict(b)).id: m for b in branch_data
        }

        tangle.add_hash()

        # Checking if the data was tampered
        if (
            secure_storage
            and Wallet.is_signature_valid(
                address=wallet.address,
                signature=tangle.signature,
                msg=tangle.hash,
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
