import time
import json
import ecdsa
from wallet import Wallet
from constants import (
    GENESIS_BLOCK_DATA,
    MAX_BLOCK_SIZE,
    ISSUE_CHANGE_INTERVAL,
    MAX_COINS,
    CURVE,
)
from hashlib import sha256
from base64 import b64encode, b64decode
from base58 import b58decode
from typing import TYPE_CHECKING
from .transaction import Transaction

# To avoid circular imports
if TYPE_CHECKING:
    from .state import State


class Block:
    def __init__(
        self,
        index: int,
        prev: str,
        forger: str,
        difficulty: int,
        timestamp: float = None,
        reward: float = None,
        transactions: list[Transaction] = [],
        signature: str = None,
        hash: str = None,
    ):
        if timestamp is None:
            timestamp = time.time()

        self.index = index
        self.prev = prev

        # Address of block forger
        self.forger = forger

        self.timestamp = timestamp

        self.transactions = transactions

        self.difficulty = difficulty

        if reward is None:
            reward = self.calculate_reward()

        self.reward = reward

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
            "difficulty": self.difficulty,
            "reward": self.reward,
            "transactions": self.get_transactions_as_json(),
        }
        return data

    def get_transactions_as_json(self):
        data = sorted(
            [t.get_json() for t in self.transactions], key=lambda t: t["nonce"]
        )
        return data

    def get_hash(self) -> None:
        data = self.get_raw_data()
        block_string = json.dumps(data, sort_keys=True).encode()
        return sha256(block_string).hexdigest()

    def get_json(self):
        """Converts the block into json"""
        data = self.get_raw_data()
        return {
            **data,
            "hash": self.hash,
            "signature": self.signature,
        }

    @property
    def forger_vk(self) -> ecdsa.VerifyingKey:
        return ecdsa.VerifyingKey.from_string(b58decode(self.forger[1:]), curve=CURVE)

    def is_signature_verified(self) -> bool:
        """Checks if the block signature is valid"""
        try:
            return self.forger_vk.verify(
                b64decode(self.signature.encode()), self.hash.encode()
            )
        except ecdsa.BadSignatureError:
            return False

    def sign(self, forger: Wallet):
        self.signature = b64encode(forger.sk.sign(self.hash.encode())).decode()

    def validate(self, chain_state: "State"):
        """Validates the block"""

        # Checking the type
        if not all(isinstance(i, int) for i in [self.difficulty, self.index]):
            return False

        if not all(isinstance(i, float) for i in [self.timestamp, self.reward]):
            return False

        if not all(
            isinstance(i, str)
            for i in [self.prev, self.forger, self.signature, self.hash]
        ):
            return False

        if not isinstance(self.transactions, list):
            return False

        # Checking if chain state doesn't contain genesis
        if chain_state.length == 0:
            return False

        # Checking if the block is the genesis block
        if self.index == chain_state.length - 1 == 0:
            # Checking if the genesis block is valid
            if self.get_json() != GENESIS_BLOCK_DATA:
                return False
            return False

        # Checking if the block has a signature
        if not self.signature:
            return False

        # Checking if the block difficulty is correct
        if chain_state.calculate_next_difficulty() != self.difficulty:
            return False

        # Checking if reward amount is correct
        if self.reward != self.calculate_reward():
            return False

        # Checking if the block comes after the last block in the chain
        if self.index != chain_state.length:
            return False

        # Checking if the timestamp is valid
        # If timestamp is over 1 minute before last block was created
        if self.timestamp + 60 < chain_state.last_block.timestamp:
            return False

        # Checking the previous hash
        if self.prev != chain_state.last_block.hash:
            return False

        # Checking if signature is verified and matches block data
        if self.is_signature_verified() is False:
            return False

        # Checking if block does not exceed max size
        if len(self.transactions) > MAX_BLOCK_SIZE:
            return False

        # Validating each transaction
        for t in self.transactions:
            if t.validate(chain_state) is False:
                return False

        return True

    # Based of bitcoin
    # Source: https://www.oreilly.com/library/view/mastering-bitcoin/9781491902639/ch08.html
    def calculate_reward(self):
        """Calculates the reward for the block forger"""
        if self.index == 0:
            return 0

        return (
            MAX_COINS
            / 2 ** ((self.index + 1) // ISSUE_CHANGE_INTERVAL + 1)
            / ISSUE_CHANGE_INTERVAL
        )

    @classmethod
    def from_json(
        cls,
        index: int,
        prev: str,
        forger: str,
        timestamp: float,
        reward: float,
        transactions: list,
        difficulty: int,
        signature: str,
        hash: str,
    ):
        transactions = list(map(lambda t: Transaction.from_json(**t), transactions))
        return cls(
            index=index,
            prev=prev,
            forger=forger,
            timestamp=timestamp,
            reward=reward,
            transactions=transactions,
            difficulty=difficulty,
            signature=signature,
            hash=hash,
        )
