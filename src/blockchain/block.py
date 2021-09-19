import time
import json
import ecdsa
from ecdsa.curves import SECP256k1
from transaction import Transaction
from wallet import Wallet
from constants import GENESIS_BLOCK_DATA
from hashlib import sha256
from base64 import b64encode, b64decode
from typing import TYPE_CHECKING

# To avoid circular imports
if TYPE_CHECKING:
    from blockchain import Blockchain


class Block:
    def __init__(
        self,
        index: int,
        prev: str,
        forger: str = None,
        timestamp: float = None,
        transactions: list[Transaction] = [],
        signature: str = None,
        hash: str = None,
    ):
        if timestamp is None:
            timestamp = time.time()

        self.index = index
        self.prev = prev
        # Public key of block forger
        self.forger = forger
        self.timestamp = timestamp
        self.transactions = transactions
        self.signature = signature

        if hash is None:
            hash = self.get_hash()

        self.hash = hash

    def get_raw_data(self):
        data = {
            "index": self.index,
            "prev": self.prev,
            "forger": self.forger,
            "timestamp": self.timestamp,
            "transactions": self.get_transactions_as_json(),
        }
        return data

    def get_transactions_as_json(self):
        data = sorted(
            [t.get_json() for t in self.transactions], key=lambda t: t["timestamp"]
        )
        return data

    def get_hash(self) -> None:
        data = self.get_raw_data()
        block_string = json.dumps(data, sort_keys=True).encode()
        return sha256(block_string).hexdigest()

    def get_json(self):
        data = self.get_raw_data()
        return {
            **data,
            "hash": self.hash,
            "signature": self.signature,
        }

    def append_transaction(self, transaction: Transaction):
        self.transactions.append(transaction)

    @property
    def forger_verifying_key(self) -> ecdsa.VerifyingKey:
        public_key = bytes.fromhex(self.forger)
        return ecdsa.VerifyingKey.from_string(public_key, curve=SECP256k1)

    def is_signature_verified(self) -> bool:
        """Checks if the block signature is valid"""
        try:
            return self.forger_verifying_key.verify(
                b64decode(self.signature.encode()), self.hash.encode()
            )
        except ecdsa.BadSignatureError:
            return False

    def sign(self, forger: Wallet):
        self.forger = forger.public_key
        self.signature = b64encode(forger.sk.sign(self.hash.encode())).decode()

    def validate(self, chain: "Blockchain"):
        """
        chain: blockchain object
        """

        # Checking if the block has a signature
        if self.signature is None:
            raise Exception("The block is not signed")

        # Checking if the block has a forger
        if self.forger is None:
            raise Exception("Block does not have a forger")

        chain_length = len(chain.chain)
        if chain_length == 0:
            raise Exception("Chain is empty")

        # Checking if the block is the genesis block
        if self.index == chain_length - 1 == 0:
            # Checking if the genesis block is valid
            if self.get_json() != GENESIS_BLOCK_DATA:
                raise Exception("Genesis block is not valid")

            return

        # Checking if the block comes after the last block in the chain
        if self.index != chain_length:
            raise Exception("Incorrect block index")

        # Checking the previous hash
        if self.prev != chain.chain[-1].hash:
            raise Exception("Previous hash does not match")

        # Checking if signature is verified
        if self.is_signature_verified() is False:
            raise Exception("Invalid block signature")

        # Validating each traqnsaction
        for t in self.transactions:
            t.validate(chain)

    @classmethod
    def from_json(
        cls, index, prev, forger, timestamp, transactions: list, signature, hash
    ):
        transactions = list(map(lambda t: Transaction.from_json(**t), transactions))
        return cls(
            index=index,
            prev=prev,
            forger=forger,
            timestamp=timestamp,
            transactions=transactions,
            signature=signature,
            hash=hash,
        )
