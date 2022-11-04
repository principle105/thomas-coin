from typing import TYPE_CHECKING

from tcoin.constants import MIN_SEND_AMT
from tcoin.utils import check_var_types

if TYPE_CHECKING:
    from tcoin.tangle import TangleState, Tangle

from .message import Message
from .payload import Payload


class TransactionPayload(Payload):
    def __init__(self, *, receiver: str, amt: int):

        self.receiver = receiver

        self.amt = amt

    def to_dict(self):
        return {"receiver": self.receiver, "amt": self.amt}


class Transaction(Message):
    value = "transaction"

    def get_transaction(self):
        return TransactionPayload.from_dict(self.payload)

    def is_payload_valid(self, state: "TangleState") -> bool:
        # Transaction form is valid
        try:
            t = self.get_transaction()
        except Exception:
            return False

        # Field type validation
        if any(check_var_types((t.amt, int), (t.receiver, str))) is False:
            return False

        # Making sure you aren't sending to yourself
        if self.node_id == t.receiver:
            return False

        if t.amt < MIN_SEND_AMT:
            return False

        balance = state.get_balance(self.node_id)

        # Checking if the sender has/had enough to send the transaction
        if balance < t.amt:
            return False

        return True

    def update_state(self, state: "TangleState"):
        state.update_tx_on_tangle(self)
