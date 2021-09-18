from .block import Block
from constants import GENESIS_BLOCK_DATA

class Blockchain:
    def __init__(self, chain: list[Block] = [], pruned: bool = False):
        self.chain = chain
        self.pruned = pruned

        self.add_genesis_block()

    def add_block(self, block: Block):
        # Checking if the block is valid
        block.validate(self)

        self.chain.append(block)

    def get_balance(self, address: str):
        bal = 0
        for block in self.chain:
            for t in block.transactions:
                if t.sender == address:
                    bal -= t.amount
                elif t.receiver == address:
                    bal += t.amount
        return bal

    def add_genesis_block(self):
        genesis_block = Block.from_json(**GENESIS_BLOCK_DATA)
        self.chain.append(genesis_block)
