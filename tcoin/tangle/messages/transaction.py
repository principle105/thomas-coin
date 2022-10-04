from typing import TYPE_CHECKING

from tcoin.constants import MIN_SEND_AMT
from tcoin.utils import check_var_types

if TYPE_CHECKING:
    from tcoin.tangle import Tangle

from .message import Message
from .payload import Payload


class TransactionPayload(Payload):
    def __init__(self, *, receiver: str, amt: int, index: int):

        self.receiver = receiver

        self.amt = amt

        self.index = index

    def to_dict(self):
        return {
            "receiver": self.receiver,
            "amt": self.amt,
            "index": self.index,
        }


class Transaction(Message):
    value = "transaction"

    def get_transaction(self):
        return TransactionPayload.from_dict(self.payload)

    def is_payload_valid(self, tangle: "Tangle") -> bool:
        # Transaction form is valid
        try:
            t = self.get_transaction()
        except Exception:
            return False

        # Field type validation
        if (
            any(check_var_types((t.amt, int), (t.receiver, str), (t.index, int)))
            is False
        ):
            return False

        # Making sure you aren't sending to yourself
        if self.node_id == t.receiver:
            return False

        index = tangle.get_transaction_index(self.node_id)

        # Checking if the transaction index is correct
        if index != t.index:
            return False

        if t.amt < MIN_SEND_AMT:
            return False

        balance = tangle.get_balance(self.node_id)

        # Checking if the sender has/had enough to send the transaction
        if balance < t.amt:
            return False

        return True

    def update_state(self, tangle: "Tangle"):
        tangle.state.add_transaction(self)
