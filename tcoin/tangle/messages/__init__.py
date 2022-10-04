from tcoin.constants import GENESIS_MSG_DATA

from .message import Message, SignedPayload, generate_message_lookup
from .transaction import Transaction, TransactionPayload

# All the transaction types
message_types = (Transaction,)

message_lookup = generate_message_lookup(message_types)

# Genesis message object
genesis_msg = message_lookup(GENESIS_MSG_DATA)

if genesis_msg is None:
    raise ValueError("Invalid genesis message")
