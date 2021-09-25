import os
import _pickle as pickle
from .block import Block
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

        self.blocks = [self.get_genesis_block()] + blocks

    def add_block(self, block: Block, validate: bool = True):
        if validate:
            # Checking if the block is valid
            block.validate(self)

        self.blocks.append(block)

    def validate(self):
        for block in self.blocks:
            block.validate(self)

    def get_balance(self, address: str):
        bal = 0
        for block in self.blocks:
            for t in block.transactions:
                if t.sender == address:
                    bal -= t.amount
                if t.receiver == address:
                    bal += t.amount
        return bal

    def get_genesis_block(self):
        return Block.from_json(**GENESIS_BLOCK_DATA)

    def get_json(self):
        blocks = []
        for b in self.blocks:
            blocks.append(b.get_json())

        return blocks

    def save_locally(self):
        dump_block_data(self.blocks[1:])

    @classmethod
    def from_local(cls, validate: bool = False):
        blocks = get_block_data()
        chain = cls()

        if blocks:
            if validate:
                for b in blocks:
                    chain.add_block(b)
            else:
                chain.blocks = chain.blocks + blocks

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
