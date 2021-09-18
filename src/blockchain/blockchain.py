from .block import Block

GENESIS_BLOCK_DATA = {
    "index": "0",
    "prev": "0",
    "forger": "0",
    "timestamp": "1631997358.256316",
    "transactions": [
        {
            "sender": "GENESIS",
            "sender_key": "GENESIS",
            "receiver": "T6a0459220225c6b4bfaef26ec87844a072afc29a",
            "amount": 10000,
            "tip": 0,
            "signature": "GENESIS",
            "timestamp": "1631997358.255879",
            "hash": "ba2a98efcc88fbd454aead1cefb96405c7827d2b0b55a721f3025749aaf1c6b1",
        }
    ],
    "hash": "6cdfe9138c37e7f9826f0031b2ef25dd33d2e7381e43380c4e6f5f4404fcfe7c",
    "signature": "0",
}

class Blockchain:
    def __init__(self, chain: list[Block] = [], pruned: bool = False):
        self.chain = chain
        self.pruned = pruned

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
                elif t.receiver == address:
                    bal += t.amount
        return bal

    def add_genesis_block(self):
        genesis_block = Block.from_json(**GENESIS_BLOCK_DATA)
        self.chain.append(genesis_block)
