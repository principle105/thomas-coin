import os
import _pickle as pickle
from itertools import islice
from wallet import Wallet
from .transaction import Transaction
from .block import Block
from .state import State
from config import BLOCK_PATH
from constants import GENESIS_BLOCK_DATA, MAX_BLOCK_SIZE


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

        # Blocks that are pending to be added to the blockchain
        self.pending: list[Block] = []

        # Keeps track of various stats
        self.state = State()

        # Adding the genesis block
        self.blocks = []
        self.add_block(self.get_genesis_block(), save=False)

    def add_block(self, block: Block, validate: bool = True, save: bool = True):

        if validate:
            # Checking if the block is valid
            if block.validate(self.state) is False:
                return False

        # Removing the block transactions from pending
        for t in block.transactions:
            if (tj := t.get_json()) in self.pending:
                self.pending.remove(tj)

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

        # Saving as json to allow for checking duplicates (doesn't work with classes)
        self.pending.append(json_t)

        return True

    @classmethod
    def from_local(cls):
        prev_chain = get_block_data()

        # Not revalidating because of pruned nodes
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
                bal -= p["amount"] + p["tip"]

        return bal

    def fetch_transactions(self, count: int = MAX_BLOCK_SIZE):
        count = min(count, len(self.pending))
        return sorted(
            islice(
                sorted(
                    self.pending,
                    key=lambda t: t["tip"],
                    reverse=True,
                ),
                count,
            ),
            key=lambda t: t["nonce"],
        )

    def convert_tx_to_objects(self, transaction: list[dict]) -> list[Transaction]:
        txs = []
        for t in transaction:
            txs.append(Transaction.from_json(**t))

        return txs

    def create_new_block(self, forger: str):
        """Creates a new unsigned block from pending transactions"""
        last_block = self.state.last_block

        transactions = self.convert_tx_to_objects(
            list(self.fetch_transactions(MAX_BLOCK_SIZE))
        )

        difficulty = self.state.calculate_next_difficulty()

        block = Block(
            index=last_block.index + 1,
            prev=last_block.hash,
            forger=forger,
            transactions=transactions,
            difficulty=difficulty,
        )

        return block

    def forge_block(self, wallet: Wallet):
        # Creating an unsigned block
        block = self.create_new_block(wallet.address)

        # Signing the block
        block.sign(wallet)

        # Adding it to our chain
        if self.add_block(block):
            return block

        return None

    def add_stake(self, staker):
        if staker.validate(self.state):
            self.state.validators[staker.address] = staker.get_json()

            # Saving the blockchain locally
            self.save_locally()

            return True

        return False

    def get_lottery_score(self):
        return self.state.get_lottery_score()
