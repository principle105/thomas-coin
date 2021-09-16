from .block import Block


class Blockchain:
    def __init__(self, chain: list[Block] = [], pruned: bool = False):
        self.chain = chain
        self.pruned = pruned

    def create_new_block(self, forger: str):
        """
        forger: public key of the block forger
        """

    def add_block(self, block: Block):

        # Checking if the block has a signature
        if block.signature is None:
            raise Exception("The block is not signed")

        # Checking if the block is valid
        block.validate(self)

        self.chain.append(block)

    def get_balance(self, address: str):
        bal = 0
        for block in self.chain:
            for t in block.transactions:
                if t.sender == address:
                    bal -= t.amount
                if t.receiver == address:
                    bal += t.amount

    def add_genesis_block(self):
        data = {
            "index": "0",
            "prev": "0",
            "forger": "T977e7b212b29a2b0fcc30d2c2db83c71ad1161c6 ",
            "timestamp": "1631749808.558269",
            "transactions": [
                {
                    "sender": "",
                    "receiver": "",
                    "amount": "",
                    "tip": "",
                    "timestamp": "",
                    "signature": "",
                }
            ],
            "signature": "",
        }
        genesis_block = Block.from_json()
        self.chain.append()
