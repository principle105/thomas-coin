from .block import Block

class Blockchain:
    def __init__(self, chain: list[Block] = [], pruned: bool = False):
        self.chain = chain
        self.pruned = pruned

    def create_new_block(self, forger: str):
        """
        creator: public key of the block forger
        """

    def add_block(self, block: Block):

        # Checking if the block has a signature
        if block.signature is None:
            raise Exception("The block is not signed")

        # Checking if the block is valid
        block.validate(self)
        
        chain.append(block)


