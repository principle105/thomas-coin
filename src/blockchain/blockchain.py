import os
import _pickle as pickle
from .block import Block
from wallet import Wallet
from transaction import Transaction
from .state import State
from config import BLOCK_PATH
from constants import GENESIS_BLOCK_DATA


def get_block_data():
    if not os.path.exists(BLOCK_PATH):
        return False

    with open(BLOCK_PATH, "rb") as f:
        return pickle.load(f)


def dump_block_data(data: list):
    with open(BLOCK_PATH, "wb") as f:
        pickle.dump(data, f, protocol=2)


class Blockchain:
    main_chain = None

    def __init__(self, blocks: list[Block] = []):
        self.__class__.main_node = self

        self.state = State()

        # Blocks that are pending to be added to the blockchain
        self.pending: list[Block] = []

        # Adding the genesis block
        self.blocks = []
        self.add_block(self.get_genesis_block(), False)
        
        self.blocks += blocks

    def add_block(self, block: Block, validate: bool = True):
        # Removing the block transactions from pending
        for t in block.transactions:
            if t in self.pending:
                self.pending.remove(t)

        if validate:
            # Checking if the block is valid
            block.validate(self)

        self.state.add_block(block)

        self.blocks.append(block)

    def validate(self):
        for block in self.blocks:
            block.validate(self)

    def get_genesis_block(self):
        return Block.from_json(**GENESIS_BLOCK_DATA)

    def get_json(self):
        blocks = []
        for b in self.blocks:
            blocks.append(b.get_json())

        return blocks

    def save_locally(self):
        dump_block_data(self.blocks[1:])

    def add_pending(self, transaction: Transaction):
        # Making sure the transaction is valid
        try:
            transaction.validate(self)
        except Exception as e:
            print("The transaction is not valid", str(e))
            return False
        else:
            self.pending.append(transaction)
            return True

    @classmethod
    def from_local(cls, validate: bool = False):
        blocks = get_block_data()
        chain = cls()

        if blocks:
            for b in blocks:
                chain.add_block(b, validate)

        return chain

    @classmethod
    def from_json(cls, blocks: list, validate: bool = False):
        chain = cls()

        for b in blocks:
            block = Block.from_json(**b)
            chain.add_block(block, validate)

        return chain

    @classmethod
    def set_main(cls, chain, save: bool = True):
        if save:
            print("Saving locally")
            chain.save_locally()
        cls.main_chain = chain

    def create_trans(self, sender: Wallet, receiver: str, amount: float, tip: float):
        wallet = self.state.get_wallet(sender.address)

        t = Transaction(
            sender.public_key, receiver, float(amount), float(tip), wallet.nonce + 1
        )
        t.sign(sender)
        return t