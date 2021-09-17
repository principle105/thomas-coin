import time
import json
import ecdsa
from ecdsa.curves import SECP256k1
from transaction import Transaction
from config import GENESIS_PUBLIC_KEY
from hashlib import sha256
from base64 import b64encode

class Block:
    def __init__(
        self,
        index: str,
        prev: str,
        forger: str = None,
        timestamp: str = None,
        transactions: list[Transaction] = [],
        signature: str = None,
        hash: str = None,
    ):
        if timestamp is None:
            timestamp = str(time.time())

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
            [t.get_json() for t in self.transactions], key=lambda t: t["amount"]
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
            "signature": b64encode(self.signature).decode(),
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
            return self.forger_verifying_key.verify(self.signature, self.hash.encode())
        except ecdsa.BadSignatureError:
            return False

    def create_signature(self, forger_private_address: str):

        forger_private_key_string = bytes.fromhex(forger_private_address)
        forger_private_key = ecdsa.SigningKey.from_string(
            forger_private_key_string, curve=SECP256k1
        )

        if forger_private_key.get_verifying_key() != self.forger_public_key:
            raise Exception("Keys do not match")
        self.signature = self.sign(forger_private_key)

    def sign(self, forger_private_key: ecdsa.SigningKey):
        self.signature = forger_private_key.sign(self.hash.encode())

    def validate(self, chain):
        chain_length = len(chain)
        # Checking if the block is the genesis block
        if self.index == chain_length - 1 == 0:
            # Checking if the genesis block is valid
            if (
                self.forger != GENESIS_PUBLIC_KEY
                or self.is_signature_verified() is False
            ):
                raise Exception("Genesis block not valid")

            return

        # Checking if the block comes after the last block in the chain
        if self.index != chain_length:
            raise Exception("Incorrect block index")

        # Checking the previous hash
        if self.prev != chain.blocks[-1]:
            raise Exception("Previous hash does not match")

        # Checking if signature is verified
        if self.is_signature_verified() is False:
            raise Exception("Invalid block signature")

        # Checking if each transaction is valid
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
