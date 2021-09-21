from .block import Block
from .storage import get_block_data, dump_block_data
from natsort import natsorted
from constants import GENESIS_BLOCK_DATA
from config import BLOCK_PATH


class Blockchain:
    def __init__(self, blocks: list[Block] = []):

        self.blocks = [self.get_genesis_block()] + blocks

    def add_block(self, block: Block):
        # Checking if the block is valid
        block.validate(self)

        self.blocks.append(block)

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
        chain = cls()

        blocks = get_block_data()
        if validate:
            for b in blocks:
                chain.add_block(b)
        else:
            chain.blocks = chain.blocks + blocks

        return chain
