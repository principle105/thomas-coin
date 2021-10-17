import os
import time
import _pickle as pickle
from wallet import Wallet
from .transaction import Transaction
from .block import Block
from config import BLOCK_PATH
from constants import GENESIS_BLOCK_DATA
from .state import State


def get_block_data():
    if not os.path.exists(BLOCK_PATH):
        return False

    with open(BLOCK_PATH, "rb") as f:
        return pickle.load(f)


def dump_block_data(data: "Blockchain"):
    with open(BLOCK_PATH, "wb") as f:
        pickle.dump(data, f, protocol=2)


class Blockchain:
    def __init__(self, pruned: bool = False):

        self.pruned = pruned

        # Keeps track of various stats
        self.state = State()

        # Blocks that are pending to be added to the blockchain
        self.pending: list[Block] = []

        # Adding the genesis block
        self.blocks = []
        self.add_block(self.get_genesis_block(), False)

    def add_block(self, block: Block, validate: bool = True, save: bool = True):
        if validate:
            # Checking if the block is valid
            if block.validate(self.state) is False:
                return False

        # Removing the block transactions from pending
        for t in block.transactions:
            if t in self.pending:
                self.pending.remove(t)

        self.state.add_block(block)

        if self.pruned:
            self.blocks = [block]
        else:
            self.blocks.append(block)

        if save:
            # Saving the blockchain locally
            self.save_locally()

        return True

    def validate(self):
        for block in self.blocks:
            if block.validate(self.state) is False:
                return False
        return True

    def get_genesis_block(self):
        return Block.from_json(**GENESIS_BLOCK_DATA)

    def get_json(self):
        blocks = []
        for b in self.blocks:
            blocks.append(b.get_json())

        return blocks

    def save_locally(self):
        dump_block_data(self)

    def add_pending(self, transaction: Transaction):
        # Making sure the transaction is valid

        if transaction.validate(self.state) is False:
            return False

        json_t = transaction.get_json()

        if json_t in self.pending:
            return False

        # Incrementing the nonce
        wallet = self.state.get_wallet(transaction.sender)
        wallet.nonce += 1

        # Saving as json to allow for checking duplicates (doesn't work with classes)
        self.pending.append(json_t)

        return True

    @classmethod
    def from_local(cls):
        prev_chain = get_block_data()

        if prev_chain is False:
            return cls()

        return prev_chain

    @classmethod
    def from_json(cls, blocks: list, validate: bool = False):
        chain = cls()

        for b in blocks:
            block = Block.from_json(**b)
            chain.add_block(block, validate)

        return chain

    def create_trans(self, sender: Wallet, receiver: str, amount: float, tip: float):
        wallet = self.state.get_wallet(sender.address)

        # Nonce increment for pending transactions
        extra = sum(x["sender"] == wallet.nonce for x in self.pending)

        t = Transaction(
            sender=sender.address,
            receiver=receiver,
            amount=float(amount),
            tip=float(tip),
            nonce=wallet.nonce + extra + 1,
        )
        t.sign(sender)
        return t

    def get_balance(self, address: str):
        # Using get instead of get_wallet method to prevent from creating new wallet in storage
        wallet = self.state.wallets.get(address, None)

        bal = 0 if wallet is None else wallet.balance

        for p in self.pending:
            # Only using sender because wallet cannot use output that it hasn't received yet
            if p["sender"] == address:
                bal -= p["amount"]

        return bal

    # Based off: https://github.com/ethereum/EIPs/blob/master/EIPS/eip-2.md
    def calculate_next_difficulty(self) -> int:
        """Calculates the difficulty of the next block"""
        return int(
            self.state.last_block.difficulty
            + self.state.last_block.difficulty
            // 2048
            * max(1 - (time.time() - self.state.last_block.timestamp) // 10, -99)
            + int(2 ** ((self.state.length // 100000) - 2))
        )
