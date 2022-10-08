import time
from typing import TYPE_CHECKING

from objsize import get_deep_size
from tcoin.constants import (
    MAX_MSG_SIZE,
    MAX_PARENT_AGE,
    MAX_PARENTS,
    MIN_STRONG_PARENTS,
)
from tcoin.utils import check_var_types, get_pow_hash, get_target, is_valid_hash, pow

from ..signed import Signed

if TYPE_CHECKING:
    from ..tangle import Tangle


def generate_message_lookup(msg_types: list["Message"]):
    lookup = {c.value: c for c in msg_types}

    def message_lookup(data: dict) -> Message | None:
        data = data.copy()

        msg_type = data.pop("value", None)

        if msg_type is None:
            return None

        # Finding the message by its value (id)
        msg_cls = lookup.get(msg_type, None)

        if msg_cls is None:
            return None

        try:
            msg_obj = msg_cls(**data)

        except Exception as e:
            return None

        else:
            return msg_obj

    return message_lookup


class SignedPayload(Signed):
    """
    value: str -- Identifier of type of message
    """

    value: str = ...

    def __init__(
        self,
        *,
        node_id: str,
        payload: dict,
        timestamp: int = None,
        hash: str = None,
        signature: str = None
    ):
        super().__init__(hash, signature)

        self.node_id = node_id

        self.payload = payload

        if timestamp is None:
            timestamp = int(time.time())

        self.timestamp = timestamp

    @property
    def address(self):
        return self.node_id

    def get_raw_data(self) -> str:
        return "".join(str(s) for s in self.meta_data.values())

    @property
    def meta_data(self) -> dict:
        return {
            "node_id": self.node_id,
            "value": self.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    def to_dict(self) -> dict:
        return {
            **self.meta_data,
            "hash": self.hash,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


class Message(SignedPayload):
    def __init__(
        self,
        *,
        node_id: str,
        payload: dict,
        parents: dict[str, bool] = [],
        nonce: int = None,
        timestamp: int = None,
        hash: str = None,
        signature: str = None
    ):
        super().__init__(
            node_id=node_id,
            payload=payload,
            timestamp=timestamp,
            hash=hash,
            signature=signature,
        )

        self.parents = parents

        self.nonce = nonce

    def update_state(self, tangle: "Tangle"):
        """Updates the tangle with a message"""
        ...

    def is_payload_valid(self, tangle: "Tangle") -> bool:
        ...

    def select_parents(self, tangle: "Tangle"):
        self.parents = tangle.state.select_tips()

    def do_work(self, tangle: "Tangle"):
        raw_data = self.get_raw_data()
        difficulty = tangle.get_difficulty(self)

        self.hash, self.nonce = pow(raw_data, difficulty)

    def is_valid(self, tangle: "Tangle", depth=2) -> bool:
        depth -= 1
        data = self.to_dict()

        # Transaction does not exceed the maximum size
        if get_deep_size(data) > MAX_MSG_SIZE:
            return False

        # Field type validation
        if (
            any(
                check_var_types(
                    (self.node_id, str),
                    (self.payload, dict),
                    (self.parents, dict),
                    (self.nonce, int),
                    (self.timestamp, int),
                    (self.hash, str),
                    (self.signature, str),
                )
            )
            is False
        ):

            return False

        from . import genesis_msg

        # Checking if the message is the genesis message
        if data == genesis_msg.to_dict():
            return True

        # Ensuring the timestamp is not before the genesis message
        if self.timestamp < genesis_msg.timestamp:
            return False

        # Ensuring the timestamp is not past 2 hours into the future
        if self.timestamp > time.time() + 60 * 60 * 2:
            return False

        raw_data = self.get_raw_data()

        # Checking if the hash matches the data
        if get_pow_hash(raw_data, self.nonce) != self.hash:
            return False

        target = get_target(tangle.get_difficulty(self))

        # Checking if enough work has been done
        if is_valid_hash(self.hash, target) is False:
            return False

        # Checking if the signature is valid
        if self.is_signature_valid is False:
            return False

        # Checking if there are enough strong parents
        if list(self.parents.values()).count(0) < MIN_STRONG_PARENTS:
            return False

        if len(self.parents) > MAX_PARENTS:
            return False

        invalid_parents = set()  # parents that are known to be invalid is a parent
        unknown_parents = set()  # parents that are not known to be valid or invalid

        # TODO: check if the graph is still acyclic

        if depth != 0:
            invalid, unknown = self.analyze_parents(tangle, depth)

            invalid_parents |= invalid
            unknown_parents |= unknown

        if invalid_parents or unknown_parents:
            return list(invalid_parents), list(unknown_parents)

        return True

    def analyze_parents(self, tangle: "Tangle", depth: int) -> bool:
        invalid_parents = set()
        unknown_parents = set()

        parent_range = range(0, MAX_PARENT_AGE + 1)

        # Checking the validity of each parent
        for p, t in self.parents.items():
            p_msg = tangle.get_msg(p)

            # Ignoring validation if the parent is weak
            if t == 1:
                # Checking if the parent is falsely weak
                if p_msg is not None:
                    invalid_parents.add(p)
                else:
                    continue

            if tangle.state.in_invalid_pool(p):
                invalid_parents.add(p)
                continue

            # Checking if the message exists on the tangle
            if p_msg is not None:

                from . import genesis_msg

                # Validating the parent's timestamp if it's not the genesis
                if (
                    p_msg.hash != genesis_msg.hash
                    and self.timestamp - p_msg.timestamp not in parent_range
                ):
                    invalid_parents.add(p)

                else:
                    # Checking the validity of the message
                    result = p_msg.is_valid(tangle, depth=depth)

                    # Checking if the parent is valid
                    if result is False:
                        invalid_parents.add(p)

                    elif result is not True:
                        invalid, unknown = result

                        invalid_parents |= invalid
                        unknown_parents |= unknown

            else:
                unknown_parents.add(p)

        return invalid_parents, unknown_parents

    @property
    def meta_data(self) -> dict:
        return {**super().meta_data, "parents": self.parents}

    def to_dict(self) -> dict:
        return {**super().to_dict(), "nonce": self.nonce}
